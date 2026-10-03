"""DCS Sortie Starter — API server.

Run:  uvicorn server.app:app --reload
Then open http://127.0.0.1:8000
"""
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse, FileResponse, HTMLResponse, PlainTextResponse


log = logging.getLogger("missionstarter")
from . import ga as _ga


router = APIRouter()

DOCS_PDF = Path(__file__).parent.parent / "docs" / "DCS_Mission_Starter_Guide.pdf"
MCP_GUIDE = Path(__file__).parent.parent / 'docs' / 'MCP.md'


@router.get('/api/mcp-guide')
def mcp_guide():
    """Public agent integration reference; one source also serves MCP readers."""
    return Response(MCP_GUIDE.read_text(), media_type='text/markdown',
                    headers={'Cache-Control': 'no-store'})


@router.get('/llms.txt')
def agent_document_index():
    from missiongen import __version__
    return PlainTextResponse(
        '# DCS Sortie Starter\n\n'
        f'> Native DCS mission generation and public MCP integration. App v{__version__}.\n\n'
        '## Integration documentation\n\n'
        '- [MCP agent guide](/api/mcp-guide): Tools, schemas, examples, workflow and errors.\n'
        '- [Recipe JSON Schema](/api/recipe-schema): Canonical fields, defaults and enums.\n'
        '- [User Manual PDF](/api/guide): Product behavior, ownership and limitations.\n\n'
        '## Connection\n\n'
        'Streamable HTTP MCP endpoint: `/mcp/`. Public tools require no login.\n'
        'The MCP resource `sortiestarter://integration-guide` contains the same agent guide.\n',
        headers={'Cache-Control': 'no-store'})


ROADMAP_MD = Path(__file__).parent.parent / "docs" / "ROADMAP.md"


ROADMAP_HTML = Path(__file__).parent.parent / "docs" / "roadmap.html"


@router.get("/api/roadmap")
def roadmap(request: Request):
    """The roadmap is the OWNER'S page now (v1.93.0). It used to ship public;
    Rob: "not for people to read AI implementation thoughts." The old address
    sends the owner to the admin copy and everyone else to the login page —
    which is the same redirect, because the admin decides who is who."""
    return RedirectResponse("/admin/roadmap", status_code=303)


PACKFORMAT_HTML = Path(__file__).parent.parent / "docs" / "packformat.html"


PACKFORMAT_MD = Path(__file__).parent.parent / "docs" / "PACK_FORMAT.md"


@router.get("/api/packformat")
def packformat():
    """The pack format specification — what a publishable unit of content is.

    The format has claimed to be public since v1.79.0: "a .sspack is a file
    somebody can hand to a friend, publish, or sell, and it may come from
    someone other than us." That commitment was only half kept while the
    document defining it lived in a repository nobody outside has. This is the
    other half.

    Built from docs/PACK_FORMAT.md by scripts/build_packformat_html.py; falls
    back to the Markdown, same contract as /api/sources. The Markdown is
    normative — where this page and the spec disagree, the spec wins, and the
    page is a build artifact that has drifted."""
    if PACKFORMAT_HTML.exists():
        return HTMLResponse(_ga.inject(PACKFORMAT_HTML.read_text()))
    return FileResponse(str(PACKFORMAT_MD), filename="PACK_FORMAT.md",
                        media_type="text/markdown")


@router.get("/api/whatsnew")
def whatsnew_gone():
    """Retired in v1.105.0. The page existed to tell returning pilots what
    changed; CHANGELOG.md is the record now and the roadmap says what is
    coming. A 410 rather than a 404 because the address was linked from the
    footer for eighty releases and "this is gone" is more useful than "this
    never existed"."""
    return PlainTextResponse(
        "What's new was retired in v1.105.0. The changelog is the record: "
        "https://github.com/rgrady/DCS-Mission-Starter/blob/main/CHANGELOG.md",
        status_code=410)


DOCS_IMG = Path(__file__).parent.parent / "docs" / "img"


CORRIDOR_CHARTS = {"nevada": "nttr_corridors", "syria": "syria_corridors", "germany": "germany_corridors"}


def _corridor_chart(map_key: str, fmt: str):
    """The corridor chart for a map (corridor_chart.py): the areas, the
    coast and borders, every corridor with its block, the gates and fixes.
    PNG is served from the committed docs image (scripts/build_corridor_charts.py,
    registered in scripts/artifacts.py) so the chart on the site is the one in
    the repo, rendered on the fly only if that file is missing; SVG is vector."""
    from missiongen import corridors as _cor
    if map_key not in CORRIDOR_CHARTS or not _cor.has(map_key):
        raise HTTPException(status_code=404, detail="no corridor chart for that map")
    stem = CORRIDOR_CHARTS[map_key]
    from missiongen import corridor_chart as _cc
    if fmt == "svg":
        f = DOCS_IMG / f"{stem}.svg"
        body = f.read_text() if f.exists() else _cc.render_svg(*_cc.page_size(map_key), mk=map_key)
        return Response(content=body, media_type="image/svg+xml")
    f = DOCS_IMG / f"{stem}.png"
    if f.exists():
        return FileResponse(str(f), media_type="image/png", filename=f.name)
    import io
    buf = io.BytesIO()
    _cc.render_page(*_cc.page_size(map_key), mk=map_key).save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")


@router.get("/api/corridors/{map_key}/chart.png")
def corridor_chart_png(map_key: str):
    return _corridor_chart(map_key, "png")


@router.get("/api/corridors/{map_key}/chart.svg")
def corridor_chart_svg(map_key: str):
    return _corridor_chart(map_key, "svg")


@router.get("/api/nttr/chart.png")
def nttr_chart_png():
    """v1.100.0 name for the Nevada chart; kept."""
    return _corridor_chart("nevada", "png")


@router.get("/api/nttr/chart.svg")
def nttr_chart_svg():
    return _corridor_chart("nevada", "svg")


SOURCES_HTML = Path(__file__).parent.parent / "docs" / "sources.html"


SOURCES_MD = Path(__file__).parent.parent / "docs" / "SOURCES.md"


@router.get("/api/sources")
def sources():
    """Where the facts came from — the product's bibliography.

    This product asserts a lot of specific things: a SAM's engagement radius, a
    stand's painted heading, the bearing of a 1981 raid, a contrast ratio. Each
    is measured, cited, or an admitted estimate, and shipping the distinction
    is the point. Built from docs/SOURCES.md by scripts/build_sources_html.py;
    falls back to the Markdown, same contract as /api/roadmap."""
    if SOURCES_HTML.exists():
        return HTMLResponse(_ga.inject(_with_thanks(SOURCES_HTML.read_text())))
    return FileResponse(str(SOURCES_MD), filename="SOURCES.md",
                        media_type="text/markdown")


@router.get("/api/credits")
def credits_json():
    """The Thanks list as data, for anyone who wants it without the page."""
    from missiongen import credits as _cr
    return {"credits": [{k: c.get(k, "") for k in ("name", "note", "url")}
                        for c in _cr.load()]}


def _with_thanks(page: str) -> str:
    """Inject the owner-curated Thanks list into the served Sources page.

    Injected at REQUEST time rather than baked into docs/sources.html, because
    that file is a build artifact: `tests/test_sources.py` asserts it is
    byte-identical to what the generator produces, and `scripts/release.sh`
    rebuilds it. Baking an editable list into it would mean the owner could not
    add a name without a deploy, and that a release would silently wipe
    whatever they had added. See missiongen/credits.py for the reasoning.

    Everything here is escaped: a credit's name and note are owner-supplied
    free text, and the URL is https-only at the storage layer."""
    import html as _h
    try:
        from missiongen import credits as _cr
        rows = _cr.load()
    except Exception:
        return page
    if not rows:
        return page
    items = []
    for c in rows:
        name = _h.escape(c.get("name", ""))
        if c.get("url"):
            name = f'<a href="{_h.escape(c["url"])}" rel="noopener">{name}</a>'
        note = _h.escape(c.get("note", ""))
        items.append(f"<li><b>{name}</b>{' — ' + note if note else ''}</li>")
    block = ("<h2>Thanks</h2><p>This tool stands on a lot of other people's "
             "work. Some of it is code we vendored and some of it is the "
             "reason anybody knows how to fly these aircraft at all.</p><ul>"
             + "".join(items) + "</ul>")
    marker = "</div></body></html>"
    return page.replace(marker, block + marker, 1) if marker in page else page + block


@router.get("/api/guide")
def guide_download():
    """Downloadable Sortie Starter documentation (professional PDF)."""
    return FileResponse(str(DOCS_PDF), filename="DCS_Mission_Starter_Guide.pdf",
                        media_type="application/pdf")
