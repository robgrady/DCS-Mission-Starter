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
    schema['x-engine-version'] = __version__
    schema['x-share-schema'] = SHARE_SCHEMA
    return schema
