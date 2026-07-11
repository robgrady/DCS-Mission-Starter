"""DCS Mission Starter — API server.

Run:  uvicorn server.app:app --reload
Then open http://127.0.0.1:8000
"""
import io
import sys
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

_root = Path(__file__).parent.parent
sys.path.insert(0, str(_root))
if (_root / "vendor" / "dcs").exists():          # vendored pydcs (Mac/no-network installs)
    sys.path.insert(0, str(_root / "vendor"))
from missiongen import Recipe, generate
from missiongen.resolver import load_json, validate_data_packs

app = FastAPI(title="DCS Mission Starter")

FRONTEND = Path(__file__).parent.parent / "frontend" / "index.html"


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
        "maps": {k: {"label": v["label"], "free": v["free"],
                     "has_carrier": "carrier" in v,
                     "presets": {e: {"blue_airbases": p["blue_airbases"],
                                     "red_airbases": p["red_airbases"],
                                     "blue_country": p["blue_country"],
                                     "red_country": p["red_country"]}
                                 for e, p in v["presets"].items()}}
                 for k, v in maps.items()},
        "eras": {k: {"label": v["label"], "window": v.get("window")}
                 for k, v in eras.items()},
        "aircraft": flyable_aircraft(),
        "templates": {
            "backseat_izlid": {"label": "WSO: IZLID Designation (F-4E solo — you run the mission from the back seat)",
                               "eras": ["coldwar", "modern"]},
            "backseat_intercept": {"label": "WSO: GCI Intercept (F-4E solo — commit the intercept from the pit)",
                                   "eras": ["coldwar", "modern"]},
            "rio_fleet_defense": {"label": "RIO: Fleet Defense (F-14 multiplayer crew — the AWG-9 vs a Backfire raid)",
                                  "eras": ["coldwar", "modern"]},
        },
        "carriers": __import__("missiongen.deck", fromlist=["hulls_for_options"]).hulls_for_options(),
        "enums": {
            "start": ["cold", "warm", "runway"],
            "time_of_day": ["dawn", "day", "dusk", "night"],
            "weather": ["clear", "scattered", "overcast", "storm"],
            "density": ["sparse", "normal", "busy"],
        },
    }


DOCS_PDF = Path(__file__).parent.parent / "docs" / "DCS_Mission_Starter_Guide.pdf"


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
    return {"ok": not errors, "data_pack_errors": errors,
            "service_data_gaps": gaps}


@app.get("/api/dl")
def api_download_by_code(r: str):
    """A share link IS the mission: /api/dl?r=<code> regenerates and downloads it."""
    from missiongen.share import decode_recipe
    try:
        recipe = decode_recipe(r)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid share code")
    tag = recipe.template or "starter"
    fname = f"{recipe.map}_{recipe.era}_{recipe.aircraft}_{tag}_{recipe.seed}.miz"
    out = Path(tempfile.mkdtemp()) / fname
    result = generate(recipe, str(out))
    return FileResponse(str(out), filename=fname, media_type="application/zip",
                        headers={"X-Warnings": "; ".join(result["warnings"])[:900]})


class GenerateRequest(BaseModel):
    recipe: dict


@app.post("/api/generate")
def api_generate(req: GenerateRequest):
    try:
        recipe = Recipe.from_dict(req.recipe)
        tag = recipe.template or "starter"
        fname = f"{recipe.map}_{recipe.era}_{recipe.aircraft}_{tag}_{recipe.seed}.miz"
        out = Path(tempfile.mkdtemp()) / fname
        result = generate(recipe, str(out))
        return FileResponse(str(out), filename=fname,
                            media_type="application/zip",
                            headers={"X-Warnings": "; ".join(result["warnings"])[:900]})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
