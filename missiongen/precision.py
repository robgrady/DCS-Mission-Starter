"""Explicit mission-author inputs; omitted values preserve authored defaults."""
from datetime import date
import math

from .recipe import RecipeError

VIEWS = ('all', 'allies', 'only_allies', 'my_aircraft', 'map_only')


def _number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def validate_position(value, name):
    if not isinstance(value, dict) or set(value) not in ({'lat', 'lon'}, {'x', 'y'}):
        raise RecipeError(f'{name} must contain exactly lat/lon (degrees) or x/y (DCS metres).')
    if not all(_number(n) for n in value.values()):
        raise RecipeError(f'{name} coordinates must be finite numbers.')
    if 'lat' in value and not (-90 <= value['lat'] <= 90 and -180 <= value['lon'] <= 180):
        raise RecipeError(f'{name} latitude/longitude is out of range.')


def validate_precision(r):
    from .resolver import load_json
    from .recipe import Recipe
    Recipe._validate_field_types({name: getattr(r, name) for name in (
        'mission_date', 'start_position', 'start_altitude', 'start_speed', 'start_time', 'player_slot', 'map_view')})
    if r.player_slot not in (None, 'player', 'client'):
        raise RecipeError('player_slot must be player, client or null.')
    if r.mission_date is not None:
        try:
            when = date.fromisoformat(r.mission_date)
            if when.isoformat() != r.mission_date:
                raise ValueError()
        except ValueError:
            raise RecipeError('mission_date must be a valid YYYY-MM-DD date.') from None
        window = load_json('eras')[r.era]['window']
        if not window[0] <= when.year <= window[1]:
            raise RecipeError(f'mission_date must fall within era={r.era!r} ({window[0]}–{window[1]}).')
        # A solved TOT can cross midnight and silently invalidate an exact date.
        if r.timing_anchor != 'takeoff':
            raise RecipeError('mission_date requires timing_anchor=takeoff; push/TOT timing may move the date.')
    if r.start_time is not None:
        from datetime import time
        import re
        if not re.fullmatch(r'\d{2}:\d{2}(?::\d{2})?', r.start_time):
            raise RecipeError('start_time must be a local clock time HH:MM or HH:MM:SS.')
        try:
            time.fromisoformat(r.start_time)
        except ValueError:
            raise RecipeError('start_time must be a valid local clock time, 00:00:00–23:59:59.') from None
        if r.timing_anchor != 'takeoff':
            raise RecipeError('start_time requires timing_anchor=takeoff; push/TOT timing owns the start clock.')
    explicit_start = r.start_position is not None or r.start_altitude is not None or r.start_speed is not None
    if explicit_start:
        from .build_context import CREW_OPS_TEMPLATES, _scenario_templates
        tpl = _scenario_templates().get(r.template, {})
        if (r.start != 'air' or r.home_airbase == 'CARRIER' or r.cq_ride
                or r.formation or r.template in CREW_OPS_TEMPLATES
                or tpl.get('wk_ride') or tpl.get('formation')):
            raise RecipeError('start_position/start_altitude/start_speed require a normal airborne flight (start=air); fixed training and carrier starts own their placement.')
    if r.start_position is not None:
        validate_position(r.start_position, 'start_position')
        from .map_bounds import check_position
        check_position(r.start_position, r.map, 'start_position')
    if r.start_altitude is not None and (not _number(r.start_altitude) or not 1 <= r.start_altitude <= 25000):
        raise RecipeError('start_altitude must be 1–25000 metres MSL; terrain clearance is the author\'s responsibility.')
    if r.start_speed is not None and (not _number(r.start_speed) or not 1 <= r.start_speed <= 1000):
        raise RecipeError('start_speed must be 1–1000 metres/second TAS; check the aircraft flight envelope.')
    if r.player_slot is not None:
        from .build_context import CREW_OPS_TEMPLATES, _scenario_templates
        tpl = _scenario_templates().get(r.template, {})
        if r.formation or r.cq_ride or r.template in CREW_OPS_TEMPLATES or tpl.get('formation'):
            raise RecipeError('player_slot is unavailable for fixed training/crew flights.')
        if r.player_slot == 'player' and r.slots - r.veteran_wingmen != 1:
            raise RecipeError('player_slot=player requires exactly one human aircraft; use client for multiplayer flights.')
    if r.map_view is not None:
        v = r.map_view
        if not v or set(v) - {'center', 'zoom', 'visibility'}:
            raise RecipeError('map_view accepts center, zoom and visibility; supply at least one.')
        if 'center' in v:
            validate_position(v['center'], 'map_view.center')
            from .map_bounds import check_position
            check_position(v['center'], r.map, 'map_view.center')
        if 'zoom' in v and (not _number(v['zoom']) or not 1000 <= v['zoom'] <= 5000000):
            raise RecipeError('map_view.zoom must be 1000–5000000 native DCS map units.')
        if 'visibility' in v and v['visibility'] not in VIEWS:
            raise RecipeError('map_view.visibility must be ' + ', '.join(VIEWS) + '.')


def dated_setting(r, preset, era_cfg):
    if r.allow_anachronistic_stores:
        preset = {**preset, 'historical_classification': 'fictional_exercise',
                  'historical_notes': [*preset.get('historical_notes', []),
                    'Author enabled an intentional fictional equipment fit. The mission date is '
                    'preserved; exact player stores bypass recorded weapon service windows. '
                    'Station compatibility still applies. This is not a historical reconstruction.']}
    if r.mission_date is None:
        return preset
    from .historical_world import scenario_date
    if scenario_date(preset, era_cfg).isoformat() == r.mission_date:
        return preset
    return {**preset, 'scenario_date': r.mission_date,
            'historical_classification': ('historically_inspired_adaptation'
                if preset.get('historical_classification') == 'reconstruction'
                else preset.get('historical_classification', 'historically_inspired_adaptation')),
            'historical_notes': [*preset.get('historical_notes', []),
                'Author-selected date overrides the scenario default. Coalition/base presets and '
                'historical overlays remain era-based; this is not a reconstruction of that exact day.']}


def point(value, terrain, name, map_key):
    from dcs.mapping import Point, LatLng
    from .map_bounds import check_position
    check_position(value, map_key, name)
    p = (Point.from_latlng(LatLng(value['lat'], value['lon']), terrain)
         if 'lat' in value else Point(value['x'], value['y'], terrain))
    return p


def apply_air_start(r, mission, group):
    if r.start_position is not None:
        pos = point(r.start_position, mission.terrain, 'start_position', r.map)
        first = group.units[0].position
        dx, dy = pos.x - first.x, pos.y - first.y
        from dcs.mapping import Point
        for u in group.units:
            u.position = Point(u.position.x + dx, u.position.y + dy, mission.terrain)
        group.points[0].position = pos
    if r.start_altitude is not None:
        for u in group.units:
            u.alt = r.start_altitude
            u.alt_type = 'BARO'
        group.points[0].alt = r.start_altitude
        group.points[0].alt_type = 'BARO'
    if r.start_speed is not None:
        # Direct native properties are m/s. PyDCS waypoint helpers take km/h.
        for u in group.units:
            u.speed = r.start_speed
        group.points[0].speed = r.start_speed


def apply_map_view(r, mission):
    if r.map_view is None:
        return
    from dcs.terrain import MapView
    from dcs.forcedoptions import ForcedOptions
    v = r.map_view
    # Do not mutate terrain.map_view_default, which may be reused by callers.
    center = point(v['center'], mission.terrain, 'map_view.center', r.map) if 'center' in v else mission.map.position
    mission.map = MapView(center, mission.terrain, v.get('zoom', mission.map.zoom))
    if 'visibility' in v:
        mission.forced_options.options_view = dict(zip(VIEWS, (
            ForcedOptions.Views.All, ForcedOptions.Views.Allies, ForcedOptions.Views.OnlyAllies,
            ForcedOptions.Views.MyAircraft, ForcedOptions.Views.OnlyMap)))[v['visibility']]
