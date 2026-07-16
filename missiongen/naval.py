"""BB-9: carrier strike group with real-world composition, names, and stations.

CSG data lives in carrier_decks.json per hull: real group name (e.g. "CSG-9
Theodore Roosevelt"), real escort ships from actual deployments (cruiser as AAW
shotgun on the beam, plane-guard destroyer astern, picket DDGs on the bow
quarters), and the embarked air wing for CAP/AEW launches.
"""
import math
from dcs import mapping, planes
from dcs.mission import StartType
from dcs.task import (ActivateBeaconCommand, ActivateICLSCommand,
                      ActivateLink4Command, ActivateACLSCommand, CAP)
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

    # BRC: into wind when weather sets one, else curated open-sea heading —
    # but CLAMPED to ±60° of the curated heading. The curated axis is the
    # map's guaranteed sea room (validated against the coastline); an
    # unconstrained wind BRC steered the whole 40 km steaming leg wherever
    # the weather pointed, which beached the CSG on coast-tight maps
    # (Persian Gulf: wind from the west -> BRC 090 -> leg ended INLAND in
    # the UAE). Real carriers want wind down the deck, but the captain
    # keeps sea room first; a ±60° window still gives useful WOD while the
    # track never leaves validated open water.
    safe = anchor_cfg["heading"]
    wind_dir = getattr(getattr(m.weather, "wind_at_ground", None), "direction", 0)
    wind_spd = getattr(getattr(m.weather, "wind_at_ground", None), "speed", 0)
    brc = safe
    if wind_spd > 2:
        want = (wind_dir + 180) % 360
        dev = (want - safe + 180) % 360 - 180      # signed diff, -180..180
        brc = (safe + max(-60.0, min(60.0, dev))) % 360

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

    # Boat systems: activate ONLY what this hull actually supports in DCS
    # (carrier_decks.json "systems"). Blanket activation advertised ICLS/ACLS
    # on boats that can't provide them (1944 Essex, 1982 Invincible) — the
    # comm card must never list a system the pilot can't use.
    cv = comms.cfg("carrier")
    ship_id = grp.units[0].id
    systems = hull.get("systems", ["tacan", "icls", "link4", "acls"])
    wp = grp.points[0]
    notes = []
    if "tacan" in systems:
        wp.tasks.append(ActivateBeaconCommand(channel=int(cv["tacan"][:-1]),
                                              modechannel=cv["tacan"][-1],
                                              callsign=cv["tacan_callsign"],
                                              unit_id=ship_id, aa=False))
    if "icls" in systems:
        wp.tasks.append(ActivateICLSCommand(channel=cv["icls"], unit_id=ship_id))
        notes.append(f"ICLS {cv['icls']}")
    if "link4" in systems:
        wp.tasks.append(ActivateLink4Command(unit_id=ship_id, frequency=int(cv["link4"])))
        notes.append(f"Link4 {cv['link4']:.0f} (F-14: RIO enters this)")
    if "acls" in systems:
        wp.tasks.append(ActivateACLSCommand(unit_id=ship_id))
        notes.append("ACLS on")
    if not systems:
        notes.append("visual recovery - no shipboard nav/landing aids in this era")
    grp.set_frequency(cv["freq"])
    comms.add("Carrier", cv["callsign"], f"{cv['freq']:.3f}",
              cv["tacan"] if "tacan" in systems else "-",
              f"{csg.get('flagship_name', hull['label'])} - "
              + ", ".join(notes + [f"BRC {int(brc):03d}"]))
    return grp, brc


def add_plane_guard(m, country, hull_key, carrier_grp, brc, comms, warnings):
    """Plane-guard / SAR helo in STARBOARD DELTA for fixed-wing flight ops.

    US carrier doctrine (CV NATOPS): whenever the boat is launching or
    recovering fixed-wing aircraft, a rescue helo is AIRBORNE first and
    recovers last ("first off, last on"). It holds in the Starboard Delta
    pattern — LOW (300 ft and below) and on the STARBOARD side of the ship,
    roughly abeam the island at 1/4–1/2 nm, tracking the ship's course.
    Starboard, because the entire Case I fixed-wing pattern (the break,
    downwind, the groove) lives in left-hand turns on the PORT side; the
    helo's station keeps it permanently clear of the pattern while seconds
    away from a crew in the water off either catapult or the ramp.

    DCS implementation: air-start the air wing's SH-60 500 m off the
    starboard beam at 300 ft, then LINK it to the ship with a Follow task on
    the carrier group (offset: 500 m starboard, 100 m astern of the bow,
    +300 ft). The DCS AI then station-keeps on the ship itself — turns,
    speed changes, everything — instead of dead-reckoning a parallel route
    that drifts apart the moment the boat maneuvers.
    """
    from .resolver import resolve
    from .deck import _load_hull
    from dcs.task import Follow
    from dcs.mapping import Vector2
    hull = _load_hull(hull_key)
    helo_cfg = hull.get("csg", {}).get("airwing", {}).get("helo") if hull.get("csg") else None
    if not helo_cfg:
        # Historically accurate gaps: 1944 Essex (plane guard was a destroyer
        # station — already in the screen) and 1982 Invincible (820 NAS Sea
        # King HAS.5 — no DCS asset).
        warnings.append(f"{hull['label']}: no plane-guard helo in this air wing "
                        "(destroyer astern holds the plane-guard station)")
        return None
    helo_type = resolve(helo_cfg["type"])
    carrier_pos = carrier_grp.units[0].position
    stbd = (brc + 90) % 360
    # Starboard Delta: 500 m off the starboard beam, 300 ft, tracking BRC
    station = _offset(carrier_pos, 500, stbd)
    fg = m.flight_group_inflight(country, f"Angel {helo_cfg['squadron']}",
                                 helo_type, station, altitude=91, speed=60)
    fg.units[0].skill = Skill.High
    fg.points[0].speed = 46                       # settle to ship's 25 kts
    # THE LINK: follow the carrier group. Offset frame is the ship's own:
    # x = along heading (negative = astern), z = starboard. 300 ft above deck.
    fg.points[0].tasks.append(Follow(groupid=carrier_grp.id,
                                     group_offset=Vector2(-100, 500),
                                     altitude_difference=91))
    # fallback route parallel to the steaming leg (only matters if the Follow
    # target despawns; harmless otherwise — the Follow task owns the helo)
    leg_end = _offset(_offset(carrier_pos, 40000, brc), 500, stbd)
    fg.add_waypoint(leg_end, altitude=91, speed=46)
    freq = comms.freq("angel")
    fg.set_frequency(freq)
    comms.add("Plane guard", "Angel", f"{freq:.3f}", "-",
              f"{helo_cfg['squadron']} {helo_type.id} in Starboard Delta, "
              "300 ft off the starboard beam")
    return fg


def add_carrier_cap(m, country, hull_key, carrier_pos, brc, threat_bearing,
                    comms, warnings, gfx=None):
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
    freq = comms.freq("cap")
    fg.set_frequency(freq)
    comms.add("CAP", cap_cfg["squadron"].split()[0], f"{freq:.3f}", "-",
              f"{airwing['label']} {cap_type.id} x2, stn 30nm on threat axis")
    if gfx is not None:
        gfx["cap"] = (st1, st2, f"CAP {cap_cfg['squadron']} {freq:.3f}")
    return fg


def add_carrier_aew(m, country, hull_key, carrier_pos, brc, threat_bearing,
                    comms, warnings, gfx=None):
    """Air-wing E-2 Hawkeye AEW orbit behind the CSG (AAW picture for the group)."""
    from .resolver import resolve
    from .deck import _load_hull
    airwing = _load_hull(hull_key).get("csg", {}).get("airwing")
    if not airwing:
        warnings.append("no air wing data for this hull - AEW skipped")
        return None
    aew_cfg = airwing.get("aew")
    if not aew_cfg:
        warnings.append("this air wing has no AEW aircraft (historically accurate "
                        "for the 1982 task force) - AEW skipped")
        return None
    aew_type = resolve(aew_cfg["type"])
    pos = _offset(carrier_pos, 45000, (threat_bearing + 180) % 360)  # 25nm behind CSG
    freq = comms.freq("aew")
    fg = m.awacs_flight(
        country, f"AEW {aew_cfg['squadron']}", aew_type, airport=None,
        position=pos, race_distance=48000, heading=(threat_bearing + 90) % 360,
        altitude=AEW_ALT, speed=500, frequency=freq)
    comms.add("AEW", aew_cfg["squadron"].split()[0], f"{freq:.3f}", "-",
              f"{airwing['label']} {aew_type.id} overhead the force")
    if gfx is not None:
        gfx["aew"] = (pos, (threat_bearing + 90) % 360, 48000,
                      f"AEW {aew_cfg['squadron']} {freq:.3f}")
    return fg
