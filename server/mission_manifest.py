"""Project engine facts into the versioned Mission Kit contract.

Kept separate from transport, temp-file cleanup, and analytics. The compact
header stays backwards-compatible while result ownership lives in the client.
"""
import json


def kit_manifest(stats: dict) -> dict:
    from missiongen import loadouts as _lo
    from missiongen.bfm import geometry_summary
    kit = {
        "flight": stats.get("flight_counts"),
        "kneeboard_pages": stats.get("kneeboard_pages", 0),
        "dtc": bool(stats.get("dtc_units_tagged")),
        "route": stats.get("route"),
        # The clock the route is anchored on ("tot 06:42:00"), when timed.
        "timing": (f"{stats['timing'].get('anchor')} "
                   f"{stats['timing'].get('anchor_clock') or stats['timing'].get('takeoff_clock') or ''}").strip()
                  if stats.get("timing") else None,
        "bfm": stats.get("bfm"),
        "bfm_setup": stats.get("bfm_setup"),
        "bfm_geometry": geometry_summary(stats.get("bfm_setup", "neutral")) if stats.get("bfm") else None,
        "threat_level": stats.get("threat_level"),
        "support": stats.get("support", [])[:6],
        # What the bandits are CARRYING. Correct-but-invisible is how the last
        # three features became discovery problems, so the fit surfaces on the
        # Mission Kit panel too, not only inside the documents.
        # YOUR fit. The user never sees a pylon picker, so the one place
        # they learn what they took off with is here and the brief.
        "player_loadout": stats.get("player_loadout"),
        "player_role": stats.get("player_loadout_role"),
        "enemy_air": [{"n": a["count"], "t": a["type"],
                       "r": _lo.ROLE_TAGS.get(a["role"], a["role"]),
                       "fit": a["fit"], "imp": a["implication"]}
                      for a in _lo.summarize(stats.get("enemy_air"))[:3]],
    }
    # The header has a hard budget and a TRUNCATED payload is worse than a
    # missing one (JSON.parse fails, the panel silently loses every row), so
    # shed enemy_air rows until it fits instead of slicing the string.
    while len(json.dumps(kit)) > 1800 and kit["enemy_air"]:
        kit["enemy_air"].pop()
    return kit


def navigation_manifest(stats, miz):
    """JSON-safe leg cards plus every emitted human flight's native route.

    Native speeds are m/s, altitudes metres, x/y theatre metres, ETAs seconds
    from mission start. Leg-card kt/alt_ft fields retain their labelled units.
    """
    from dcs.mapping import Point
    import dcs.lua as lua
    import zipfile
    def plain(value):
        if isinstance(value, Point):
            ll = value.latlng()
            return {'x':value.x, 'y':value.y, 'latitude':ll.lat, 'longitude':ll.lng}
        if isinstance(value, dict):
            return {k:plain(v) for k,v in value.items()}
        if isinstance(value,(list,tuple)):
            return [plain(v) for v in value]
        return value
    def values(value):
        return list(value.values()) if isinstance(value,dict) else list(value or [])
    with zipfile.ZipFile(miz) as archive:
        mission = lua.loads(archive.read('mission').decode())['mission']
    flights=[]
    for side in ('blue','red','neutrals'):
        for country in values(mission.get('coalition',{}).get(side,{}).get('country')):
            for kind in ('plane','helicopter'):
                for group in values(country.get(kind,{}).get('group')):
                    if not any(u.get('skill') in ('Player','Client') for u in values(group.get('units'))):
                        continue
                    points=[{k:p.get(k) for k in ('name','x','y','alt','alt_type','speed','action','airdromeId','linkUnit','helipadId','ETA','ETA_locked')}
                            for p in values(group.get('route',{}).get('points'))]
                    flights.append({'name':group.get('name'),'coalition':side,'points':points})
    return {'route':plain(stats.get('route_legs') or stats.get('wk_route') or stats.get('cq_route') or []),
            'target':stats.get('route_target'), 'timing':plain(stats.get('timing')),
            'native_units':{'coordinates':'theatre metres','altitude':'metres','speed':'metres per second','ETA':'seconds from mission start'},
            'mission_start_seconds':mission.get('start_time'), 'flights':flights}
