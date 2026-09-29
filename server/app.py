"""DCS Sortie Starter — API server.

Run:  uvicorn server.app:app --reload
Then open http://127.0.0.1:8000
"""
import hashlib
import json
import logging
import os
import secrets
import shutil
import sys
import tempfile
import time as _time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import (RedirectResponse, FileResponse, HTMLResponse,
                               JSONResponse, PlainTextResponse)
from starlette.background import BackgroundTask
from pydantic import BaseModel

_root = Path(__file__).parent.parent
sys.path.insert(0, str(_root))
if (_root / "vendor" / "dcs").exists():          # vendored pydcs (Mac/no-network installs)
    sys.path.insert(0, str(_root / "vendor"))
from missiongen import Recipe, generate, __version__
from missiongen.recipe import Recipe, RECIPE_ENUMS, RecipeError
from missiongen.builder import EraViolation
from missiongen.resolver import load_json, validate_data_packs, UnknownUnitError
from missiongen import deck as _deck
from missiongen import contact as contact_store
from missiongen import tracks as _tracks_mod
from missiongen import courses as _courses_mod
from missiongen import aar as _aar_mod

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


# HTTP header values are latin-1 by spec, and Starlette enforces it. The engine
# writes prose — with em dashes, multiplication signs and middots — straight
# into X-Warnings, so ONE warning containing a typographic character turned the
# whole response into a 500 and the user got no mission at all. That is exactly
# what "Carrier tanker is the KA-6D (A-6E) — the air wing's own gas" did: every
# carrier mission with a tanker, including the Library's Carrier Qualification,
# failed to download. Transliterate what we can, then hard-encode as a net.
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
    from missiongen import loadouts as _lo
    kit = {
        "kneeboard_pages": stats.get("kneeboard_pages", 0),
        "dtc": bool(stats.get("dtc_units_tagged")),
        "route": stats.get("route"),
        # The clock the route is anchored on ("tot 06:42:00"), when timed.
        "timing": (f"{stats['timing'].get('anchor')} "
                   f"{stats['timing'].get('anchor_clock') or stats['timing'].get('takeoff_clock') or ''}").strip()
                  if stats.get("timing") else None,
        "bfm": stats.get("bfm"),
        "threat_level": stats.get("threat_level"),
        "support": stats.get("support", [])[:6],
        # What the bandits are CARRYING. Correct-but-invisible is how the last
        # three features became discovery problems, so the fit surfaces on the
        # Mission Kit panel too, not only inside the documents.
        # YOUR fit. The user never sees a pylon picker, so the one place
        # they learn what they took off with is here and the brief.
        "player_loadout": stats.get("player_loadout"),
        "player_role": stats.get("player_loadout_role"),
        "enemy_air": [{"n": a["count"], "t": a["type"],
                       "r": _lo.ROLE_TAGS.get(a["role"], a["role"]),
                       "fit": a["fit"], "imp": a["implication"]}
                      for a in _lo.summarize(stats.get("enemy_air"))[:3]],
    }
    # The header has a hard budget and a TRUNCATED payload is worse than a
    # missing one (JSON.parse fails, the panel silently loses every row), so
    # shed enemy_air rows until it fits instead of slicing the string.
    while len(json.dumps(kit)) > 1800 and kit["enemy_air"]:
        kit["enemy_air"].pop()
    return FileResponse(str(out), filename=fname, media_type="application/zip",
                        headers={"X-Warnings": _header_safe(
                                     "; ".join(result["warnings"]))[:900],
                                 "X-Kit": json.dumps(kit)},
                        background=BackgroundTask(shutil.rmtree, tmpdir, ignore_errors=True))

from . import ga as _ga

FRONTEND = Path(__file__).parent.parent / "frontend" / "index.html"
FONT_DIR = Path(__file__).parent.parent / "missiongen" / "data" / "brand" / "fonts"


@app.get("/fonts/{name}")
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


@app.exception_handler(404)
async def not_found(request, exc):
    """404s split by audience: API clients keep the JSON contract they parse;
    a human who fat-fingers a URL gets the radar scope with the missing
    contact instead of a bare {"detail":"Not Found"}."""
    from fastapi.responses import JSONResponse
    if request.url.path.startswith("/api/") or not NOTFOUND.exists():
        return JSONResponse({"detail": "Not Found"}, status_code=404)
    return HTMLResponse(_ga.inject(NOTFOUND.read_text()), status_code=404)


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
    return _ga.inject(FRONTEND.read_text())


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
            # starters (north star: no flight plan you did not ask for —
            # strike routes, training syllabi and the opt-in tickbox are the
            # three asks), most
            # with a suggested-tasking brief; crew-ops are full missions.
            **{k: {"label": v["label"], "eras": v.get("eras", []),
                   "maps": v.get("maps"), "needs_carrier": v.get("needs_carrier", False),
                   "needs_acls": v.get("needs_acls", False),
                   "recipe": v.get("recipe", {}),
                   # per-era overrides (see missiongen/templates.py): a card that
                   # spans eras cannot pin one aircraft
                   "by_era": v.get("by_era") or {},
                   # per-era list of airframes this card is willing to fly.
                   # Formation training uses it so the Library can offer a
                   # choice instead of pinning one jet — the syllabus is
                   # airframe-agnostic and pinning made it look F-16-only.
                   "aircraft_choices": v.get("aircraft_choices") or {},
                   # Track membership. The Library uses it to keep a track's
                   # rides OUT of the loose grid — without it every ride shows
                   # twice, once in its track and once alphabetically.
                   "track": v.get("track"),
                   "kind": (v.get("library") or {}).get("kind", "open"),
                   "tasked": bool(v.get("brief")),
                   # quick: owned by the Quick Flight picker, hidden in Library
                   "quick": v.get("quick", False),
                          "library": v.get("library"), "default_map": v.get("default_map")}
               for k, v in load_json("mission_templates").items()
               # Pack reconciliation: a pack card only exists if its .miz
               # actually shipped. A deploy without packs/ (e.g. the core zip
               # alone) hides the cards instead of showing twelve broken
               # download buttons; /api/health lists what's missing.
               if not k.startswith("_")},
            # packs live on the volume, uploaded via /admin — merged in here so
            # the Library treats them exactly like built-in templates
            **_pack_templates(),
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
        # Training tracks: ordered sets of the cards above. The Library renders
        # one grouped card per track instead of eleven loose ones, and each
        # ride still opens as the ordinary card it is.
        # `published` says whether a whole-syllabus download exists for this
        # track — i.e. whether somebody has produced and uploaded its pack.
        # Without it the UI would keep offering a button that now answers 409,
        # which is a worse experience than the 502 it replaced: at least the
        # 502 looked like a failure.
        "tracks": _published_tracks(),
        # Training COURSES: the pipeline above the tracks (missiongen/courses.py).
        # Summaries only; the Pipeline door fetches a course in full on open.
        "courses": _courses_mod.summaries(),
        # Tanker labels and track figures, so the wizard can name what it is
        # offering instead of printing a key like "kc135mprs".
        "tankers": {k: {"label": v["label"], "boom": v["boom"],
                        "ias_kt": v["ias_kt"], "alt_ft": v["alt_ft"],
                        "callsign": v["callsign"]}
                    for k, v in _aar_mod.TANKERS.items()},
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
            # "air" was omitted here because air starts used to be
            # template-only. They are not any more — the formation syllabus
            # REQUIRES one — and a value the engine accepts but the UI never
            # offers is worse than either: opening an air-start card in the
            # Builder set `start = "air"` on a <select> with no such option, so
            # the control silently showed nothing and the setting was lost the
            # moment anything else was changed.
            "start": list(RECIPE_ENUMS["start"]),
            "time_of_day": ["dawn", "day", "dusk", "night"],
            "weather": ["clear", "scattered", "overcast", "storm"],
            "density": ["sparse", "normal", "busy"],
            "pattern_mode": ["landing", "takeoff", "both"],
            "pattern_kind": ["fighter", "cargo", "helicopter", "mixed"],
        },
    }


DOCS_PDF = Path(__file__).parent.parent / "docs" / "DCS_Mission_Starter_Guide.pdf"
ROADMAP_MD = Path(__file__).parent.parent / "docs" / "ROADMAP.md"


ROADMAP_HTML = Path(__file__).parent.parent / "docs" / "roadmap.html"


@app.get("/api/roadmap")
def roadmap(request: Request):
    """The roadmap is the OWNER'S page now (v1.93.0). It used to ship public;
    Rob: "not for people to read AI implementation thoughts." The old address
    sends the owner to the admin copy and everyone else to the login page —
    which is the same redirect, because the admin decides who is who."""
    return RedirectResponse("/admin/roadmap", status_code=303)


PACKFORMAT_HTML = Path(__file__).parent.parent / "docs" / "packformat.html"
PACKFORMAT_MD = Path(__file__).parent.parent / "docs" / "PACK_FORMAT.md"


@app.get("/api/packformat")
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


# --------------------------------------------------------------------------- #
# The comm table (missiongen/commplan.py): the standard ladder as rows the
# pilot can overwrite. GET describes the table for an airframe and a set of
# building blocks; POST validates a set of overrides the same way
# Recipe.validate will, so the page can refuse a bad cell before Build does.
# --------------------------------------------------------------------------- #
class CommPlanCheck(BaseModel):
    comms: dict | None = None
    aircraft: str | None = None


@app.get("/api/commplan")
def commplan_table(aircraft: str | None = None, bb_tanker: bool = True,
                   bb_awacs: bool = True, bb_carrier: bool = False,
                   carrier_cap: bool = False, carrier_aew: bool = False):
    from missiongen import commplan as _cp
    ut = _cp.unit_type_for(aircraft)
    present = {"bb_tanker": bb_tanker, "bb_awacs": bb_awacs, "bb_carrier": bb_carrier,
               "carrier_cap": carrier_cap, "carrier_aew": carrier_aew}
    return {"rows": _cp.rows(ut, present), "radios": _cp.radios_for(ut),
            "aircraft_known": ut is not None}


@app.post("/api/commplan/validate")
def commplan_validate(req: CommPlanCheck):
    from missiongen import commplan as _cp
    return _cp.validate(req.comms, _cp.unit_type_for(req.aircraft))


@app.get("/api/whatsnew")
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


@app.get("/api/corridors/{map_key}/chart.png")
def corridor_chart_png(map_key: str):
    return _corridor_chart(map_key, "png")


@app.get("/api/corridors/{map_key}/chart.svg")
def corridor_chart_svg(map_key: str):
    return _corridor_chart(map_key, "svg")


@app.get("/api/nttr/chart.png")
def nttr_chart_png():
    """v1.100.0 name for the Nevada chart; kept."""
    return _corridor_chart("nevada", "png")


@app.get("/api/nttr/chart.svg")
def nttr_chart_svg():
    return _corridor_chart("nevada", "svg")


SOURCES_HTML = Path(__file__).parent.parent / "docs" / "sources.html"
SOURCES_MD = Path(__file__).parent.parent / "docs" / "SOURCES.md"


@app.get("/api/sources")
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


@app.get("/api/credits")
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
    from missiongen.dressing import livery_pack_verified
    return {"ok": not errors, "version": __version__,
            "data_pack_errors": errors, "service_data_gaps": gaps,
            # Guessed livery ids are NOT written into missions. False here means
            # parked statics wear DCS stock skins; run scripts/dump_liveries.py
            # against a real install to verify the pack and switch them on.
            "liveries_verified": livery_pack_verified(),
            # installed mission packs (volume-backed, uploaded via /admin)
            "packs": [{"id": p["id"], "missions": len(p.get("events", [])),
                       "mb": p.get("size_mb")} for p in __import__(
                           "missiongen.packs", fromlist=["packs"]).list_packs()],
            # feature-interest tallies since this process started (see /api/ev).
            # Aggregate counts only — no identifiers, nothing per-user.
            "signals": dict(_event_counts)}


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
    return _build_and_respond(recipe, source="share")


class GenerateRequest(BaseModel):
    recipe: dict
    # Which door the request came through (builder | library | quick). Used
    # ONLY for the no-PII analytics ledger; unknown/absent values fall back to
    # "api" so a stale client can't invent categories.
    source: str = "api"
    # Anonymous visitor id: a random UUID the browser made up about itself.
    # Absent when the visitor opted out or sent Do Not Track. Stored hashed.
    visitor: str | None = None


class EventRequest(BaseModel):
    event: str


# Demand signals only — an allowlist, so this can never become a general
# analytics sink. Per claude/analytics-plan.md: NO IP, NO identifiers, NO PII.
# We log a counted line and hold a process-local tally; nothing is persisted,
# which sidesteps the ephemeral-filesystem question entirely.
EVENTS = ("want_mixed_flight", "qf_open", "qf_reroll")
_event_counts: dict = {}


@app.post("/api/ev")
def api_event(req: EventRequest):
    """Record an interest click on a feature that doesn't exist yet.

    Deliberately minimal: no request body beyond the event name, nothing about
    who sent it. Unknown names are dropped silently so a stale client (or a
    bot) can't fill the log."""
    if req.event in EVENTS:
        _event_counts[req.event] = _event_counts.get(req.event, 0) + 1
        log.info("ev %s n=%d", req.event, _event_counts[req.event])
    return {"ok": True}


@app.post("/api/generate")
def api_generate(req: GenerateRequest):
    try:
        recipe = Recipe.from_dict(req.recipe)     # validates enums/bounds
    except USER_ERRORS as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _build_and_respond(recipe, source=req.source, visitor=req.visitor)


# --------------------------------------------------------------------------- #
# Mission packs — uploaded through /admin, stored on the volume (see
# missiongen/packs.py). Nothing pack-related is baked into the image.
# --------------------------------------------------------------------------- #
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


# --------------------------------------------------------------------------- #
# Training tracks — ordered sets of GENERATED cards that travel together.
# Unlike packs these ship with the code: no volume, no upload, no admin
# password. See missiongen/tracks.py for why the two are separate things.
# --------------------------------------------------------------------------- #
TRACK_DOCS = Path(__file__).parent.parent / "docs"


@app.get("/api/track/{track}/guide.pdf")
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


# --------------------------------------------------------------------------- #
# Training courses — the pipeline above the tracks (missiongen/courses.py).
# Read-only, public, no state: progress lives in the student's browser and
# the squadron's gradesheet, which is the kit.
# --------------------------------------------------------------------------- #
@app.get("/api/courses")
def api_courses():
    return _courses_mod.summaries()


@app.get("/api/course/{course}")
def api_course(course: str):
    try:
        c = _courses_mod.resolve(course)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not c:
        raise HTTPException(status_code=404, detail="Not Found")
    return c


@app.get("/api/course/{course}/reading/{doc}")
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


@app.get("/api/course/{course}/kit.zip")
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


@app.get("/api/track/{track}/all.zip")
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


@app.get("/api/pack/{pack}/{fname:path}")
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
    from missiongen import analytics
    analytics.record("brief", req.source, recipe, visitor=req.visitor)
    return FileResponse(str(pack), filename=f"{stem}_briefing_pack.zip",
                        media_type="application/zip",
                        background=BackgroundTask(shutil.rmtree, tmpdir, ignore_errors=True))


# The page titles, in the order build_kneeboard() emits them. Used only to name
# the exported files; the renderer stays the single source of the pages
# themselves. Optional pages are appended, so a short list is normal.
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


@app.post("/api/kneeboard")
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


# ---------------------------------------------------------------- contact
# The product's only inbound channel (docs/contact-form-spec.md). Public and
# unauthenticated, therefore a spam magnet — three layers of defense, none of
# them a CAPTCHA (an accessibility tax we will not levy after shipping AA):
#   1. honeypot field bots fill and humans never see
#   2. a signed issue-time, so a sub-3-second submit is rejected as a machine
#   3. a per-IP rate limit whose key is held IN MEMORY and never written down
# Rejections 1 and 2 return the SAME success shape as a real submit: telling a
# bot why it failed is free tuning advice for the bot.
_CONTACT_SECRET = os.environ.get("CONTACT_SECRET") or secrets.token_hex(16)
_CONTACT_MIN_SECONDS = 3
_CONTACT_TOKEN_TTL = 60 * 60 * 4          # a form left open over lunch still works
_CONTACT_HOURLY, _CONTACT_DAILY = 5, 20
_contact_hits: dict = {}


def _contact_sign(issued: int) -> str:
    import hmac as _hmac
    return _hmac.new(_CONTACT_SECRET.encode(), str(issued).encode(),
                     hashlib.sha256).hexdigest()[:32]


def _contact_rate_ok(ip: str) -> bool:
    """Token bucket keyed by IP. The IP lives in this dict and nowhere else —
    it is never persisted, which is what keeps the no-PII stance true even
    though this endpoint accepts personal data by design."""
    now = _time.time()
    hits = [t for t in _contact_hits.get(ip, []) if now - t < 86400]
    if len(hits) >= _CONTACT_DAILY:
        return False
    if len([t for t in hits if now - t < 3600]) >= _CONTACT_HOURLY:
        return False
    hits.append(now)
    _contact_hits[ip] = hits
    if len(_contact_hits) > 4096:         # bound the dict; oldest keys go
        for k in list(_contact_hits)[:1024]:
            _contact_hits.pop(k, None)
    return True


class ContactRequest(BaseModel):
    name: str = ""
    email: str = ""
    topic: str = ""
    comment: str = ""
    context: dict | None = None
    issued: int = 0
    sig: str = ""
    website: str = ""          # honeypot: labelled plausibly, hidden in CSS


@app.get("/api/contact/token")
def api_contact_token():
    """Issued when the form opens; proves on submit that a human spent time
    in it. Signed so the client cannot backdate itself."""
    issued = int(_time.time())
    return {"issued": issued, "sig": _contact_sign(issued),
            "topics": [{"value": t, "label": contact_store.TOPIC_LABELS[t]}
                       for t in contact_store.TOPICS],
            "max_comment": contact_store.MAX_COMMENT}


@app.post("/api/contact")
def api_contact(req: ContactRequest, request: Request):
    accepted = {"ok": True}               # the shape every rejection mimics
    # 1. honeypot
    if req.website.strip():
        log.info("contact: honeypot")
        return accepted
    # 2. signed issue-time
    import hmac as _hmac
    if not _hmac.compare_digest(req.sig or "", _contact_sign(req.issued)):
        log.info("contact: bad token")
        return accepted
    age = _time.time() - req.issued
    if age < _CONTACT_MIN_SECONDS or age > _CONTACT_TOKEN_TTL:
        log.info("contact: token age %.1fs", age)
        return accepted
    # 3. rate limit — the one rejection the user is told about, because a real
    # person hitting it needs to know their message did not go through
    ip = (request.client.host if request.client else "?") or "?"
    if not _contact_rate_ok(ip):
        raise HTTPException(status_code=429,
                            detail="That's a lot of messages in a short time. "
                                   "Please try again later.")
    errors = contact_store.validate(req.name, req.email, req.topic, req.comment)
    if errors:
        return JSONResponse(status_code=422, content={"ok": False, "errors": errors})
    ctx = dict(req.context or {})
    ctx["version"] = __version__          # server-stamped: a client-supplied
                                          # version in a bug report is worthless
    mid = contact_store.add(req.name, req.email, req.topic, req.comment, ctx)
    if not mid:
        raise HTTPException(status_code=500,
                            detail="We couldn't save that message. Please try again.")
    log.info("contact: stored %s (%s)", mid, req.topic)
    return {"ok": True}
