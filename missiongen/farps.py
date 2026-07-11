"""BB-4: functional FARPs — pad plus the support units DCS requires for
rearm/refuel to actually work (fuel, ammo, command, comms within 150m)."""
import math
import random
from dcs import mapping
from dcs.unit import FARP

from .resolver import resolve

# the four units a FARP needs to function, per side
FARP_KIT = {
    "blue": ["vehicles.Unarmed.M978_HEMTT_Tanker",   # fuel
             "vehicles.Unarmed.M_818",               # ammo truck
             "vehicles.Unarmed.Hummer",              # command
             "vehicles.Unarmed.Predator_TrojanSpirit"],  # comms
    "red": ["vehicles.Unarmed.ATZ_10",
            "vehicles.Unarmed.GAZ_3308",
            "vehicles.Unarmed.GAZ_66",
            "vehicles.Unarmed.KAMAZ_Truck"],
}


def _offset(pos, meters, bearing_deg):
    b = math.radians(bearing_deg)
    return mapping.Point(pos.x + meters * math.cos(b),
                         pos.y + meters * math.sin(b), pos._terrain)


def add_farp(m, country, side, position, rng: random.Random, name, comms=None):
    """One functional FARP: pad + support ring. Returns the FARP static group."""
    freq = comms.next_farp() if comms else 127.5
    pad = FARP(m.terrain, m.next_unit_id(), f"{name} pad", frequency=freq)
    pad.position = position
    from dcs import unitgroup
    from dcs.point import StaticPoint
    sg = unitgroup.StaticGroup(m.next_group_id(), name)
    sg.add_unit(pad)
    sg.add_point(StaticPoint(pad.position))
    country.add_static_group(sg)

    # support units in a ring 60-90m out — inside the 150m service radius
    base = rng.uniform(0, 360)
    for i, ref in enumerate(FARP_KIT[side]):
        try:
            utype = resolve(ref)
        except Exception:
            continue
        pos = _offset(position, rng.uniform(60, 90), base + i * 90)
        m.vehicle_group(country, f"{name} spt {i+1}", utype, pos,
                        heading=rng.uniform(0, 360))
    if comms:
        comms.add("FARP", name, f"{freq:.2f}", "-", "rearm/refuel active")
    return sg
