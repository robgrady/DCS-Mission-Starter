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

from missiongen import __version__
from missiongen import tracks as _tracks_mod
from missiongen import courses as _courses_mod

log = logging.getLogger("missionstarter")


router = APIRouter()

def _published_tracks() -> dict:
    """Track summaries, each flagged with whether its pack is published here."""
    from .packref import installed_pack
    out = {}
    for tid, t in (_tracks_mod.summaries() or {}).items():
        t = dict(t)
        t["published"] = installed_pack(tid) is not None
        # ...and when it IS published the pack card renders it, so the track
        # card stands down rather than duplicating it.
        t["superseded_by_pack"] = t["published"]
        out[tid] = t
    return out


def _pack_templates() -> dict:
    """Installed packs rendered as Library entries, same shape the frontend
    already understands for template cards."""
    from missiongen import packs as _packs
    out = {}
    for man in _packs.list_packs():
        pid = man["id"]
        # A pack and a track sharing an id are the SAME syllabus — one authored
        # as a spec, the other as the artifact built from it. Rendering both
        # gives the pilot two cards for one thing, and the difference between
        # them is an implementation detail he should never have to learn.
        # The pack wins: it is the published artifact.
        out[f"pack_{pid}"] = {
            "label": man.get("label") or pid,
            "eras": man.get("eras") or ["modern"],
            "maps": man.get("maps"),
            "needs_carrier": False, "needs_acls": False,
            "recipe": {}, "kind": "full", "tasked": True, "quick": False,
            "default_map": (man.get("maps") or [None])[0],
            "pack": {"id": pid, "image": man.get("image"),
                     "guide_pdf": (man.get("docs") or {}).get("guide"),
                     "readme_pdf": (man.get("docs") or {}).get("readme"),
                     "events": man.get("events", []),
                     # WHAT A PILOT MUST OWN, surfaced BEFORE the download.
                     # This is the field the whole format-2 exercise was for:
                     # without it somebody downloads eleven Sinai missions and
                     # finds out afterwards that he does not have Sinai.
                     "requires": man.get("requires") or {},
                     "version": man.get("version"),
                     "source": man.get("source"),
                     "size_mb": man.get("size_mb")},
            "library": {"role": man.get("role", "training"),
                        "threat": man.get("threat", 3),
                        "players": man.get("players", "SP"),
                        "new": True, "featured": bool(man.get("featured")),
                        "module": man.get("module"), "kind": "full",
                        "premise": man.get("premise", "")},
        }
    return out


TRACK_DOCS = Path(__file__).parent.parent / "docs"


@router.get("/api/track/{track}/guide.pdf")
def api_track_guide(track: str, era: str = None, aircraft: str = None,
                    tanker: str = None):
    """The printed syllabus. With no query it serves the committed default;
    with a selection it is GENERATED for that combination, because a guide
    showing an F-16C sight picture to somebody flying the syllabus in a
    Phantom is the say/do gap this product exists to avoid."""
    from missiongen import tracks as _tracks
    t = _tracks.get(track)
    if not t or not t.get("guide"):
        raise HTTPException(status_code=404, detail="Not Found")
    if not (t.get("lane")):
        # A track with no refuelling lane has no era/aircraft/tanker wizard
        # behind it, so there is nothing to resolve and nothing to cache. It
        # gets its own builder. Routing it through the AAR path would have
        # 404'd on a committed default that does not exist and 400'd on a
        # tanker it never had — a track advertising a guide it cannot produce
        # is the say/do gap with a filename on it.
        from missiongen import wk_guide as _wkg
        tmpdir = tempfile.mkdtemp()
        pdf = _wkg.build(track, t, __version__, out_dir=tmpdir,
                         map_key=(t.get("default_map") or ""))
        return FileResponse(str(pdf), media_type="application/pdf",
                            filename=f"{t['guide']}.pdf",
                            background=BackgroundTask(shutil.rmtree, tmpdir,
                                                      ignore_errors=True))
    if not (era or aircraft or tanker):
        # Resolve inside docs/ and refuse anything that escapes it — the track
        # id comes off the URL and a data typo must not become a traversal.
        f = (TRACK_DOCS / f"{t['guide']}.pdf").resolve()
        if TRACK_DOCS.resolve() not in f.parents or not f.is_file():
            raise HTTPException(status_code=404, detail="Not Found")
        return FileResponse(str(f), filename=f"{t['guide']}.pdf",
                            media_type="application/pdf")
    try:
        era, aircraft, tanker = _tracks.resolve_choice(track, era, aircraft,
                                                       tanker)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    tmpdir = tempfile.mkdtemp()
    from missiongen import aar_guide as _guide
    pdf = _guide.build(track, t, __version__, out_dir=tmpdir,
                       aircraft=aircraft, tanker=tanker, era=era)
    return FileResponse(str(pdf), media_type="application/pdf",
                        filename=f"{t['guide']}-{aircraft.lower()}.pdf",
                        background=BackgroundTask(shutil.rmtree, tmpdir,
                                                  ignore_errors=True))


@router.get("/api/courses")
def api_courses():
    return _courses_mod.summaries()


@router.get("/api/course/{course}")
def api_course(course: str):
    try:
        c = _courses_mod.resolve(course)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not c:
        raise HTTPException(status_code=404, detail="Not Found")
    return c


@router.get("/api/course/{course}/reading/{doc}")
def api_course_reading(course: str, doc: str):
    """A chapter, rendered for the site's own page furniture. The markdown
    ships alongside for anyone who wants to paste it into a squadron wiki."""
    c = _courses_mod.get(course)
    if not c:
        raise HTTPException(status_code=404, detail="Not Found")
    docs = {u.get("doc") for s in c.get("schools") or [] for p in s.get("phases") or []
            for u in p.get("units") or [] if u.get("kind") == "reading"}
    md = _courses_mod.reading_text(doc) if doc in docs else None
    if md is None:
        raise HTTPException(status_code=404, detail="Not Found")
    from server.admin import _md_to_html
    title = next((ln[2:].strip() for ln in md.splitlines() if ln.startswith("# ")), doc)
    return {"course": course, "doc": doc, "title": title,
            "html": _md_to_html(md), "md": md}


@router.get("/api/course/{course}/kit.zip")
def api_course_kit(course: str):
    """The squadron kit: program PDF, gradesheet CSV, readings. No
    missions — see course_kit.py for why."""
    if not _courses_mod.get(course):
        raise HTTPException(status_code=404, detail="Not Found")
    from missiongen import course_kit as _kit
    tmpdir = tempfile.mkdtemp()
    z = _kit.build_kit(course, __version__, Path(tmpdir))
    return FileResponse(str(z), media_type="application/zip",
                        filename=f"{course}_kit.zip",
                        background=BackgroundTask(shutil.rmtree, tmpdir,
                                                  ignore_errors=True))


def _track_pack_or_none(track: str):
    """The published pack for this track, or None.

    THE IN-REQUEST BUILD IS GONE. It used to live here: eleven missions, eleven
    brief PDFs and a printed guide, assembled while the browser waited. Half a
    minute of saturated CPU on a developer machine and minutes on a shared
    vCPU; on Fly it came back 502 with the machine restarting under the
    download, which is how Rob found it.

    Caching it in the image made the symptom go away for four of the sixty
    possible combinations and left the other fifty-six armed. Deleting the
    build is the only version of this fix that is actually finished.

    A syllabus is now either PUBLISHED — produced by scripts/build_pack.py,
    uploaded through /admin — or it is flown one ride at a time, which is a
    single mission per request and has never been a problem. Nothing in
    between, and nothing that can take the machine down.
    """
    from .packref import pack_zip
    return pack_zip(track)


@router.get("/api/track/{track}/all.zip")
def api_track_zip(track: str, era: str = None, aircraft: str = None,
                  tanker: str = None):
    """The whole syllabus, IF it has been published as a pack.

    The query parameters are accepted and ignored, so that every share link and
    bookmark from before the pack model still resolves. What they used to do —
    pick a combination and build it — is exactly the thing that had to stop.
    """
    from missiongen import tracks as _tracks
    t = _tracks.get(track)
    if not t:
        raise HTTPException(status_code=404, detail="Not Found")
    path = _track_pack_or_none(track)
    if path is None:
        # 409, not 404: the syllabus EXISTS, it simply has not been published
        # here. The message is written for the person who clicked, because a
        # bare status code sends them looking for a bug that is not there.
        raise HTTPException(
            status_code=409,
            detail=("This syllabus has not been published as a pack on this "
                    "server yet. Every ride can still be generated on its own "
                    "from the Library card."))
    from missiongen import analytics
    analytics.record("track", "library", type("R", (), {
        "template": f"{track}_ALL", "map": None,
        "era": (t.get("eras") or [None])[0],
        "aircraft": t.get("aircraft"), "slots": 1, "threat_tier": None})())
    return FileResponse(str(path), media_type="application/zip",
                        filename=f"{track}_complete.zip")


@router.get("/api/pack/{pack}/{fname:path}")
def api_pack_file(pack: str, fname: str):
    """Serve a file from an installed pack. all.zip bundles the whole pack."""
    from missiongen import packs as _packs
    if fname == "all.zip":
        return _pack_all_zip(pack)
    f = _packs.get_file(pack, fname)
    if f is None:
        raise HTTPException(status_code=404, detail="Not Found")
    if f.suffix.lower() == ".miz":
        from missiongen import analytics
        analytics.record("pack", "library", type("R", (), {
            "template": f"{pack}/{f.stem}", "map": None, "era": None,
            "aircraft": None, "slots": 1, "threat_tier": None})())
    media = {".miz": "application/zip", ".pdf": "application/pdf",
             ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
             ".md": "text/markdown", ".json": "application/json"}.get(
                 f.suffix.lower(), "application/octet-stream")
    return FileResponse(str(f), filename=f.name, media_type=media)


def _pack_all_zip(pack: str):
    """The whole pack as one download. ONE implementation, in `packs`.

    It used to be zipped here and zipped again in `packref` for the track
    route, which is the twin-function shape this codebase has paid for twice.
    """
    from missiongen import packs as _packs
    p = _packs.all_zip(pack)
    if p is None:
        raise HTTPException(status_code=404, detail="Not Found")
    return FileResponse(str(p), media_type="application/zip",
                        filename=f"{_packs._slug(pack)}_complete.zip")

