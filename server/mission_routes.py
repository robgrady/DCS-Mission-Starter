"""DCS Sortie Starter — API server.

Run:  uvicorn server.app:app --reload
Then open http://127.0.0.1:8000
"""
import logging
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from pydantic import BaseModel, Field

from missiongen import Recipe
from .recipe_contract import recipe_json_schema
from missiongen.recipe import Recipe

log = logging.getLogger("missionstarter")

from .artifact_service import USER_ERRORS, _build_and_respond, generate

router = APIRouter()

@router.get("/api/dl")
def api_download_by_code(r: str):
    """A share link IS the mission: /api/dl?r=<code> regenerates and downloads it.
    Uses the SAME build+error path as /api/generate, so a hand-edited or
    truncated share link returns a clean 400, not an unhandled 500."""
    from missiongen.share import decode_recipe
    try:
        recipe = decode_recipe(r)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid share code")
    return _build_and_respond(recipe, source="share")


@router.get("/api/recipe-schema")
def api_recipe_schema():
    """Field types/defaults/enums from the same dataclass the engine validates."""
    return recipe_json_schema()


class GenerateRequest(BaseModel):
    recipe: dict = Field(json_schema_extra=recipe_json_schema())
    # Which door the request came through (builder | library | quick). Used
    # ONLY for the no-PII analytics ledger; unknown/absent values fall back to
    # "api" so a stale client can't invent categories.
    source: str = "api"
    # Anonymous visitor id: a random UUID the browser made up about itself.
    # Absent when the visitor opted out or sent Do Not Track. Stored hashed.
    visitor: str | None = None


class EventRequest(BaseModel):
    event: str


EVENTS = ("want_mixed_flight", "qf_open", "qf_reroll")


_event_counts: dict = {}


@router.post("/api/ev")
def api_event(req: EventRequest):
    """Record an interest click on a feature that doesn't exist yet.

    Deliberately minimal: no request body beyond the event name, nothing about
    who sent it. Unknown names are dropped silently so a stale client (or a
    bot) can't fill the log."""
    if req.event in EVENTS:
        _event_counts[req.event] = _event_counts.get(req.event, 0) + 1
        log.info("ev %s n=%d", req.event, _event_counts[req.event])
    return {"ok": True}


@router.post("/api/generate")
def api_generate(req: GenerateRequest):
    try:
        recipe = Recipe.from_dict(req.recipe)     # validates enums/bounds
    except USER_ERRORS as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _build_and_respond(recipe, source=req.source, visitor=req.visitor)


@router.post("/api/brief")
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
    except HTTPException:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise
    except USER_ERRORS as e:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        shutil.rmtree(tmpdir, ignore_errors=True)
        log.exception("brief generation failed")
        raise HTTPException(status_code=500, detail="Internal error generating the brief.")
    from missiongen import analytics
    analytics.record("brief", req.source, recipe, visitor=req.visitor)
    return FileResponse(str(pack), filename=f"{stem}_briefing_pack.zip",
                        media_type="application/zip",
                        background=BackgroundTask(shutil.rmtree, tmpdir, ignore_errors=True))


_KB_TITLES = ["comms_nav", "airfield_data", "theater_overview",
              "stores", "flight_plan"]


_KB_README = """DCS SORTIE STARTER — KNEEBOARD PACK
{stem}

These are the same pages that ship inside the mission. They are here as plain
PNGs so they are yours to use anywhere: OpenKneeboard, a printed card on your
leg, or a Discord post to the rest of your flight.

TO USE THEM IN DCS WITHOUT THE MISSION
  Copy the PNG files into:

    Saved Games\\DCS\\Kneeboard\\             (every aircraft, every mission)
    Saved Games\\DCS\\Kneeboard\\<AIRCRAFT>\\  (one airframe only, e.g. F-16C_50)

  DCS shows them in filename order, which is why they are numbered. Open the
  kneeboard in the cockpit with RCTRL+K and page with [ and ].

  If you fly DCS from Steam the folder is the same — Saved Games, not the
  Steam library.

NOTE
  The pages are already inside the .miz you downloaded. You only need these
  files if you want them outside that one mission.

  Headings on the flight plan card are TRUE. Apply your theater's magnetic
  variation before flying them off the compass.

Generated by {site} - mission {stem}
"""


@router.post("/api/kneeboard")
def api_kneeboard(req: GenerateRequest):
    """The kneeboard pages as a ZIP of PNGs, outside the .miz.

    WHY THIS EXISTS. The pages have always been generated and injected into the
    mission, which makes them invisible everywhere else: you cannot open them in
    OpenKneeboard, print one, put them in Saved Games for every mission, or post
    them to a squadron Discord. The renderer was never the limitation — the
    packaging was. So this rebuilds the same mission (the determinism contract
    means it is byte-identical to the one downloaded) and lifts the pages out.

    Stateless, like /api/brief: nothing is stored, the recipe regenerates it.
    """
    tmpdir = tempfile.mkdtemp()
    try:
        recipe = Recipe.from_dict(req.recipe)
        recipe.validate()
        if not recipe.bb_kneeboard:
            raise HTTPException(
                status_code=400,
                detail="This mission has no kneeboard — turn on the nav chart "
                       "kneeboard and generate again.")
        miz = Path(tmpdir) / "m.miz"
        generate(recipe, str(miz))
        import zipfile as _zf
        tag = recipe.template or "starter"
        stem = f"{recipe.map}_{recipe.era}_{tag}_{recipe.seed}"
        with _zf.ZipFile(miz) as z:
            pages = sorted(n for n in z.namelist()
                           if n.startswith("KNEEBOARD/IMAGES/")
                           and n.lower().endswith(".png"))
            if not pages:
                raise HTTPException(
                    status_code=400,
                    detail="No kneeboard pages were rendered for this mission.")
            pack = Path(tmpdir) / "kneeboard_pack.zip"
            with _zf.ZipFile(pack, "w", _zf.ZIP_DEFLATED) as out:
                for i, name in enumerate(pages):
                    # Title where we know it, index where we do not — a new page
                    # appended by a later release must still export, just with a
                    # generic name, rather than crashing on a short list.
                    title = _KB_TITLES[i] if i < len(_KB_TITLES) else f"page{i + 1:02d}"
                    out.writestr(f"{stem}_{i + 1:02d}_{title}.png", z.read(name))
                out.writestr(
                    "README.txt",
                    _KB_README.format(stem=stem, site="DCS Sortie Starter"))
    except HTTPException:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise
    except USER_ERRORS as e:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        shutil.rmtree(tmpdir, ignore_errors=True)
        log.exception("kneeboard pack generation failed")
        raise HTTPException(status_code=500,
                            detail="Internal error building the kneeboard pack.")
    from missiongen import analytics
    analytics.record("kneeboard", req.source, recipe, visitor=req.visitor)
    return FileResponse(str(pack), filename=f"{stem}_kneeboard_pack.zip",
                        media_type="application/zip",
                        background=BackgroundTask(shutil.rmtree, tmpdir,
                                                  ignore_errors=True))

