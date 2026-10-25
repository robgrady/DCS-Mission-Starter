"""Explicit player routes: strict inputs, one native route and shared leg facts.

No executable waypoint tasks and no inferred terrain clearance. PyDCS helpers
take km/h; the public recipe and native saved speeds are metres/second TAS.
"""
import re

from .recipe import RecipeError
from .precision import _number, validate_position, point

MAX_POINTS = 32
PURPOSES = ('transit', 'rendezvous', 'ip', 'target', 'egress')


def validate_route(r):
    if r.waypoints is None:
        if r.route_recovery is not None:
            raise RecipeError('route_recovery requires waypoints.')
        return
    from .build_context import CREW_OPS_TEMPLATES, _scenario_templates
    tpl = _scenario_templates().get(r.template, {})
    if (r.cq_ride or r.formation or r.template in CREW_OPS_TEMPLATES
            or tpl.get('wk_ride') or tpl.get('formation')):
        raise RecipeError('waypoints cannot replace a fixed training route.')
    if r.bb_route:
        raise RecipeError('waypoints and bb_route are alternative route modes; turn bb_route off.')
    if (r.timing_anchor != 'takeoff' or r.timing_at is not None
            or r.timing_hold_min or r.timing_coach or r.timing_package):
        raise RecipeError('Authored waypoints currently use advisory ETAs only; disable automatic-route timing options.')
    if not 1 <= len(r.waypoints) <= MAX_POINTS:
        raise RecipeError(f'waypoints must contain 1–{MAX_POINTS} points, excluding the start and recovery.')
    ids, names = set(), set()
    for i, w in enumerate(r.waypoints):
        label = f'waypoints[{i}]'
        if not isinstance(w, dict) or set(w) - {'id', 'name', 'position', 'altitude', 'speed', 'purpose'}:
            raise RecipeError(f'{label} accepts id, name, position, altitude, speed and purpose only.')
        if not {'id', 'name', 'position', 'altitude', 'speed'} <= set(w):
            raise RecipeError(f'{label} requires id, name, position, altitude and speed.')
        if not isinstance(w['id'], str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,40}', w['id']):
            raise RecipeError(f'{label}.id must be 1–40 ASCII letters, digits, hyphens or underscores.')
        name = w['name']
        if (not isinstance(name, str) or not 1 <= len(name) <= 24
                or name != name.strip() or any(ord(c) < 32 or ord(c) == 127 for c in name)):
            raise RecipeError(f'{label}.name must contain 1–24 characters without surrounding whitespace or control characters.')
        if w['id'] in ids or w['id'].casefold() == 'recovery' or name.casefold() in names or name.casefold() == 'recovery':
            raise RecipeError(f'{label}: waypoint IDs and names must be unique; RECOVERY and its recovery ID are reserved.')
        ids.add(w['id']); names.add(name.casefold())
        validate_position(w['position'], label + '.position')
        from .map_bounds import check_position
        check_position(w['position'], r.map, label + '.position')
        if not _number(w['altitude']) or not 1 <= w['altitude'] <= 25000:
            raise RecipeError(f'{label}.altitude must be 1–25000 metres MSL (BARO), not AGL.')
        if not _number(w['speed']) or not 1 <= w['speed'] <= 1000:
            raise RecipeError(f'{label}.speed must be 1–1000 metres/second TAS; check the aircraft envelope.')
        if w.get('purpose', 'transit') not in PURPOSES:
            raise RecipeError(f'{label}.purpose must be one of {", ".join(PURPOSES)}; purposes do not add actions or targets.')
    if r.route_recovery not in (None, 'home'):
        from .resolver import load_json, resolve_terrain
        terrain = resolve_terrain(load_json('maps')[r.map]['terrain_class'])()
        if r.route_recovery not in {a.name for a in terrain.airport_list()}:
            raise RecipeError('route_recovery must be home or an exact airfield name on this map.')


def apply(builder, ctx, player):
    from . import routing, timing
    r, group, m = builder.recipe, player.player_group, ctx.mission
    if group is None:
        raise RecipeError('Authored waypoints require a player flight.')
    # Preserve only spawn/takeoff points. Existing template transit points
    # must not survive beside an explicitly authored route.
    group.points[:] = [p for i, p in enumerate(group.points)
                       if i == 0 or str(p.type).startswith('TakeOff')]
    origin = group.points[-1].position
    legs = []
    for i, w in enumerate(r.waypoints):
        p = point(w['position'], m.terrain, f'waypoints[{i}].position', r.map)
        wp = group.add_waypoint(p, altitude=w['altitude'], speed=w['speed'] * 3.6, name=w['name'])
        wp.alt_type = 'BARO'
        wp.speed_locked, wp.ETA_locked = True, False
        legs.append({'name': w['name'], 'point': p, 'alt': w['altitude'],
                     'speed': w['speed'] * 3.6, 'id': w['id'], 'purpose': w.get('purpose', 'transit')})
    if r.route_recovery is not None:
        carrier = builder._csg.units[0] if ctx.carrier_home and builder._csg else None
        airport = player.home if r.route_recovery == 'home' else next(
            a for a in m.terrain.airport_list() if a.name == r.route_recovery)
        routing.add_recovery(group, home_airport=airport if r.route_recovery != 'home' or carrier is None else None,
                             home_carrier=carrier if r.route_recovery == 'home' else None)
        end = group.points[-1]; end.name = 'RECOVERY'
        end.ETA_locked = False
        legs.append({'name': 'RECOVERY', 'point': end.position, 'alt': end.alt,
                     'speed': end.speed * 3.6, 'id': 'recovery', 'purpose': 'recovery'})
    rows = routing.leg_card(origin, legs, 'START')
    for row, leg in zip(rows, legs):
        row.update(id=leg['id'], purpose=leg['purpose'], altitude_m=leg['alt'],
                   speed_mps=leg['speed'] / 3.6, altitude_reference='MSL')
    # Estimates only: exact distances and requested TAS, no generic era climb
    # schedule imposed on an authored airborne route. Human points stay unlocked.
    elapsed = timing.GROUND_S.get(r.start, 0)
    clock = m.start_time.hour * 3600 + m.start_time.minute * 60 + m.start_time.second
    for row, leg, wp in zip(rows, legs, group.points[-len(legs):]):
        seconds = int(round(row['nm'] * 1852 / max(leg['speed'] / 3.6, 1)))
        elapsed += seconds
        row.update(eta=timing.hhmmss(clock + elapsed), eta_s=elapsed, leg_s=seconds)
        wp.ETA = elapsed
        wp.ETA_locked = False
    ctx.stats.update(route=' > '.join(l['name'] for l in legs), route_mode='authored',
                     route_legs=rows, route_target='Author-defined route',
                     authored_waypoints=r.waypoints, route_recovery=r.route_recovery)
    builder.warnings.append('Authored route: MSL altitudes and TAS speeds are preserved. ETAs are estimates without wind/climb allowance; terrain clearance, aircraft limits and recovery access require author review. Purpose labels add no targets or actions.')
    return rows


def brief_lines(rows):
    """Complete names, coordinates and native units; reused by all documents."""
    lines = ['AUTHORED FLIGHT PLAN',
             'MSL altitudes; true airspeed. ETAs are advisory estimates without wind/climb allowance.',
             'Purpose labels add no targets or actions. Check terrain clearance and recovery access in DCS.']
    for i, row in enumerate(rows, 1):
        ll = row['point'].latlng()
        lines.extend([f"{i:02d} {row['to']} — {row['purpose']}",
            f"{ll.lat:.6f}, {ll.lng:.6f} | {row['altitude_m']:g} m MSL | {row['speed_mps']:g} m/s TAS",
            f"{row['heading']:03d} deg true | {row['nm']:.1f} NM | ETA {row['eta']}"])
    return lines
