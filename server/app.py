"""DCS Sortie Starter — API server.

Run:  uvicorn server.app:app --reload
Then open http://127.0.0.1:8000
"""
import logging
import shutil
import sys
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response
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

app = FastAPI(title="DCS Sortie Starter", version=__version__)

# Password-gated sponsor-ad admin (/admin). Disabled unless ADMIN_PASSWORD is set.
from server.admin import router as admin_router  # noqa: E402
app.include_router(admin_router)

# Errors that are the USER's fault → 400 with the real message. Anything else is
# a bug and must surface as a 500 (logged, generic message) so monitoring sees
# it and we never leak a server path to the client.
#
# KeyError is deliberately NOT here: it used to mask real internal bugs (a
# missing data-pack key, a logic error) as a 400 "bad request". User-facing
# bad input (unknown map/era/enum) is now caught explicitly in Recipe.validate
# and raised as RecipeError, so a stray KeyError is genuinely a server bug → 500.
USER_ERRORS = (RecipeError, EraViolation, UnknownUnitError)


def _build_and_respond(recipe: Recipe):
    """Single build path shared by /api/generate and /api/dl so their error
    contracts and temp-file cleanup can't drift. Temp dir is removed after the
    response is sent (BackgroundTask) — the old code leaked ~93 KB per request."""
    tmpdir = tempfile.mkdtemp()
    try:
        recipe.validate()
        tag = recipe.template or "starter"
        fname = f"{recipe.map}_{recipe.era}_{recipe.aircraft}_{tag}_{recipe.seed}.miz"
        out = Path(tmpdir) / fname
        result = generate(recipe, str(out))
        # Count a sponsor impression when the active sponsor was actually baked
        # in (stats["branding"] holds the sponsor id; True = shipped default).
        _bid = result.get("stats", {}).get("branding")
        if isinstance(_bid, str):
            from missiongen import sponsors
            sponsors.increment_impressions(_bid)
    except USER_ERRORS as e:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        shutil.rmtree(tmpdir, ignore_errors=True)
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
    # modules pydcs has no native class for; verified ones list as normal jets
    from missiongen.pending import pending_aircraft
    for key, cfg in pending_aircraft().items():
        # a verified/released module is a normal selectable jet, not "upcoming"
        out.append({"key": key, "id": cfg["label"], "kind": cfg["kind"],
                    "service": service.get(key),
                    "upcoming": not cfg.get("verified", False)})
    # re-sort AFTER appending pending modules so e.g. the F-14B(U) alphabetizes
    # into the F-14 cluster instead of dangling at the bottom of the dropdown
    # where nobody scanning the roster finds it.
    out.sort(key=lambda a: a["id"])
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
        "air_corridors": {k: v for k, v in load_json("air_corridors").items()
                          if not k.startswith("_")},
        "templates": {
            # kind: "full" = the .miz places a flown route/waypoints (crew-ops);
            # "open" = a dressed theater, no waypoints placed (you fly/build it).
            # tasked = ships a suggested-tasking brief. Scenario templates are open
            # starters (north star: we never place the player's waypoints), most
            # with a suggested-tasking brief; crew-ops are full missions.
            **{k: {"label": v["label"], "eras": v.get("eras", []),
                   "maps": v.get("maps"), "needs_carrier": v.get("needs_carrier", False),
                   "needs_acls": v.get("needs_acls", False),
                   "recipe": v.get("recipe", {}),
                   "kind": (v.get("library") or {}).get("kind", "open"),
                   "tasked": bool(v.get("brief")),
                   "library": v.get("library"), "default_map": v.get("default_map")}
               for k, v in load_json("mission_templates").items()
               if not k.startswith("_")},
            "backseat_izlid": {"kind": "full", "tasked": True, "label": "F-14B(U) Pilot + Jester: IZLID Strike — you fly, Jester designates on your call",
                               "eras": ["modern"], "aircraft_locked": True, "default_map": "caucasus",
                               "recipe": {"aircraft": "F_14B_U"},
                               "library": {"role": "strike", "new": True, "featured": True, "module": "F-14B(U)",
                                           "threat": 3, "players": "SP",
                                           "premise": "You fly, Jester works the back seat — run the IZLID designation on your call through the F10 crew menu."}},
            "backseat_intercept": {"kind": "full", "tasked": True, "label": "F-14B(U) RIO + Iceman: GCI Intercept — Iceman flies YOUR calls from the back seat",
                                   "eras": ["modern"], "aircraft_locked": True, "default_map": "caucasus",
                                   "recipe": {"aircraft": "F_14B_U"},
                                   "library": {"role": "a2a", "new": True, "featured": True, "module": "F-14B(U)",
                                               "threat": 3, "players": "SP",
                                               "premise": "You're the RIO; Iceman flies your calls from the front seat — build the AWG-9 picture and commit on the raid."}},
            "rio_fleet_defense": {"kind": "full", "tasked": True, "label": "F-14 RIO: Fleet Defense — the AWG-9 vs a Backfire raid (solo or MP crew, works today)",
                                  "eras": ["coldwar", "modern"], "aircraft_locked": True, "default_map": "caucasus",
                                  "recipe": {"aircraft": "F_14B"},
                                  "library": {"role": "a2a", "new": True, "featured": True, "module": "F-14B(U)",
                                              "threat": 4, "players": "SP · MP",
                                              "premise": "Classic Tomcat outer-air-battle — manage the Phoenix picture against a saturating raid on the fleet."}},
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


ROADMAP_HTML = Path(__file__).parent.parent / "docs" / "roadmap.html"


@app.get("/api/roadmap")
def roadmap():
    """The product roadmap ships WITH the product — served as a styled HTML
    page (falls back to the Markdown source if the page is missing)."""
    if ROADMAP_HTML.exists():
        return HTMLResponse(ROADMAP_HTML.read_text())
    return FileResponse(str(ROADMAP_MD), filename="ROADMAP.md",
                        media_type="text/markdown")


@app.get("/api/guide")
def guide_download():
    """Downloadable Sortie Starter documentation (professional PDF)."""
    return FileResponse(str(DOCS_PDF), filename="DCS_Mission_Starter_Guide.pdf",
                        media_type="application/pdf")


@app.get("/api/health")
def health(response: Response):
    """Readiness probe. Data-pack errors mean the product cannot build correct
    missions, so return 503 (not a 200 with ok:false) — a load balancer or
    monitor treats it as unhealthy and stops sending traffic."""
    errors = validate_data_packs()
    service = load_json("aircraft_service")
    gaps = [a["key"] for a in flyable_aircraft() if a["key"] not in service]
    if errors:
        response.status_code = 503
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


@app.post("/api/brief")
def api_brief(req: GenerateRequest):
    """Sortie Starter Brief — the pre-flight briefing pack (PDF + MD, zipped).

    Stateless by design: the determinism contract means the same recipe rebuilds
    the identical mission, so the brief regenerates on demand — no server-side
    storage, and the .miz download flow is untouched."""
    tmpdir = tempfile.mkdtemp()
    try:
        recipe = Recipe.from_dict(req.recipe)
        recipe.validate()
        miz = Path(tmpdir) / "m.miz"
        result = generate(recipe, str(miz), brief_dir=tmpdir)
        if "brief_pdf" not in result:
            raise RuntimeError("; ".join(result["warnings"]) or "brief failed")
        import zipfile as _zf
        tag = recipe.template or "starter"
        stem = f"{recipe.map}_{recipe.era}_{tag}_{recipe.seed}"
        pack = Path(tmpdir) / "briefing_pack.zip"
        with _zf.ZipFile(pack, "w", _zf.ZIP_DEFLATED) as z:
            z.write(result["brief_pdf"], f"{stem}_brief.pdf")
            z.write(result["brief_md"], f"{stem}_brief.md")
            if result.get("dtc_card"):        # F-14B(U): include the DTC setup card
                z.write(result["dtc_card"], f"{stem}_dtc_setup_card.md")
    except USER_ERRORS as e:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        shutil.rmtree(tmpdir, ignore_errors=True)
        log.exception("brief generation failed")
        raise HTTPException(status_code=500, detail="Internal error generating the brief.")
    return FileResponse(str(pack), filename=f"{stem}_briefing_pack.zip",
                        media_type="application/zip",
                        background=BackgroundTask(shutil.rmtree, tmpdir, ignore_errors=True))
