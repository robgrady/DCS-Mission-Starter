"""Public recipe schema derived from the engine, without expanding presets.

The API keeps omission semantics: fields omitted by the client may be filled
by its selected template. Schema defaults document values; validation remains
strict in Recipe.from_dict and its cross-field/domain checks.
"""
from pydantic import TypeAdapter

from missiongen import __version__
from missiongen.recipe import (Recipe, RECIPE_ENUMS, recipe_numeric_bounds,
                               FILL_BOUNDS, TARGET_PACKAGE_BOUNDS, CALLSIGN_LENGTH)
from missiongen.share import SHARE_SCHEMA


def recipe_json_schema() -> dict:
    schema = TypeAdapter(Recipe).json_schema()
    schema['additionalProperties'] = False
    for name, values in RECIPE_ENUMS.items():
        schema['properties'][name]['enum'] = list(values)
    bounds = recipe_numeric_bounds()
    for name, (lower, upper) in bounds.items():
        schema['properties'][name].update(minimum=lower, maximum=upper)
    schema['properties']['veteran_wingmen']['description'] = (
        'Trailing High-skill AI aircraft. Must be less than slots so at least '
        'one human seat remains. Unavailable for fixed Case III and crew-ops flights.')
    # Standard JSON Schema can express the finite cross-field seat constraint.
    # An omitted slots value is resolved by the template/engine, not assumed here.
    schema['allOf'] = [
        {'if': {'required': ['slots'], 'properties': {'slots': {'const': slots}}},
         'then': {'properties': {'veteran_wingmen': {'maximum': slots - 1}}}}
        for slots in range(bounds['slots'][0], bounds['slots'][1] + 1)
    ]
    packages = next(branch for branch in schema['properties']['target_packages']['anyOf']
                    if branch.get('type') == 'array')
    from missiongen.targets import TARGET_PACKAGES
    packages.update(minItems=TARGET_PACKAGE_BOUNDS[0], maxItems=TARGET_PACKAGE_BOUNDS[1],
                    items={'type': 'string', 'enum': list(TARGET_PACKAGES)})
    schema['properties']['dress_overrides']['additionalProperties'] = {
        'type': 'integer', 'minimum': FILL_BOUNDS[0], 'maximum': FILL_BOUNDS[1]}
    mix = next(branch for branch in schema['properties']['dress_mix']['anyOf']
               if branch.get('type') == 'object')
    mix['additionalProperties'] = {'type': 'integer', 'minimum': 0}
    schema['properties']['callsign']['description'] = (
        f'Surrounding whitespace is trimmed; the result must contain '
        f'{CALLSIGN_LENGTH[0]}-{CALLSIGN_LENGTH[1]} characters.')
    schema['properties']['mission_date'].update(description='Exact YYYY-MM-DD within the selected era; overrides scenario date. Presets remain era-based.', format='date')
    schema['properties']['start_position'] = {'anyOf': [position_json_schema(), {'type':'null'}], 'default':None,
        'description':'Exact airborne lead position. WGS84 lat/lon degrees OR DCS theatre x/y metres. Requires start=air. Ground parking and fixed training starts are excluded.'}
    schema['properties']['start_altitude'] = {'anyOf': [{'type':'number','minimum':1,'maximum':25000},{'type':'null'}],
        'default':None, 'description':'Airborne start altitude in metres MSL (BARO), not feet or AGL. Author must check terrain clearance. Requires start=air.'}
    schema['properties']['start_speed'] = {'anyOf': [{'type':'number','minimum':1,'maximum':1000},{'type':'null'}],
        'default':None, 'description':'Exact airborne start true airspeed in metres/second, not knots, km/h or IAS. Requires start=air and a normal player flight. Check flight envelope.'}
    schema['properties']['start_time'] = {'anyOf': [{'type':'string', 'pattern':r'^([01][0-9]|2[0-3]):[0-5][0-9](:[0-5][0-9])?$'},{'type':'null'}],
        'default':None, 'description':'Exact mission start local clock HH:MM or HH:MM:SS. Requires timing_anchor=takeoff. Does not shift the requested date.'}
    schema['properties']['player_stores'] = {'anyOf': [{'type':'object','maxProperties':64,
        'propertyNames':{'pattern':r'^(0|[1-9][0-9]{0,2})$'}, 'additionalProperties':{'type':'string','minLength':1}}, {'type':'null'}],
        'default':None, 'description':'Complete player-flight station-to-CLSID fit, e.g. {"1":"CLSID"}. Omitted stations stay empty; {} is clean; null keeps presets. Discover exact aircraft/stations in the stores catalog. Requires player_arm=true and player_fit=auto. Fixed training fits are excluded. Checks individual station lists, not every physical multi-store constraint.'}
    schema['properties']['allow_anachronistic_stores']['description'] = 'Explicit fictional-fit override for recorded weapon service windows, only with player_stores. Preserves mission date, labels historical context fictional and reports conflicts. Never bypasses station compatibility.'
    schema['properties']['player_slot']['description'] = 'Native DCS player/client control. Null preserves automatic solo/multiplayer seating. player requires one human aircraft; client allows a single multiplayer client.'
    from missiongen.precision import VIEWS
    schema['properties']['map_view'] = {'anyOf': [
        {'type':'object', 'minProperties':1, 'additionalProperties':False, 'properties':{
            'center':position_json_schema(), 'zoom':{'type':'number','minimum':1000,'maximum':5000000},
            'visibility':{'type':'string','enum':list(VIEWS)}}}, {'type':'null'}],
        'default':None, 'description':'Initial saved map framing and forced F10 unit visibility; independent of map_layers graphics. zoom uses native DCS map units.'}
    schema['x-engine-version'] = __version__
    schema['x-share-schema'] = SHARE_SCHEMA
    return schema


def position_json_schema():
    """Two explicit coordinate systems, with no inferred units."""
    return {'oneOf': [
        {'type': 'object', 'properties': {
            'lat': {'type': 'number', 'minimum': -90, 'maximum': 90},
            'lon': {'type': 'number', 'minimum': -180, 'maximum': 180}},
         'required': ['lat', 'lon'], 'additionalProperties': False},
        {'type': 'object', 'properties': {'x': {'type': 'number'}, 'y': {'type': 'number'}},
         'required': ['x', 'y'], 'additionalProperties': False}]}
