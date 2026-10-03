"""Compose the HTTP application; route modules own transport responsibilities."""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from . import artifact_service
from . import ROOT as _root
from missiongen import __version__
from . import site_routes, catalog_routes, document_routes, comm_routes
from . import health_routes, mission_routes, library_routes, contact_routes
from .admin import router as admin_router

app = FastAPI(title="DCS Sortie Starter", version=__version__)
app.mount("/assets", StaticFiles(directory=_root / "frontend" / "assets"), name="assets")
for module in (site_routes, catalog_routes, document_routes, comm_routes,
               health_routes, mission_routes, library_routes, contact_routes):
    app.include_router(module.router)
app.include_router(admin_router)
app.add_exception_handler(404, site_routes.not_found)

# Historical Python imports remain available; new code imports the owning module.
from .artifact_service import (generate, USER_ERRORS, _HEADER_TRANSLIT, _header_safe, _build_and_respond)  # noqa: F401,E402
from .site_routes import (FRONTEND, FONT_DIR, font_file, NOTFOUND, not_found, index)  # noqa: F401,E402
from .catalog_routes import (_theme_mix, flyable_aircraft, options)  # noqa: F401,E402
from .document_routes import (DOCS_PDF, ROADMAP_MD, ROADMAP_HTML, roadmap, PACKFORMAT_HTML, PACKFORMAT_MD, packformat, whatsnew_gone, DOCS_IMG, CORRIDOR_CHARTS, _corridor_chart, corridor_chart_png, corridor_chart_svg, nttr_chart_png, nttr_chart_svg, SOURCES_HTML, SOURCES_MD, sources, credits_json, _with_thanks, guide_download)  # noqa: F401,E402
from .comm_routes import (CommPlanCheck, commplan_table, commplan_validate)  # noqa: F401,E402
from .health_routes import (health)  # noqa: F401,E402
from .mission_routes import (api_download_by_code, api_recipe_schema, GenerateRequest, EventRequest, EVENTS, _event_counts, api_event, api_generate, api_brief, _KB_TITLES, _KB_README, api_kneeboard)  # noqa: F401,E402
from .library_routes import (_published_tracks, _pack_templates, TRACK_DOCS, api_track_guide, api_courses, api_course, api_course_reading, api_course_kit, _track_pack_or_none, api_track_zip, api_pack_file, _pack_all_zip)  # noqa: F401,E402
from .contact_routes import (_CONTACT_SECRET, _CONTACT_MIN_SECONDS, _CONTACT_TOKEN_TTL, _CONTACT_HOURLY, _CONTACT_DAILY, _contact_hits, _contact_sign, _contact_rate_ok, ContactRequest, api_contact_token, api_contact)  # noqa: F401,E402

@app.middleware("http")
async def release_identity_cache(request, call_next):
    response = await call_next(request)
    if request.url.path in {"/api/options", "/api/health", "/api/guide"}:
        response.headers["Cache-Control"] = "no-store"
    return response

from .catalog_owner import install as install_catalog_owner
install_catalog_owner(app)
