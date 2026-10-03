"""DCS Sortie Starter — API server.

Run:  uvicorn server.app:app --reload
Then open http://127.0.0.1:8000
"""
import logging

from fastapi import APIRouter, Response

from missiongen import __version__
from missiongen.resolver import load_json, validate_data_packs

log = logging.getLogger("missionstarter")

from .mission_routes import _event_counts
from .catalog_routes import flyable_aircraft

router = APIRouter()

@router.get("/api/health")
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

