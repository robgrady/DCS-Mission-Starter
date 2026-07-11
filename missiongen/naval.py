"""BB-9: carrier strike group with real-world composition, names, and stations.

CSG data lives in carrier_decks.json per hull: real group name (e.g. "CSG-9
Theodore Roosevelt"), real escort ships from actual deployments (cruiser as AAW
shotgun on the beam, plane-guard destroyer astern, picket DDGs on the bow
quarters), and the embarked air wing for CAP/AEW launches.
"""
import math
from dcs import mapping, planes
from dcs.mission import StartType
from dcs.task import ActivateBeaconCommand, ActivateICLSCommand, ActivateLink4Command, CAP
from dcs.unit import Skill

CARRIERS = {  # legacy fallback when no hull specified
    "coldwar": {"blue": ("forrestal", None)},
    "modern": {"blue": ("stennis", None)},
}
CAP_ALT = 7620    # 25,000 ft
AEW_ALT = 8534    # 28,000 ft


def _offset(pos, meters, bearing_deg):
    b = math.radians(bearing_deg)
    return mapping.Point(pos.x + meters * math.cos(b),
                         pos.y + meters * math.sin(b), pos._terrain)


def add_carrier_group(m, country, era, side, map_cfg, weather, comms, warnings,
                      hull_key=None):
    from .resolver import resolve
    from .deck import _load_hull
    anchor_cfg = map_cfg.get("carrier")
    if not anchor_cfg:
        warnings.append("map has no carrier anchor - carrier group skipped")
        return None, None

    hull_key = hull_key or CARRIERS.get(era, {}).get(side, (None,))[0]
    if not hull_key:
        warnings.append(f"no {era}/{side} carrier defined - carrier group skipped")
        return None, None
    hull = _load_hull(hull_key)
    if era not in hull["eras"]:
        warnings.append(f"{hull['label']} is not a {era} hull - carrier skipped")
        return None, None

    csg = hull.get("csg", {})
    ctype = resolve(hull["ship"])
    anchor = mapping.Point(anchor_cfg["anchor"]["x"], anchor_cfg["anchor"]["y"], m.terrain)

    # BRC: into wind when weather sets one, else curated open-sea heading
    wind_dir = getattr(getattr(m.weather, "wind_at_ground", None), "direction", 0)
    wind_spd = getattr(getattr(m.weather, "wind_at_ground", None), "speed", 0)
    brc = (wind_dir + 180) % 360 if wind_spd > 2 else anchor_cfg["heading"]

    group_name = csg.get("group_name", f"CSG {hull['label']}")
    grp = m.ship_group(country, group_name, ctype, anchor, heading=brc)
    grp.units[0].skill = Skill.Excellent
    grp.units[0].name = csg.get("flagship_name", hull["label"])

    # real screen stations, oriented on BRC
    for esc in csg.get("escorts", []):
        u = m.ship(esc["name"], resolve(esc["ref"]))
        u.position = _offset(anchor, esc["r"], (brc + esc["brg"]) % 360)
        u.heading = brc
        u.skill = Skill.High
        grp.add_unit(u)

    # steam 40km down BRC at ~25kts
    grp.add_waypoint(_offset(anchor, 40000, brc), speed=46)

    # beacons on the boat
    wp = grp.points[0]
    freq = comms.next_uhf()
    wp.tasks.append(ActivateBeaconCommand(channel=71, modechannel="X", callsign="STN",
                                          unit_id=grp.units[0].id, aa=False))
    wp.tasks.append(ActivateICLSCommand(channel=11, unit_id=grp.units[0].id))
    wp.tasks.append(ActivateLink4Command(unit_id=grp.units[0].id))
    comms.add("Carrier", "Mother", f"{freq:.2f}", "71X",
              f"{csg.get('flagship_name', hull['label'])} - ICLS 11, BRC {int(brc):03d}")
    return grp, brc


def add_carrier_cap(m, country, hull_key, carrier_pos, brc, threat_bearing,
                    comms, warnings):
    """2-ship CAP from the embarked air wing, on station toward the threat axis."""
    from .resolver import resolve
    from .deck import _load_hull
    airwing = _load_hull(hull_key).get("csg", {}).get("airwing")
    if not airwing:
        warnings.append("no air wing data for this hull - CAP skipped")
        return None
    cap_cfg = airwing["cap"]
    cap_type = resolve(cap_cfg["type"])
    st1 = _offset(carrier_pos, 55000, threat_bearing)          # 30nm toward threat
    st2 = _offset(st1, 37000, (threat_bearing + 90) % 360)     # 20nm racetrack leg
    fg = m.patrol_flight(
        country, f"CAP {cap_cfg['squadron']}", cap_type, airport=None,
        pos1=st1, pos2=st2, speed=750, altitude=CAP_ALT, group_size=2)
    freq = comms.next_uhf()
    comms.add("CAP", cap_cfg["squadron"].split()[0], f"{freq:.2f}", "-",
              f"{airwing['label']} {cap_type.id} x2, stn 30nm on threat axis")
    return fg


def add_carrier_aew(m, country, hull_key, carrier_pos, brc, threat_bearing,
                    comms, warnings):
    """Air-wing E-2 Hawkeye AEW orbit behind the CSG (AAW picture for the group)."""
    from .resolver import resolve
    from .deck import _load_hull
    airwing = _load_hull(hull_key).get("csg", {}).get("airwing")
    if not airwing:
        warnings.append("no air wing data for this hull - AEW skipped")
        return None
    aew_cfg = airwing["aew"]
    aew_type = resolve(aew_cfg["type"])
    pos = _offset(carrier_pos, 45000, (threat_bearing + 180) % 360)  # 25nm behind CSG
    freq = comms.next_uhf()
    fg = m.awacs_flight(
        country, f"AEW {aew_cfg['squadron']}", aew_type, airport=None,
        position=pos, race_distance=48000, heading=(threat_bearing + 90) % 360,
        altitude=AEW_ALT, speed=500, frequency=freq)
    comms.add("AEW", aew_cfg["squadron"].split()[0], f"{freq:.2f}", "-",
              f"{airwing['label']} {aew_type.id} overhead the force")
    return fg
