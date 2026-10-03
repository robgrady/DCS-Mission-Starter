"""The airfield guide: the page every commercial campaign's Doc folder has and
we did not — channelization, runways, elevation, parking and the divert
order, for the fields this mission uses.

ALL OF IT COMES OUT OF THE TERRAIN. pydcs holds, per airport: the ATC radio
in four bands (HF, VHF-low, VHF-high, UHF), every runway by name with both
ends, every parking stand with its height, and the position. Nothing here
is typed in by hand, so the guide cannot disagree with the field DCS will
actually give you — the comm plan's own note ("field ATC per DCS
auto-assign, see the airfield page") finally points at a page that has it.

WHAT IS NOT HERE, AND SAID SO. TACAN channels and ILS frequencies are not
exposed by pydcs (it carries beacon IDs, not what they broadcast). Until a
per-map navaid table exists — the honest source is the terrain module's own
Beacons.lua — the guide prints no TACAN/ILS column rather than a guessed
one. See `navaids()`.

ELEVATION IS A TABLE, NOT A GUESS. pydcs carries no elevation at all —
`ParkingSlot.height` is the stand's clearance height (6–18 m), and
pattern.py mistook it for field elevation until v1.107.0: harmless on the
Caucasus, 1,800 ft underground at Nellis. data/airfield_elevations.json
holds published field elevations per map; a field not in it has NO
elevation on record, prints "—" here, and gets no airborne pattern spawn.
"""
from __future__ import annotations

import math

NM = 1852.0
FT = 3.28084


def _mhz(hz) -> float | None:
    try:
        v = float(hz)
    except (TypeError, ValueError):
        return None
    return round(v / 1e6, 3) if v > 0 else None


def atc(airport) -> dict:
    """{uhf, vhf, vhf_low, hf} in MHz, None where the field has no radio in
    that band (a FARP, a grass strip)."""
    r = getattr(airport, "atc_radio", None)
    if not r:
        return {"uhf": None, "vhf": None, "vhf_low": None, "hf": None}
    return {"uhf": _mhz(r.uhf_hz), "vhf": _mhz(r.vhf_high_hz),
            "vhf_low": _mhz(r.vhf_low_hz), "hf": _mhz(r.hf_hz)}


def runways(airport) -> list[dict]:
    """One entry per runway: name "07-25", the two ends with their headings."""
    out = []
    for rw in getattr(airport, "runways", []) or []:
        try:
            out.append({"name": rw.name,
                        "ends": [(rw.main.name, int(rw.main.heading)),
                                 (rw.opposite.name, int(rw.opposite.heading))]})
        except AttributeError:
            out.append({"name": str(getattr(rw, "name", "?")),
                        "ends": [("?", int(getattr(rw, "heading", 0)))]})
    return out


_ELEV = None


def _elev_table() -> dict:
    global _ELEV
    if _ELEV is None:
        from .resolver import load_json
        try:
            _ELEV = load_json("airfield_elevations")
        except Exception:
            _ELEV = {}
    return _ELEV


def elevation_ft(airport, map_key: str | None = None) -> int | None:
    """Published field elevation in feet, or None when none is on record.
    Never derived from the terrain object: it has nothing to derive from."""
    t = _elev_table()
    maps = [map_key] if map_key else [k for k in t if not k.startswith("_")]
    for mk in maps:
        v = ((t.get(mk) or {}).get("fields") or {}).get(getattr(airport, "name", ""))
        if v is not None:
            return int(v)
    return None


def elevation_m(airport, map_key: str | None = None) -> float | None:
    ft = elevation_ft(airport, map_key)
    return None if ft is None else ft / FT


def range_bearing(frm, to) -> tuple[float, int]:
    dx = to.position.x - frm.position.x
    dy = to.position.y - frm.position.y
    return math.hypot(dx, dy) / NM, int(round(math.degrees(math.atan2(dy, dx)) % 360)) % 360


def navaids(airport) -> dict | None:
    """TACAN / ILS for this field, when a navaid table exists for the map.
    None today — pydcs does not carry what the beacons broadcast."""
    return None


def row(airport, home=None, map_key: str | None = None) -> dict:
    d = {"name": airport.name, "atc": atc(airport), "runways": runways(airport),
         "elev_ft": elevation_ft(airport, map_key), "stands": len(getattr(airport, "parking_slots", []) or []),
         "navaids": navaids(airport), "home": bool(home is not None and airport.name == home.name)}
    if home is not None and not d["home"]:
        d["range_nm"], d["bearing"] = range_bearing(home, airport)
    else:
        d["range_nm"], d["bearing"] = 0.0, None
    return d


def rows(own_fields, home=None, enemy_fields=(), map_key: str | None = None) -> dict:
    """{"own": [...home first, then by range...], "enemy": [...]}."""
    own = [row(ap, home, map_key) for ap in own_fields]
    own.sort(key=lambda r: (not r["home"], r["range_nm"]))
    enemy = [row(ap, home, map_key) for ap in enemy_fields]
    enemy.sort(key=lambda r: r["range_nm"])
    return {"own": own, "enemy": enemy}


# --- formatting shared by the brief, the kneeboard and the markdown --------

def fmt_mhz(v) -> str:
    return f"{v:.3f}" if v else "—"


def fmt_rwy(r: dict, with_heading: bool = False, first_only: bool = False) -> str:
    """"07/25" or, with headings, "07 (071) / 25 (251)"; several runways
    joined by two spaces, or only the first with `first_only`."""
    if not r["runways"]:
        return "—"
    parts = []
    for rw in (r["runways"][:1] if first_only else r["runways"]):
        if with_heading:
            parts.append(" / ".join(f"{n} ({h:03d})" for n, h in rw["ends"]))
        else:
            parts.append("/".join(n for n, _ in rw["ends"]))
    return "  ".join(parts)


def nordo_line(table: dict, home_name: str) -> str:
    """One sentence for the brief: where to go with no radio."""
    own = table["own"]
    alt = next((r for r in own if not r["home"]), None)
    home = next((r for r in own if r["home"]), None)
    if home is None:
        return "NORDO: recover at the ship per the comm ladder — Marshal, then the pattern."
    rw = home["runways"][0]["ends"][0][0] if home["runways"] else "the active"
    s = f"NORDO: squawk 7600, return to {home_name}, overhead for RWY {rw}, rock wings on initial."
    if alt:
        s += f" Alternate {alt['name']} {alt['bearing']:03d}° / {alt['range_nm']:.0f} nm."
    return s
