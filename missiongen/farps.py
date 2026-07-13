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


def helipad_farps(m, country, side, own_center, enemy_center, rng, comms,
                  count=2):
    """Cold War Germany ships 100+ real 'H FRG/GDR' helipad sites as terrain
    airports. When the map has them, FARPs use the REAL surveyed pads nearest
    the frontline instead of synthetic pads in a field — Visual Fidelity:
    the FARP sits where the map author put a helipad clearing.
    Returns list of (airport, name) used, or [] if the map has none."""
    tag = "H FRG" if side == "blue" else "H GDR"
    med = "H Med FRG" if side == "blue" else "H Med GDR"
    pads = [a for a in m.terrain.airports.values()
            if a.name.startswith(tag) or a.name.startswith(med)]
    if not pads:
        return []
    # forward pads: closest to the enemy centroid but on our side of center
    def key(a):
        return a.position.distance_to_point(enemy_center)
    pads.sort(key=key)
    # skip the absolute closest (often ON the border); take the next ones
    picked, used = [], []
    for a in pads:
        d_own = a.position.distance_to_point(own_center)
        d_enemy = a.position.distance_to_point(enemy_center)
        if d_enemy > d_own * 0.4:      # forward but not across the line
            picked.append(a)
        if len(picked) >= count:
            break
    for i, ap in enumerate(picked):
        if side == "blue":
            ap.set_blue()
        else:
            ap.set_red()
        name = f"FARP {'London Dallas Berlin Paris'.split()[i]} ({ap.name})"
        freq = comms.next_farp() if comms else 127.5
        base = rng.uniform(0, 360)
        for j, ref in enumerate(FARP_KIT[side]):
            try:
                utype = resolve(ref)
            except Exception:
                continue
            pos = _offset(ap.position, rng.uniform(60, 90), base + j * 90)
            m.vehicle_group(country, f"{name} spt {j+1}", utype, pos,
                            heading=rng.uniform(0, 360))
        if comms:
            comms.add("FARP", name, f"{freq:.2f}", "-",
                      "real helipad site - rearm/refuel active")
        used.append((ap, name))
    return used
