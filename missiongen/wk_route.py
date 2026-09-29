"""Flight plans for the White Knights rides.

WHY THIS EXISTS
---------------
Every one of the twenty rides shipped with exactly ONE waypoint — the parking
spot. The B'NAI card describes an IP, a 2-3 nm in-trail set-up, a pop and an
egress on the opposite side; the mission contained a place to start the
engines. That is the say/do gap in its most literal form: the brief described a
route the file did not have.

WHY NOT `routing.route_for()`
-----------------------------
That builds a generic strike route — home, IP, target, home — sized for a
combat sortie. These are training sorties whose geometry IS the lesson: the
low-level rides need turn points that exercise a comm-out 90, the delivery
rides need an IP at the sheet's own pull-up distance, and the attack rides need
a split point at the distance the squadron's guide names. A generic router
cannot produce those numbers because it has never read the document.

ALTITUDES ARE PLANNING FIGURES, AND THE CARD SAYS SO
----------------------------------------------------
DCS waypoints carry MSL. The squadron's floor is AGL. Those are not the same
number and pydcs exposes no terrain elevation to convert between them, so the
route is laid at `floor + a per-theatre ground reference` and the kneeboard
prints the AGL figure as the one you fly. A real low-level card works exactly
this way: the route altitude is planning, the terrain is what you actually fly.
"""
from __future__ import annotations

import math

from . import wk

# Typical ground elevation along a low-level route, per theatre. OURS — an
# estimate, not a measurement, and labelled as one. It converts the squadron's
# AGL floor into the MSL a waypoint carries. It is deliberately NOT
# `aar.TERRAIN_MAX_FT`: that is the highest ground on the whole map, which
# would push a 500 ft low level to 19,000 ft on Caucasus.
ROUTE_GROUND_FT = {
    "germany": 1000,     # Rhineland / Hessen uplands, Fulda corridor
    "sinai": 500,        # Nile valley and the Western Desert floor
    "caucasus": 300,     # Colchis lowland
    "nevada": 3000,      # the Nevada basins
}
ROUTE_GROUND_DEFAULT_FT = 1000

# The route axis. Fixed per theatre rather than random, because a training
# route you fly ten times should be the same route ten times — a learner cannot
# build a picture against terrain that moves.
# SINAI RUNS WEST. 120 was chosen when the rides silently launched from
# Hatzor; from CAIRO WEST a 120-degree axis runs the low level straight across
# Cairo city — Cairo International sits 28 NM out on bearing 091 — and parks
# the target leg in the Nile valley suburbs. Rob flew it: "the mission
# waypoints don't seem aligned." 265 puts the whole route in the open Western
# Desert, pointed at the threat the 1980 lineup names (Libya), and from Beni
# Suef it keeps the checkout rides west of the Nile instead of crossing it.
AXIS_DEG = {"germany": 75.0, "sinai": 265.0, "caucasus": 250.0, "nevada": 340.0}
AXIS_DEFAULT_DEG = 90.0

NM = 1852.0


def ground_ft(map_key: str) -> int:
    return int(ROUTE_GROUND_FT.get(map_key, ROUTE_GROUND_DEFAULT_FT))


def axis_deg(map_key: str) -> float:
    return float(AXIS_DEG.get(map_key, AXIS_DEFAULT_DEG))


def msl_ft(agl_ft: float, map_key: str) -> int:
    """AGL -> the MSL a waypoint carries, via the theatre ground reference."""
    return int(round(agl_ft + ground_ft(map_key)))


# --------------------------------------------------------------------------- #
# The leg tables. (name, along_nm, across_nm, alt_ft_AGL, ias_kt)
#
# `along` runs down the route axis from the home field; `across` is positive to
# the right of it. Both in nautical miles. Altitudes are AGL and converted at
# build time; speeds are indicated, exactly as the squadron's documents state
# them, and converted to true for the file.
# --------------------------------------------------------------------------- #
def _low_level(map_key: str, ias: int | None = None) -> list:
    """The common low-level route: out, two turns, and back.

    The turn points are 90 degrees to each other on purpose — that is the
    comm-out turn the WSO calls, and a route of gentle 20-degree doglegs would
    never make the pilot fly one.
    """
    f = wk.floor_ft(map_key)
    v = ias or wk.MIN_IAS_KT
    return [
        ("DEPARTURE", 6, 0, 2000, 350),
        ("ROUTE ENTRY", 18, 0, f, v),
        ("TP A — 90 LEFT", 34, 0, f, v),
        ("TP B — 90 RIGHT", 34, -16, f, v),
        ("TP C", 52, -16, f, v),
        ("ROUTE EXIT", 60, -4, f, v),
        ("RECOVERY", 14, 4, 3000, 300),
    ]


def _range_pattern(map_key: str, delivery: str) -> list:
    """IP, pull-up, target, off-target — at the delivery sheet's own numbers.

    The IP sits at the sheet's PULL UP POINT converted from feet to a distance
    on the ground, because that is what the number means: the slant distance at
    which you start the pop.
    """
    d = wk.DELIVERIES[delivery]
    f = wk.floor_ft(map_key)
    pup_nm = d["pup_ft"] / 6076.12
    return [
        ("DEPARTURE", 6, 0, 2000, 350),
        ("IP", 24, 0, f, wk.MIN_IAS_KT),
        ("PULL UP POINT", 24 + round(8 - pup_nm, 1), 0, f, wk.MIN_IAS_KT),
        ("TARGET", 32, 0, d["apex_ft"], d["release_kt"]),
        ("OFF TARGET", 38, -6, f, wk.MIN_IAS_KT),
        ("RECOVERY", 14, 4, 3000, 300),
    ]


def _attack(map_key: str, attack: str) -> list:
    """IP, the split point at the distance the guide names, target, egress."""
    a = wk.ATTACKS[attack]
    f = wk.floor_ft(map_key)
    split_nm = a.get("support_nm") or 4.0
    if attack == "bnai":
        split_nm = a["trail_nm"][1]
    return [
        ("DEPARTURE", 6, 0, 2000, 350),
        ("IP", 26, 0, f, wk.MIN_IAS_KT),
        ("SPLIT POINT", 36 - split_nm, 0, f, wk.MIN_IAS_KT),
        ("TARGET", 36, 0, 4000, 500),
        ("EGRESS", 44, -8, f, wk.MIN_IAS_KT),
        ("RECOVERY", 14, 4, 3000, 300),
    ]


def _bnai_coached(map_key: str) -> list:
    """The B'NAI, flown the way the guide actually describes the set-up.

    THE DIFFERENCE FROM `_attack("bnai")`, AND WHY IT IS NOT A TIDY-UP.
    The guide's own paragraph says: "To set in-trail spacing, approach the IP
    at nearly 90° angle off with lead on the side of the formation nearest the
    target." `_attack` runs in dead straight and leaves that to the pilot's
    imagination, which is defensible on a check ride — you are being tested on
    whether you know it.

    On a COACHED ride it is not defensible. A cue that says "IP, turn inbound"
    while the flight plan runs straight through the IP is a cue contradicting
    the route it fires on. So the coached leg table comes in from the side:
    TRAIL SET sits 8 nm off the run-in axis and 1 nm short of the IP, which is
    an approach 83 degrees off the run-in heading. "Nearly 90" is the guide's
    own wording and 83 is what the geometry gives at a spacing that leaves the
    pilot room to roll out; claiming a clean 90 would be inventing precision
    the drawing does not have.

    PULL-UP is a real waypoint here rather than a distance in a card, so the
    F10 map shows the point the cue fires at. It is the delivery sheet's
    11,400 ft — see `wk_coach._pup_ft` for why the diagram's 4.5 NM is not it.
    """
    f = wk.floor_ft(map_key)
    pup_nm = wk.DELIVERIES["lald15"]["pup_ft"] / 6076.12
    return [
        ("DEPARTURE", 6, 0, 2000, 350),
        ("LOW LEVEL", 18, 9, f, wk.MIN_IAS_KT),
        ("TRAIL SET", 25, 8, f, wk.MIN_IAS_KT),
        ("IP", 26, 0, f, wk.MIN_IAS_KT),
        ("PULL-UP", round(36 - pup_nm, 2), 0, f, 500),
        ("TARGET", 36, 0, 4000, 500),
        ("EGRESS", 44, -8, f, wk.MIN_IAS_KT),
        ("RECOVERY", 14, 4, 3000, 300),
    ]


def _working_area(map_key: str, three_ship: bool = False) -> list:
    """Intercepts and BFM. A block of air, a set-up point, and the outbound leg
    the Standards section actually specifies: two minutes at 350 KIAS."""
    i = wk.INTERCEPT
    out_nm = i["setup_kt"] * (i["outbound_min"] / 60.0)   # 2 min at 350 KIAS
    base = 18000
    return [
        ("AREA ENTRY", 30, 0, base, i["setup_kt"]),
        ("SET-UP POINT", 42, 0, base, i["setup_kt"]),
        ("OUTBOUND", 42 + round(out_nm, 1), 0, base, i["setup_kt"]),
        ("TURN-IN", 42 + round(out_nm, 1), 8 if three_ship else 6,
         base + (i["alt_split_ft"] if three_ship else 0), i["fighter_kt"]),
        ("MERGE", 42, 0, base, i["fighter_kt"]),
        ("RECOVERY", 16, 4, 6000, 300),
    ]


def _pattern(map_key: str) -> list:
    """The overhead. Out to initial, and back."""
    return [
        ("DEPARTURE", 5, 0, 1500, 300),
        ("DOWNWIND", 9, 3, 2000, 300),
        ("INITIAL", 4, 0, 1500, 300),
        ("RECOVERY", 1, 0, 800, 220),
    ]


def _tanker_drag(map_key: str) -> list:
    """Out to the tanker track and back. The rendezvous itself is the tanker's
    orbit, which `support_air` places — this is the flow to it."""
    return [
        ("DEPARTURE", 8, 0, 5000, 350),
        ("RV POINT", 40, 0, 20000, 300),
        ("POST-AAR", 55, -10, 20000, 300),
        ("RECOVERY", 16, 4, 6000, 300),
    ]


def legs_for(ride_key: str, map_key: str) -> list:
    """The leg table for a ride, or [] where a flight plan would be a fiction.

    Rides 1 and 3 are a departure and a stopwatch on the ramp. Inventing a
    route for a combat quick turn would put waypoints on the F10 map for a
    sortie that never leaves the chocks.
    """
    r = wk.RIDES.get(ride_key) or {}
    if ride_key == "wk_3_cqt":
        return []
    if ride_key == "wk_1_stepstart":
        return [("DEPARTURE", 8, 0, 5000, 350), ("RECOVERY", 12, 4, 3000, 300)]
    if ride_key == "wk_2_overhead":
        return _pattern(map_key)
    if ride_key in ("wk_4_lineabreast", "wk_5_commout", "wk_6_ridge",
                    "wk_7_threats", "wk_8_abort"):
        return _low_level(map_key)
    if ride_key == "wk_9_intercepts":
        return _working_area(map_key)
    if ride_key == "wk_10_threeship":
        return _working_area(map_key, three_ship=True)
    if ride_key == "wk_11_bfm":
        return _working_area(map_key)
    if ride_key == "pp_1_drag":
        return _tanker_drag(map_key)
    if r.get("coach"):
        return _bnai_coached(map_key)
    if r.get("attack"):
        return _attack(map_key, r["attack"])
    if r.get("delivery"):
        return _range_pattern(map_key, r["delivery"])
    return []


# --------------------------------------------------------------------------- #
# Applying it
# --------------------------------------------------------------------------- #
def _offset(p, dist_m, bearing_deg):
    from .dressing import _offset as _o
    return _o(p, dist_m, bearing_deg)


def ias_to_tas_kt(ias_kt: float, alt_ft: float) -> float:
    """Same conversion the AAR module uses, for the same reason: a pilot flies
    indicated and the mission file stores true. Reusing `aar.ias_to_tas_kt`
    keeps one implementation."""
    from .aar import ias_to_tas_kt as _f
    return _f(ias_kt, alt_ft)


def leg_positions(home_pos, ride_key: str, map_key: str) -> dict:
    """{leg name: map point} for a ride, by the SAME arithmetic `apply` uses.

    This exists so the coaching cues can be placed on the flight plan rather
    than near it. Recomputing "where is the pull-up point" in `wk_coach` with
    its own copy of the offset maths is the twin-function shape that has cost
    this codebase two live defects; one function, called twice, cannot drift.
    """
    if home_pos is None:
        return {}
    ax = axis_deg(map_key)
    out = {}
    for name, along, across, _agl, _ias in legs_for(ride_key, map_key):
        p = _offset(home_pos, along * NM, ax)
        if across:
            p = _offset(p, abs(across) * NM,
                        (ax + (90 if across > 0 else -90)) % 360.0)
        out[name] = p
    return out


def apply(group, home_pos, ride_key: str, map_key: str,
          home_airport=None) -> list:
    """Write the ride's flight plan onto the player's flight.

    Returns the rows the kneeboard prints: [(name, alt_agl_ft, ias_kt)]. Empty
    when the ride has no route, which is a legitimate answer and not a failure.
    """
    legs = legs_for(ride_key, map_key)
    if not legs or group is None or home_pos is None:
        return []
    ax = axis_deg(map_key)
    rows = []
    for name, along, across, agl, ias in legs:
        p = _offset(home_pos, along * NM, ax)
        if across:
            p = _offset(p, abs(across) * NM, (ax + (90 if across > 0 else -90)) % 360.0)
        alt_ft = msl_ft(agl, map_key)
        # KM/H, NOT M/S. `FlyingGroup.add_waypoint(speed=...)` divides by
        # 3.6 before storing — its argument is km/h. This line spent four
        # releases passing metres per second, which DCS read as a route flown
        # at 112 knots instead of 400: a number slow enough that the AI
        # counterpart never accelerated to rotation speed and trundled down
        # the runway instead of flying. Rob watched him do it.
        tas_kmh = ias_to_tas_kt(ias, alt_ft) * 1.852
        try:
            group.add_waypoint(p, altitude=alt_ft * 0.3048, speed=tas_kmh,
                               name=name)
        except Exception:
            return rows
        rows.append((name, int(agl), int(ias)))
    if home_airport is not None:
        try:
            group.land_at(home_airport)
        except Exception:
            pass
    return rows


def brief_lines(ride_key: str, map_key: str, rows: list) -> list:
    """The flight-plan block for the card.

    It prints AGL because that is what the pilot flies, and says in one line
    that the waypoints themselves carry MSL — otherwise a pilot who checks the
    F10 map against this card finds two different numbers and trusts neither.
    """
    if not rows:
        if ride_key == "wk_3_cqt":
            return ["== FLIGHT PLAN ==",
                    "None. This ride is a ramp, a taxiway and a stopwatch — "
                    "putting waypoints on the F10 map for a sortie that never "
                    "leaves the chocks would be decoration."]
        return []
    g = ground_ft(map_key)
    L = ["== FLIGHT PLAN ==",
         f"{'WAYPOINT':<22}{'AGL':>8}{'KIAS':>8}"]
    for name, agl, ias in rows:
        L.append(f"{name:<22}{agl:>7,}'{ias:>8}")
    L += ["",
          f"ALTITUDES ABOVE ARE AGL — the number you fly. The waypoints in the "
          f"aircraft carry MSL, laid at AGL plus a {g:,} ft ground reference "
          f"for this theatre. That reference is OUR estimate, not a survey: "
          f"pydcs exposes no terrain elevation, so a route altitude is a "
          f"planning figure and the terrain is what you actually fly.",
          "",
          "SPEEDS ARE INDICATED. The file stores true, converted at the "
          "waypoint altitude — the same conversion the tanker tracks use, and "
          "the reason a tanker once flew 217 knots."]
    return L


# --------------------------------------------------------------------------- #
# The counterpart — the airplane every card promised and no mission contained
# --------------------------------------------------------------------------- #
# THE DEFECT THIS FIXES. Every ride's card carries the WINGMAN NOTE: "he is a
# SEPARATE FLIGHT flying a scripted route, not a wingman inside your flight".
# Twenty-one missions shipped with one airplane in them. The card described an
# aircraft that was not there, which is the say/do gap in the purest form the
# product has produced — and it was written into the card by us, deliberately,
# before the thing it described existed.
#
# HIS OFFSET IS THE SQUADRON'S OWN SPACING. Line abreast is 5-7 nm; the B'NAI
# is 2-3 nm in trail; the splits and the double 90 put him the other side of
# the target. Those are not chosen numbers, they are the documents'.
def counterpart_legs(ride_key: str, map_key: str) -> list:
    """His leg table: the player's, displaced by the briefed geometry.

    Returns [] where the ride has no counterpart — the quick turn is a ramp,
    and ride 1 is a departure you fly alone.
    """
    r = wk.RIDES.get(ride_key) or {}
    if ride_key in ("wk_1_stepstart", "wk_3_cqt"):
        return []
    legs = legs_for(ride_key, map_key)
    if not legs:
        return []

    # Lateral displacement, in nm, positive to the right of the route axis.
    lo, hi = wk.LINE_ABREAST_NM
    side = -(lo + hi) / 2.0              # 6 nm, left: you are on his right
    trail_nm = 0.0
    if r.get("attack") == "bnai":
        # In trail, not abreast: 2-3 nm behind on the SAME ground track, which
        # is the attack's defining feature and its stated disadvantage.
        side = 0.0
        trail_nm = -sum(wk.ATTACKS["bnai"]["trail_nm"]) / 2.0
    elif r.get("attack") in ("split_lowhigh", "split_lowlow"):
        # Opposite side of the target. The axes converge 120-180 degrees.
        side = 7.0
    elif r.get("attack") in ("echelon", "double90"):
        # Same hemisphere, offset enough to be a formation and not a collision.
        side = 3.0
    elif ride_key in ("wk_9_intercepts", "wk_10_threeship", "wk_11_bfm"):
        # He is the other half of the set-up, and he goes the other way.
        side = 10.0

    out = []
    for name, along, across, agl, ias in legs:
        out.append((name, along + trail_nm, across + side, agl, ias))
    return out


# `apply_counterpart` lived here until v1.85.0 — it built the wingman as a
# SEPARATE flight on a scripted route, and across three redesigns (schedule,
# hold, release) it never once flew with the pilot, because DCS gives an
# independent flight no way to hold position on a human. The wingman is seat
# two of the player's own group now (the builder sizes the group from
# `wk.has_counterpart`), and `counterpart_legs` above survives as the
# two-ship predicate and the source of the trail/abreast numbers the cards
# print. Dead code that pretends to build an airplane is exactly the drift
# this codebase exists to prevent, so the function is gone rather than idle.
