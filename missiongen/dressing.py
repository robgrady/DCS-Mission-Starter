"""BB-1..3: airfield dressing — static aircraft on real parking spots, ground support
equipment near occupied stands, infrastructure statics near the ramp."""
import math
import random
from dcs import mapping
import dcs.statics as statics

from .resolver import resolve
from .placement import AirfieldKeepOut

DENSITY_FILL = {"sparse": 0.25, "normal": 0.45, "busy": 0.70}
MAX_STATICS_PER_FIELD = 24   # NFR: FPS guard


def _offset(pos, meters, bearing_deg):
    b = math.radians(bearing_deg)
    return mapping.Point(pos.x + meters * math.cos(b),
                         pos.y + meters * math.sin(b), pos._terrain)


def dress_airfield(m, airport, country, era_side_cfg, density, rng: random.Random,
                   used_slot_names=None):
    """Fill an airfield with era/faction-correct static aircraft + ground equipment.

    Placement discipline: aircraft go on surveyed parking stands only (always
    safe); everything free-placed (GSE, infrastructure) is validated against
    the runway keep-out corridors so movement areas stay clear.
    """
    used = used_slot_names or set()
    keepout = AirfieldKeepOut(airport)
    placed = 0

    free = [s for s in airport.parking_slots
            if s.unit_id is None and s.slot_name not in used]
    rng.shuffle(free)
    target = min(int(len(free) * DENSITY_FILL[density]), MAX_STATICS_PER_FIELD)

    plane_refs = era_side_cfg["parked_planes"]
    large_refs = era_side_cfg["parked_large"]
    helo_refs = era_side_cfg["parked_helos"]
    fuel_truck = resolve(era_side_cfg["fuel_truck"])
    utility = [resolve(r) for r in era_side_cfg["utility_trucks"]]

    for slot in free:
        if placed >= target:
            break
        # pick a type that fits the stand (helo lists can be empty, e.g. WWII)
        if slot.helicopter and not slot.airplanes:
            if not helo_refs:
                continue
            ref = rng.choice(helo_refs)
        elif slot.large:
            ref = rng.choice(large_refs + plane_refs)
        elif slot.airplanes:
            # only put big airframes on large stands
            ref = rng.choice([r for r in plane_refs if r not in large_refs] or plane_refs)
        else:
            if not helo_refs:
                continue
            ref = rng.choice(helo_refs)
        unit_type = resolve(ref)

        heading = rng.uniform(0, 360)
        name = f"ST {airport.name} {slot.slot_name} {unit_type.id}"
        m.static_group(country, name, _type=unit_type, position=slot.position,
                       heading=heading)
        placed += 1

        # BB-2: ground support equipment near ~half the occupied stands.
        # Stay WITHIN the stand's own footprint (stands are 40-80 m wide, so
        # 12-16 m off the aircraft is still apron, never the taxilane) and
        # never inside a runway corridor.
        if rng.random() < 0.5:
            gse_max = max(12.0, min(16.0, (min(slot.length, slot.width) / 2) - 8))
            gse_pos = _offset(slot.position, rng.uniform(12, gse_max),
                              heading + rng.uniform(60, 120))
            if keepout.clear(gse_pos, avoid_stands=False):
                gse_type = fuel_truck if rng.random() < 0.5 else rng.choice(utility)
                m.static_group(country, f"GSE {airport.name} {slot.slot_name}",
                               _type=gse_type, position=gse_pos,
                               heading=rng.uniform(0, 360))

    # BB-3: infrastructure cluster near the ramp. The ramp sits BESIDE the
    # runway, so a random bearing from its centroid used to land the cluster
    # mid-runway. Now: push the anchor perpendicular to the runway axis,
    # DEEPER into the ramp side (away from the runway), then validate — the
    # cluster row runs parallel to the runway so it can never cross it.
    if free:
        cx = sum(s.position.x for s in free) / len(free)
        cy = sum(s.position.y for s in free) / len(free)
        centroid = mapping.Point(cx, cy, airport.position._terrain)
        away = keepout.away_side_bearing(centroid)
        anchor = None
        for push in (300, 450, 600):
            cand = _offset(centroid, push, away + rng.uniform(-20, 20))
            if keepout.clear(cand, margin=60):
                anchor = cand
                break
        if anchor is None:
            anchor = keepout.find_clear(centroid, 300, 700, rng, margin=60,
                                        prefer_bearing=away)
        if anchor is not None:
            row = keepout.runway_axis_heading()   # row parallels the runway
            infra = [
                (statics.Fortification.Fuel_tank, 0),
                (statics.Fortification.Fuel_tank, 18),
                (statics.Fortification.Tent01, 60),
                (statics.Fortification.Tent03, 85),
                (statics.Fortification.Barracks_2, 130),
                (statics.Fortification.Comms_tower_M, 190),
            ]
            for i, (obj, dist) in enumerate(infra):
                pos = _offset(anchor, dist, row)
                if not keepout.clear(pos):
                    continue                      # belt and suspenders
                m.static_group(country, f"INF {airport.name} {i}", _type=obj,
                               position=pos, heading=(row + 90) % 360)

    return placed
