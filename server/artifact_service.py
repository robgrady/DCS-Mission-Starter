"""DCS Sortie Starter — API server.

Run:  uvicorn server.app:app --reload
Then open http://127.0.0.1:8000
"""
import json
import logging
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from missiongen import Recipe, generate as _engine_generate
from .generation import capacity as generation_capacity
from missiongen.recipe import Recipe, RecipeError
from missiongen.builder import EraViolation
from missiongen.resolver import UnknownUnitError

log = logging.getLogger("missionstarter")


router = APIRouter()

def generate(recipe: Recipe, out_path: str, brief_dir: str = None):
    """API admission boundary, shared by mission and document generation."""
    with generation_capacity.slot():
        return _engine_generate(recipe, out_path, brief_dir=brief_dir)


USER_ERRORS = (RecipeError, EraViolation, UnknownUnitError)


_HEADER_TRANSLIT = {
    "—": "--", "–": "-", "−": "-",      # em/en dash, minus
    "×": "x", "·": "-", "…": "...",     # times, middot, ellipsis
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "→": "->", "✓": "OK", "•": "-",
}


def _header_safe(s: str) -> str:
    """Make a string safe to put in an HTTP header without losing its meaning."""
    for bad, good in _HEADER_TRANSLIT.items():
        s = s.replace(bad, good)
    return s.encode("latin-1", "replace").decode("latin-1")


def _build_and_respond(recipe: Recipe, source: str = "api", visitor: str | None = None):
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
    except HTTPException:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise
    except USER_ERRORS as e:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        shutil.rmtree(tmpdir, ignore_errors=True)
        log.exception("mission generation failed")
        raise HTTPException(status_code=500, detail="Internal error generating the mission.")
    # No-PII analytics: record the MISSION's shape (never the user's) — see
    # missiongen/analytics.py for the entire schema. Best-effort by contract.
    from missiongen import analytics
    analytics.record("dl" if source == "share" else "generate", source, recipe,
                     visitor=visitor)
    # X-Kit (UX v3, Mission Kit panel): what the engine actually produced, so
    # the frontend can hand the user their documents BY NAME instead of ending
    # the flow with a status string. Data already in stats — no extra work.
    stats = result.get("stats", {})
    from .mission_manifest import kit_manifest
    kit = kit_manifest(stats)
    return FileResponse(str(out), filename=fname, media_type="application/zip",
                        headers={"X-Warnings": _header_safe(
                                     "; ".join(result["warnings"]))[:900],
                                 "X-Kit": json.dumps(kit)},
                        background=BackgroundTask(shutil.rmtree, tmpdir, ignore_errors=True))

