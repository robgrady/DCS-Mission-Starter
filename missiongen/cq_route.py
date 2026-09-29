"""The Case III flight plan — geometry hung off the boat, not off a map axis.

WHY THIS IS NOT `wk_route`
--------------------------
The White Knights rides lay their legs along a fixed per-theatre axis from a
home airfield, because a training route you fly ten times should be the same
route ten times. A carrier recovery has no such freedom: every point in it is
defined relative to the ship — a radial and a DME — and the ship is under way.
So the whole geometry here is a function of two runtime facts, the carrier's
position and her base recovery course, and of nothing else.

ONE HAPPY SIMPLIFICATION. `wk_route` has to convert the squadron's AGL floor
into the MSL a waypoint carries, using an estimated ground reference per
theatre, and says so on every card. Over the sea, AGL and MSL are the same
number. Every altitude in this module is both.

THE LINE THE WHOLE APPROACH LIVES ON
------------------------------------
The marshal fix sits on the reciprocal of the final bearing, and the final
approach runs up the extension of the landing-area centerline. Those are the
same line. That is *why* NATOPS can describe the correction from the marshal
radial to the final bearing as a small one — you were never far off it. So a
single unit vector does all the work here: `u` points from the marshal fix
toward the ship along the final bearing, and every gate is the ship minus some
number of miles of `u`.
"""
from __future__ import annotations

from . import cq

NM = cq.NM_M


def _offset(p, dist_m, bearing_deg):
    from .dressing import _offset as _o
    return _o(p, dist_m, bearing_deg)


def ias_to_tas_kt(ias_kt: float, alt_ft: float) -> float:
    from .aar import ias_to_tas_kt as _f
    return _f(ias_kt, alt_ft)


# --------------------------------------------------------------------------- #
# Points on the approach line
# --------------------------------------------------------------------------- #
def point_at_dme(carrier_pos, brc: float, dme: float, cross_nm: float = 0.0):
    """The point `dme` miles from the ship on the marshal radial.

    `cross_nm` displaces it perpendicular to that line, positive to the LEFT of
    the inbound course — which is the side a left-hand holding pattern uses,
    and the only reason this parameter exists.
    """
    p = _offset(carrier_pos, dme * NM, cq.marshal_radial(brc))
    if cross_nm:
        # Left of the inbound course (the final bearing) is final bearing - 90.
        brg = (cq.final_bearing(brc) - 90.0) % 360.0
        p = _offset(p, abs(cross_nm) * NM,
                    brg if cross_nm > 0 else (brg + 180.0) % 360.0)
    return p


# --------------------------------------------------------------------------- #
# The holding pattern
# --------------------------------------------------------------------------- #
# A left-hand racetrack whose INBOUND LEG PASSES OVER THE FIX (§6.4.1.1 says so
# explicitly, and it is how CATCC keeps a stack deconflicted). So the fix is the
# END of the inbound leg, not its middle.
#
# Leg length is one minute at holding speed and turn diameter is what a 180 at
# 30 degrees of bank actually costs — both computed rather than tabled, because
# they change with the stack altitude through true airspeed.
def _turn_diameter_nm(tas_kt: float, bank_deg: float = 30.0) -> float:
    import math
    v = tas_kt * 0.514444                       # m/s
    r = v * v / (9.80665 * math.tan(math.radians(bank_deg)))
    return 2.0 * r / NM


def holding_pattern(carrier_pos, brc: float, angels: int) -> list:
    """[(name, point, alt_ft, kias)] — the racetrack, starting on the inbound leg.

    Laid as waypoints so the F10 map shows the pilot the shape he is supposed
    to be flying. A holding pattern described on a card and absent from the map
    is the say/do gap in its cheapest form.
    """
    dme = cq.marshal_dme(angels)
    alt = angels * 1000
    tas = ias_to_tas_kt(cq.MARSHAL_HOLD_KT, alt)
    leg_nm = tas * (cq.MARSHAL_LEG_MIN / 60.0)
    across = _turn_diameter_nm(tas)
    out_dme = dme + leg_nm
    return [
        ("MARSHAL FIX", point_at_dme(carrier_pos, brc, dme), alt,
         cq.MARSHAL_HOLD_KT),
        ("OUTBOUND ABEAM", point_at_dme(carrier_pos, brc, dme, across), alt,
         cq.MARSHAL_HOLD_KT),
        ("OUTBOUND END", point_at_dme(carrier_pos, brc, out_dme, across), alt,
         cq.MARSHAL_HOLD_KT),
        ("INBOUND START", point_at_dme(carrier_pos, brc, out_dme), alt,
         cq.MARSHAL_HOLD_KT),
    ]


# --------------------------------------------------------------------------- #
# The descent profile
# --------------------------------------------------------------------------- #
def platform_dme(angels: int) -> float:
    """Where 4,000 fpm from the stack arrives at 5,000 feet.

    Not a published gate — NATOPS is explicit that platform is an ALTITUDE —
    but the pilot still needs a waypoint on the map, and telling him where it
    will happen for HIS stack is the point. From the base of the stack it
    arrives about a mile after commencing, which surprises people, and is
    worth them seeing before they fly it rather than after.
    """
    drop_ft = angels * 1000 - cq.PLATFORM_FT
    if drop_ft <= 0:
        return float(cq.marshal_dme(angels))
    minutes = drop_ft / cq.DESCENT_FPM
    tas = ias_to_tas_kt(cq.DESCENT_KT, (angels * 1000 + cq.PLATFORM_FT) / 2)
    return round(cq.marshal_dme(angels) - tas * (minutes / 60.0), 1)


def profile(carrier_pos, brc: float, angels: int) -> list:
    """[(name, point, alt_ft, kias)] from the fix to the ramp."""
    gi = round(cq.glideslope_intercept_nm(), 1)
    rows = [
        ("COMMENCE", cq.marshal_dme(angels), angels * 1000, cq.DESCENT_KT),
        ("PLATFORM", platform_dme(angels), cq.PLATFORM_FT, cq.DESCENT_KT),
        ("LEVEL 10", cq.LEVEL_DME, cq.LEVEL_FT, cq.DESCENT_KT),
        ("DIRTY 8", cq.DIRTY_DME, cq.LEVEL_FT, cq.DESCENT_KT),
        ("ON SPEED 6", cq.ONSPEED_DME, cq.LEVEL_FT, cq.ONSPEED_KT),
        ("GLIDESLOPE", gi, cq.LEVEL_FT, cq.ONSPEED_KT),
        ("THE BALL", cq.BALL_CALL_NM, 280, cq.ONSPEED_KT),
    ]
    return [(n, point_at_dme(carrier_pos, brc, d), a, k) for n, d, a, k in rows]


# --------------------------------------------------------------------------- #
# Per-ride leg tables
# --------------------------------------------------------------------------- #
# Each ride starts where the last one ended, and EVERY ride's plan runs all the
# way to the deck. A pilot who busts the timing on ride 1 still has to land the
# airplane, and a route that stops at the gate under test would leave him with
# no waypoints for the part he is not being graded on.
INBOUND_DME = 60
INBOUND_ALT = 20000
INBOUND_KT = 300


def legs_for(ride_key: str, carrier_pos, brc: float) -> list:
    r = cq.ride(ride_key)
    if not r or carrier_pos is None:
        return []
    angels = r["angels"]
    start = r["start"]
    hold = holding_pattern(carrier_pos, brc, angels)
    prof = profile(carrier_pos, brc, angels)

    if start == "marshal":
        # Cross the fix, fly the pattern once so the shape is on the map, then
        # commence from the fix.
        return hold + [hold[0]] + prof
    if start == "inbound":
        return [("INBOUND", point_at_dme(carrier_pos, brc, INBOUND_DME),
                 INBOUND_ALT, INBOUND_KT)] + hold + [hold[0]] + prof
    if start == "twelve":
        return [("CHECK IN 12", point_at_dme(carrier_pos, brc, cq.ARC_DME),
                 cq.LEVEL_FT, cq.DESCENT_KT)] + [p for p in prof
                                                 if p[0] not in
                                                 ("COMMENCE", "PLATFORM")]
    if start == "final":
        return [p for p in prof if p[0] in ("GLIDESLOPE", "THE BALL")]
    return prof


def start_state(ride_key: str, carrier_pos, brc: float):
    """(point, altitude_ft, ias_kt, heading_deg) for an airborne start.

    The heading is the inbound course in every case — even in the stack, where
    the ride begins on the inbound leg with the fix ahead. Starting a student
    mid-turn in cloud at night would be teaching something, but not this.
    """
    legs = legs_for(ride_key, carrier_pos, brc)
    if not legs:
        return None
    name, p, alt, kt = legs[0]
    return p, alt, kt, cq.final_bearing(brc)


def apply(group, ride_key: str, carrier_pos, brc: float) -> list:
    """Write the ride's flight plan onto the player's flight.

    Returns the rows the kneeboard prints: [(name, dme, alt_ft, kias)]. Never
    raises — a mission with no flight plan is a worse mission, not a failed
    build.
    """
    legs = legs_for(ride_key, carrier_pos, brc)
    if not legs or group is None:
        return []
    rows = []
    for name, p, alt_ft, ias in legs:
        # KM/H. `add_waypoint(speed=)` divides by 3.6 — see wk_route for the
        # release this cost.
        tas_kmh = ias_to_tas_kt(ias, alt_ft) * cq.KT_KMH
        try:
            group.add_waypoint(p, altitude=alt_ft * cq.FT_M, speed=tas_kmh,
                               name=name)
        except Exception:
            return rows
        rows.append((name, round(_dme_of(p, carrier_pos), 1), int(alt_ft),
                     int(ias)))
    return rows


def _dme_of(p, carrier_pos) -> float:
    try:
        return p.distance_to_point(carrier_pos) / NM
    except Exception:
        return 0.0


def brief_lines(ride_key: str, rows: list, brc: float, angels: int) -> list:
    """The flight-plan block for the kneeboard and the brief."""
    if not rows:
        return []
    fb = cq.final_bearing(brc)
    L = [
        "== CASE III RECOVERY ==",
        f"BRC {int(brc):03d}    FINAL BEARING {int(fb):03d}    "
        f"MARSHAL RADIAL {int(cq.marshal_radial(brc)):03d}",
        f"STACK  angels {angels} at {cq.marshal_dme(angels)} DME  "
        f"(angels + {cq.MARSHAL_DME_PLUS})",
        "",
        f"{'FIX':<16}{'DME':>7}{'ALT':>9}{'KIAS':>7}",
    ]
    for name, dme, alt, ias in rows:
        L.append(f"{name:<16}{dme:>7.1f}{alt:>8,}'{ias:>7}")
    L += [
        "",
        "FINAL BEARING is the extension of the ANGLED DECK — about "
        f"{cq.ANGLED_DECK_DEG:.0f} degrees to port of BRC. The marshal radial "
        "hangs off IT, not off the BRC. Computing it off the BRC is the error "
        "that puts you off the arc before you have started.",
        "",
        "PLATFORM IS AN ALTITUDE, NOT A RANGE. 5,000 feet, wherever that "
        "falls. The DME beside it above is where it will happen for THIS "
        "stack, not a gate to look for.",
        "",
        "MARSHAL WILL ASSIGN YOU A RADIAL, A DME AND A TIME ON THE RADIO, and "
        "those are generated while the mission runs — a mission file cannot "
        "read them. Fly what Marshal assigns. The numbers above are the same "
        "rule applied to this ship's BRC, and they are what this ride grades "
        "you against.",
    ]
    return L
