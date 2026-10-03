"""DCS Sortie Starter — API server.

Run:  uvicorn server.app:app --reload
Then open http://127.0.0.1:8000
"""
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from missiongen import __version__

log = logging.getLogger("missionstarter")
from . import ga as _ga


router = APIRouter()

from . import ga as _ga


FRONTEND = Path(__file__).parent.parent / "frontend" / "index.html"


FONT_DIR = Path(__file__).parent.parent / "missiongen" / "data" / "brand" / "fonts"


@router.get("/fonts/{name}")
def font_file(name: str):
    """Self-hosted Flightline fonts (all OFL; license texts ship in the repo).

    Serving these ourselves rather than from Google Fonts means opening the
    page no longer sends every visitor's IP to a third party for typography —
    the same no-PII stance the analytics ledger already holds. The name is
    validated against the directory listing, so this cannot be used to read
    arbitrary files.
    """
    if name not in {p.name for p in FONT_DIR.glob("*.ttf")}:
        raise HTTPException(status_code=404, detail="Not Found")
    return FileResponse(str(FONT_DIR / name), media_type="font/ttf",
                        headers={"Cache-Control": "public, max-age=604800"})


NOTFOUND = Path(__file__).parent.parent / "frontend" / "404.html"


async def not_found(request, exc):
    """404s split by audience: API clients keep the JSON contract they parse;
    a human who fat-fingers a URL gets the radar scope with the missing
    contact instead of a bare {"detail":"Not Found"}."""
    from fastapi.responses import JSONResponse
    if request.url.path.startswith("/api/") or not NOTFOUND.exists():
        return JSONResponse({"detail": "Not Found"}, status_code=404)
    return HTMLResponse(_ga.inject(NOTFOUND.read_text()), status_code=404)


@router.get("/", response_class=HTMLResponse)
def index():
    page = _ga.inject(FRONTEND.read_text()).replace("{{APP_VERSION}}", __version__)
    # Version every script URL so caches cannot mix controllers across releases.
    import re
    page = re.sub(r'(src="/assets/[^"?]+)(")', rf'\1?v={__version__}\2', page)
    return HTMLResponse(page, headers={"Cache-Control": "no-store"})
