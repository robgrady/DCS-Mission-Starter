"""BB-13: ambient air traffic — AI transports flying between friendly fields so the
world feels alive. Warm starts mean visible startup/taxi/departure activity.
Must run BEFORE dressing so these aircraft claim their parking slots first."""
import random
from dcs import mapping
from dcs.mission import StartType

from .resolver import resolve

DENSITY_FLIGHTS = {"sparse": 1, "normal": 2, "busy": 3}


def add_ambient_traffic(m, country, fields, era_side_cfg, density,
                        rng: random.Random, tag):
    created = []
    if len(fields) < 2:
        return created
    n = DENSITY_FLIGHTS[density]
    types = era_side_cfg["parked_large"] + era_side_cfg["parked_planes"][:1]
    for i in range(n):
        origin, dest = rng.sample(fields, 2)
        ref = rng.choice(types)
        try:
            actype = resolve(ref)
            fg = m.flight_group_from_airport(
                country, f"Ambient {tag} {i+1}", actype, origin,
                start_type=StartType.Warm, group_size=1)
            fg.add_runway_waypoint(origin)
            mid = mapping.Point((origin.position.x + dest.position.x) / 2,
                                (origin.position.y + dest.position.y) / 2, m.terrain)
            fg.add_waypoint(mid, altitude=3000)
            fg.land_at(dest)
            created.append(fg.name)
        except Exception:
            continue  # field full or type unusable: ambience is best-effort
    return created
