"""DCS Sortie Starter — API server.

Run:  uvicorn server.app:app --reload
Then open http://127.0.0.1:8000
"""
import logging

from fastapi import APIRouter
from pydantic import BaseModel


log = logging.getLogger("missionstarter")


router = APIRouter()

class CommPlanCheck(BaseModel):
    comms: dict | None = None
    aircraft: str | None = None


@router.get("/api/commplan")
def commplan_table(aircraft: str | None = None, bb_tanker: bool = True,
                   bb_awacs: bool = True, bb_carrier: bool = False,
                   carrier_cap: bool = False, carrier_aew: bool = False):
    from missiongen import commplan as _cp
    ut = _cp.unit_type_for(aircraft)
    present = {"bb_tanker": bb_tanker, "bb_awacs": bb_awacs, "bb_carrier": bb_carrier,
               "carrier_cap": carrier_cap, "carrier_aew": carrier_aew}
    return {"rows": _cp.rows(ut, present), "radios": _cp.radios_for(ut),
            "aircraft_known": ut is not None}


@router.post("/api/commplan/validate")
def commplan_validate(req: CommPlanCheck):
    from missiongen import commplan as _cp
    return _cp.validate(req.comms, _cp.unit_type_for(req.aircraft))

