"""BB-23: aircraft in the pattern — AI traffic shooting approaches into, or
departing from, YOUR home field at mission start, so the base you walk out onto
is visibly operational instead of dead.

Player-visible knobs: which side of the pattern (landing / takeoff / both), what
kind of traffic (fighters / cargo / helicopters / mixed) and how many aircraft.

Only AI flights are placed here — the player's own route is never touched, which
keeps this inside the "never place player waypoints" rule.

Runs BEFORE dressing so departing aircraft claim their parking stands first.
"""
import random

from dcs.mission import StartType

from .resolver import resolve

MODES = ("landing", "takeoff", "both")
KINDS = ("fighter", "cargo", "helicopter", "mixed")

KIND_LABELS = {
    "fighter": "fighters",
    "cargo": "cargo/transport",
    "helicopter": "helicopters",
    "mixed": "mixed types",
}

# --- pattern geometry (metres) ---------------------------------------------
FIRST_FINAL = 11000     # lead aircraft ~6 nm out on the extended centreline
TRAIL_SPACING = 7000    # ~3.8 nm in trail behind it
SHORT_FINAL = 6000      # gate waypoint on the straight-in
# Altitude follows a ~3 degree profile off the runway rather than a flat number,
# so trailing aircraft stack up correctly and nobody dives at the threshold.
GLIDE = 0.05
MIN_APPROACH_AGL = 150
MAX_APPROACH_AGL = 1500
HELO_GLIDE = 0.02       # helicopters run the pattern low and flat
MIN_HELO_AGL = 60
MAX_HELO_AGL = 400
DOWNWIND_AGL = 450      # closed-circuit leg after departure

APPROACH_SPEED = 400    # km/h — fixed wing on a straight-in
HELO_SPEED = 180
DEPART_MIN = 6000       # departure waypoint distance off the runway
DEPART_MAX = 9000

MAX_COUNT = 4


def _field_elevation(airport) -> float:
    """Field elevation in metres. pydcs Airports carry no elevation, but every
    parking slot does — any stand is within a few feet of field elevation."""
    try:
        return float(airport.parking_slots[0].height)
    except Exception:
        return 0.0


def _approach_agl(dist, helo=False) -> float:
    """Height above field at `dist` metres out on the straight-in.

    A flat spawn altitude makes trailing aircraft sit at the same height and
    forces a dive at the threshold. A ~3 degree profile (5% here, so the AI has
    a little margin to descend into) stacks the stream correctly and puts every
    aircraft on a plausible glidepath. Floored so nobody starts in the weeds and
    capped so the lead does not spawn at airliner altitude.
    """
    if helo:
        return min(MAX_HELO_AGL, max(MIN_HELO_AGL, dist * HELO_GLIDE))
    return min(MAX_APPROACH_AGL, max(MIN_APPROACH_AGL, dist * GLIDE))


def types_for(era_side_cfg, kind):
    """Era-correct type refs for a traffic category. Everything comes out of the
    era pack, so a 1944 pattern is Spitfires and C-47s, never Vipers."""
    large = list(era_side_cfg.get("parked_large") or [])
    helos = list(era_side_cfg.get("parked_helos") or [])
    # "fighter" means the tactical jets/props, i.e. the parked-plane list with
    # the transports (which also appear in parked_large) taken back out
    fighters = [t for t in (era_side_cfg.get("parked_planes") or []) if t not in large]
    if kind == "cargo":
        return large
    if kind == "helicopter":
        return helos
    if kind == "fighter":
        return fighters or list(era_side_cfg.get("parked_planes") or [])
    return fighters + large + helos          # mixed


def _plan(mode, count, rng):
    """Which leg each aircraft flies. 'both' alternates, landing first, so the
    player always sees at least one aircraft on the approach."""
    if mode == "landing":
        return ["landing"] * count
    if mode == "takeoff":
        return ["takeoff"] * count
    return ["landing" if i % 2 == 0 else "takeoff" for i in range(count)]


def _add_landing(m, country, airport, actype, name, slot, elev, rng):
    """Spawn airborne on the extended centreline and let DCS fly the approach."""
    runway = airport.runways[0]
    heading = runway.heading
    dist = FIRST_FINAL + slot * TRAIL_SPACING
    pos = airport.position.point_from_heading((heading + 180) % 360, dist)
    helo = actype.helicopter
    speed = HELO_SPEED if helo else APPROACH_SPEED
    fg = m.flight_group_inflight(
        country, name, actype, pos, int(elev + _approach_agl(dist, helo)),
        speed=speed, group_size=1)
    gate = airport.position.point_from_heading((heading + 180) % 360, SHORT_FINAL)
    fg.add_waypoint(gate, int(elev + _approach_agl(SHORT_FINAL, helo)), speed=speed)
    fg.land_at(airport)
    return fg


def _add_takeoff(m, country, airport, actype, name, slot, elev, rng):
    """Engines running on the ramp: they taxi, roll and fly a closed circuit back
    to the same field, so the pattern stays populated the whole time."""
    runway = airport.runways[0]
    heading = runway.heading
    fg = m.flight_group_from_airport(
        country, name, actype, airport,
        start_type=StartType.Warm, group_size=1)
    helo = actype.helicopter
    speed = HELO_SPEED if helo else APPROACH_SPEED
    # pass distance from the SEEDED rng — pydcs's default arg is a random value
    # frozen at import time, which breaks cross-process reproducibility.
    # See missiongen/_determinism.py.
    fg.add_runway_waypoint(
        airport, runway,
        distance=rng.randrange(DEPART_MIN, DEPART_MAX, 100) + slot * 500)
    # crosswind/downwind abeam, then back around to land
    downwind = airport.position.point_from_heading(
        (heading + 235) % 360, 12000 + slot * 1500)
    fg.add_waypoint(downwind, int(elev + DOWNWIND_AGL +
                                  (0 if helo else 300)), speed=speed)
    fg.land_at(airport)
    return fg


def add_pattern_traffic(m, country, airport, era_side_cfg, mode, kind, count,
                        rng: random.Random, warnings=None):
    """Place `count` AI aircraft in the pattern at `airport`.

    Returns the list of group names created. Best-effort throughout: a full ramp
    or an unusable type costs one aircraft, never the mission.
    """
    if airport is None:
        return []
    refs = types_for(era_side_cfg, kind)
    if not refs:
        if warnings is not None:
            warnings.append(
                f"no era-correct {KIND_LABELS.get(kind, kind)} for this side — "
                f"pattern traffic skipped")
        return []
    count = max(1, min(MAX_COUNT, int(count)))
    elev = _field_elevation(airport)
    created = []
    land_slot = depart_slot = 0
    for i, leg in enumerate(_plan(mode, count, rng)):
        name = f"Pattern {i + 1}"
        # try the whole category before giving up on this aircraft: a departing
        # C-47 needs a large stand that a WWII strip may not have, but a fighter
        # from the same list will fit.
        order = [rng.choice(refs)]
        order += [t for t in refs if t != order[0]]
        for ref in order:
            try:
                actype = resolve(ref)
                if leg == "landing":
                    fg = _add_landing(m, country, airport, actype, name,
                                      land_slot, elev, rng)
                    land_slot += 1
                else:
                    fg = _add_takeoff(m, country, airport, actype, name,
                                      depart_slot, elev, rng)
                    depart_slot += 1
                created.append(fg.name)
                break
            except Exception:
                continue    # ramp full or type unusable: try the next type
    if warnings is not None:
        if not created:
            warnings.append(
                f"pattern traffic could not be placed at {airport.name}")
        elif len(created) < count:
            warnings.append(
                f"{count - len(created)} of {count} pattern aircraft did not "
                f"fit at {airport.name} - placed {len(created)}")
    return created
