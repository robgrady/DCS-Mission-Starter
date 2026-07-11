"""BB-9: carrier strike group — CVN + escort screen, steaming into wind on BRC,
TACAN/ICLS/Link-4 configured. Anchor points are curated per-map data (verify in-game)."""
import math
from dcs import mapping, ships
from dcs.task import ActivateBeaconCommand, ActivateICLSCommand, ActivateLink4Command
from dcs.unit import Skill

CARRIERS = {
    "coldwar": {"blue": ("ships.Forrestal", "CV-59 Forrestal")},
    "modern": {"blue": ("ships.Stennis", "CVN-74 Stennis")},
}
ESCORTS = {
    "coldwar": ["ships.PERRY", "ships.PERRY"],
    "modern": ["ships.USS_Arleigh_Burke_IIa", "ships.USS_Arleigh_Burke_IIa", "ships.PERRY"],
}
# screen positions relative to carrier: (radius_m, bearing_off_BRC)
SCREEN = [(2500, 135), (2500, 225), (4000, 180)]


def _offset(pos, meters, bearing_deg):
    b = math.radians(bearing_deg)
    return mapping.Point(pos.x + meters * math.cos(b),
                         pos.y + meters * math.sin(b), pos._terrain)


def add_carrier_group(m, country, era, side, map_cfg, weather, comms, warnings,
                      hull_key=None):
    from .resolver import resolve, load_json
    anchor_cfg = map_cfg.get("carrier")
    if not anchor_cfg:
        warnings.append(f"map has no carrier anchor - carrier group skipped")
        return None, None

    if hull_key:
        from .deck import _load_hull
        hull = _load_hull(hull_key)
        if era not in hull["eras"]:
            warnings.append(f"{hull['label']} is not a {era} hull - carrier skipped")
            return None, None
        ref, label = hull["ship"], hull["label"]
    else:
        carrier_cfg = CARRIERS.get(era, {}).get(side)
        if not carrier_cfg:
            warnings.append(f"no {era}/{side} carrier defined - carrier group skipped")
            return None, None
        ref, label = carrier_cfg
    ctype = resolve(ref)
    anchor = mapping.Point(anchor_cfg["anchor"]["x"], anchor_cfg["anchor"]["y"], m.terrain)

    # BRC: into wind when we set wind (storm), else the curated open-sea heading
    wind_dir = getattr(getattr(m.weather, "wind_at_ground", None), "direction", 0)
    wind_spd = getattr(getattr(m.weather, "wind_at_ground", None), "speed", 0)
    brc = (wind_dir + 180) % 360 if wind_spd > 2 else anchor_cfg["heading"]

    grp = m.ship_group(country, "CSG Mother", ctype, anchor, heading=brc)
    grp.units[0].skill = Skill.Excellent
    for (radius, brg_off), eref in zip(SCREEN, ESCORTS[era]):
        u = m.ship(f"CSG escort {len(grp.units)}", resolve(eref))
        u.position = _offset(anchor, radius, (brc + brg_off) % 360)
        u.heading = brc
        grp.add_unit(u)

    # steam 40km down BRC at ~25kts so the deck has wind over it
    grp.add_waypoint(_offset(anchor, 40000, brc), speed=46)

    # beacons on the boat
    wp = grp.points[0]
    freq = comms.next_uhf()
    wp.tasks.append(ActivateBeaconCommand(channel=71, modechannel="X", callsign="STN",
                                          unit_id=grp.units[0].id, aa=False))
    wp.tasks.append(ActivateICLSCommand(channel=11, unit_id=grp.units[0].id))
    wp.tasks.append(ActivateLink4Command(unit_id=grp.units[0].id))
    comms.add("Carrier", "Mother", f"{freq:.2f}", "71X",
              f"{label} - ICLS 11, Link4, BRC {int(brc):03d}")
    return grp, brc
