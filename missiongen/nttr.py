"""NTTR corridors — the Nevada face of corridors.py.

v1.99.0 built this for Nellis alone; v1.102.0 generalised it to one data
file per map (data/corridors/<map>.json) so the Syria map could have the
same Authentic standard map detail. Everything here delegates to
corridors.py with map_key="nevada"; the names are kept because the tests,
the builder and the docs learned them first. Read corridors.py for the how.
"""
from __future__ import annotations

from . import corridors as _c

NM = _c.NM
FT = _c.FT


def data() -> dict:
    return _c.data("nevada")


def fix(name: str) -> dict:
    return _c.fix(name, "nevada")


def corridor(cid: str) -> dict:
    return _c.corridor(cid, "nevada")


def sector_for(lat: float, lon: float) -> str:
    return _c.sector_for(lat, lon, "nevada", "nellis")


def mode_for(era: str) -> str:
    return _c.mode_for(era)


def plan_route(home_pos, target_pos, era: str, rng, terrain, map_key: str = "nevada",
               home_name: str | None = None):
    if map_key != "nevada":
        return None
    if home_name is None and home_pos is not None:
        # the NTTR tests hand in a bare position: Nellis is "in the cluster"
        # when the position is inside its terminal area
        ll = home_pos.latlng()
        home_name = "Nellis" if _c.sector_for(ll.lat, ll.lng, "nevada", "nellis") == "local" else ""
    return _c.plan_route(home_pos, target_pos, era, rng, terrain, "nevada", home_name)


summary = _c.summary
approx_fixes = _c.approx_fixes
brief_lines = _c.brief_lines
known_issue_lines = _c.known_issue_lines


def draw(m, plan=None):
    return _c.draw(m, plan, "nevada")
