"""DCS Mission Starter — API server.

Run:  uvicorn server.app:app --reload
Then open http://127.0.0.1:8000
"""
import logging
import shutil
import sys
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from starlette.background import BackgroundTask
from pydantic import BaseModel

_root = Path(__file__).parent.parent
sys.path.insert(0, str(_root))
if (_root / "vendor" / "dcs").exists():          # vendored pydcs (Mac/no-network installs)
    sys.path.insert(0, str(_root / "vendor"))
from missiongen import Recipe, generate, __version__
from missiongen.recipe import RecipeError
from missiongen.builder import EraViolation
from missiongen.resolver import load_json, validate_data_packs, UnknownUnitError
from missiongen import deck as _deck

log = logging.getLogger("missionstarter")

app = FastAPI(title="DCS Mission Starter", version=__version__)

# Errors that are the USER's fault → 400 with the real message. Anything else is
# a bug and must surface as a 500 (logged, generic message) so monitoring sees
# it and we never leak a server path to the client.
USER_ERRORS = (RecipeError, EraViolation, UnknownUnitError, KeyError)


def _build_and_respond(recipe: Recipe):
    """Single build path shared by /api/generate and /api/dl so their error
    contracts and temp-file cleanup can't drift. Temp dir is removed after the
    response is sent (BackgroundTask) — the old code leaked ~93 KB per request."""
    try:
        recipe.validate()
        tag = recipe.template or "starter"
        fname = f"{recipe.map}_{recipe.era}_{recipe.aircraft}_{tag}_{recipe.seed}.miz"
        tmpdir = tempfile.mkdtemp()
        out = Path(tmpdir) / fname
        result = generate(recipe, str(out))
    except USER_ERRORS as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        log.exception("mission generation failed")
        raise HTTPException(status_code=500, detail="Internal error generating the mission.")
    return FileResponse(str(out), filename=fname, media_type="application/zip",
                        headers={"X-Warnings": "; ".join(result["warnings"])[:900]},
                        background=BackgroundTask(shutil.rmtree, tmpdir, ignore_errors=True))

FRONTEND = Path(__file__).parent.parent / "frontend" / "index.html"


def _theme_mix(theme):
    """Flatten a ramp theme's weighted planes/large/helos lists into a default
    {type_id: count} composition the Ramp Composer pre-populates from. Weights
    double as sensible starting counts (a Red Flag ramp is authored that way)."""
    mix = {}
    for key in ("planes", "large", "helos"):
        for entry in theme.get(key, []):
            ref = entry[0]
            weight = entry[1] if len(entry) > 1 else 1
            tid = ref.split(".")[-1]
            mix[tid] = mix.get(tid, 0) + int(weight)
    return mix


def flyable_aircraft():
    """FR-1: every current flyable DCS aircraft, straight from the pydcs unit DB."""
    import dcs.planes as planes
    import dcs.helicopters as helicopters
    out = []
    for mod, kind in ((planes, "plane"), (helicopters, "helicopter")):
        for name in dir(mod):
            if name.startswith("_"):
                continue
            cls = getattr(mod, name)
            if isinstance(cls, type) and getattr(cls, "flyable", False):
                out.append({"key": name, "id": cls.id, "kind": kind})
    out.sort(key=lambda a: a["id"])
    service = load_json("aircraft_service")
    for a in out:
        a["service"] = service.get(a["key"])   # [from, to|null] or null=unknown
    # pending (announced/pre-order) modules, flagged for the UI
    from missiongen.pending import pending_aircraft
    for key, cfg in pending_aircraft().items():
        out.append({"key": key, "id": cfg["label"], "kind": cfg["kind"],
                    "upcoming": True})
    return out


@app.get("/", response_class=HTMLResponse)
def index():
    return FRONTEND.read_text()


@app.get("/api/options")
def options():
    maps = load_json("maps")
    eras = load_json("eras")
    return {
        "version": __version__,
        "maps": {k: {"label": v["label"], "free": v["free"],
                     "has_carrier": "carrier" in v,
                     "presets": {e: {"blue_airbases": p["blue_airbases"],
                                     "red_airbases": p["red_airbases"],
                                     "blue_country": p["blue_country"],
                                     "red_country": p["red_country"],
                                     "civilian_airbases": p.get("civilian_airbases", [])}
                                 for e, p in v["presets"].items()}}
                 for k, v in maps.items()},
        "eras": {k: {"label": v["label"], "window": v.get("window")}
                 for k, v in eras.items()},
        "aircraft": flyable_aircraft(),
        "templates": {
            **{k: {"label": v["label"], "eras": v.get("eras", []),
                   "maps": v.get("maps"), "needs_carrier": v.get("needs_carrier", False),
                   "needs_acls": v.get("needs_acls", False),
                   "recipe": v.get("recipe", {})}
               for k, v in load_json("mission_templates").items()
               if not k.startswith("_")},
            "backseat_izlid": {"label": "F-14B(U) Pilot + Jester: IZLID Strike — you fly, Jester designates on your call (⏳ pre-release module)",
                               "eras": ["modern"], "aircraft_locked": True},
            "backseat_intercept": {"label": "F-14B(U) RIO + Iceman: GCI Intercept — Iceman flies YOUR calls from the back seat (⏳ pre-release module)",
                                   "eras": ["modern"], "aircraft_locked": True},
            "rio_fleet_defense": {"label": "F-14 RIO: Fleet Defense — the AWG-9 vs a Backfire raid (solo or MP crew, works today)",
                                  "eras": ["coldwar", "modern"], "aircraft_locked": True},
        },
        "ramp_themes": {
            era: {side: {k: {"label": t["label"], "desc": t["desc"],
                             "mix": _theme_mix(t)}
                         for k, t in sides.items() if k != "default"}
                  for side, sides in eras_t.items()}
            for era, eras_t in load_json("ramp_themes").items()
            if isinstance(eras_t, dict)},
        "map_theme_defaults": {
            mk: {e: {s: p.get(f"{s}_theme") for s in ("blue", "red")}
                 for e, p in mv["presets"].items()}
            for mk, mv in maps.items()},
        "carriers": _deck.hulls_for_options(),
        "carrier_capable": load_json("carrier_capable"),
        "static_catalog": load_json("static_catalog"),
        "enums": {
            "start": ["cold", "warm", "runway"],
            "time_of_day": ["dawn", "day", "dusk", "night"],
            "weather": ["clear", "scattered", "overcast", "storm"],
            "density": ["sparse", "normal", "busy"],
        },
    }


DOCS_PDF = Path(__file__).parent.parent / "docs" / "DCS_Mission_Starter_Guide.pdf"
ROADMAP_MD = Path(__file__).parent.parent / "docs" / "ROADMAP.md"


@app.get("/api/roadmap")
def roadmap():
    """The product roadmap ships WITH the product (published manifest)."""
    return FileResponse(str(ROADMAP_MD), filename="ROADMAP.md",
                        media_type="text/markdown")


@app.get("/api/guide")
def guide_download():
    """Downloadable Mission Starter documentation (professional PDF)."""
    return FileResponse(str(DOCS_PDF), filename="DCS_Mission_Starter_Guide.pdf",
                        media_type="application/pdf")


@app.get("/api/health")
def health():
    errors = validate_data_packs()
    service = load_json("aircraft_service")
    gaps = [a["key"] for a in flyable_aircraft() if a["key"] not in service]
    return {"ok": not errors, "version": __version__,
            "data_pack_errors": errors, "service_data_gaps": gaps}


@app.get("/api/dl")
def api_download_by_code(r: str):
    """A share link IS the mission: /api/dl?r=<code> regenerates and downloads it.
    Uses the SAME build+error path as /api/generate, so a hand-edited or
    truncated share link returns a clean 400, not an unhandled 500."""
    from missiongen.share import decode_recipe
    try:
        recipe = decode_recipe(r)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid share code")
    return _build_and_respond(recipe)


class GenerateRequest(BaseModel):
    recipe: dict


@app.post("/api/generate")
def api_generate(req: GenerateRequest):
    try:
        recipe = Recipe.from_dict(req.recipe)     # validates enums/bounds
    except USER_ERRORS as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _build_and_respond(recipe)
