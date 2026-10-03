"""Public recipe schema derived from the engine, without expanding presets.

The API keeps omission semantics: fields omitted by the client may be filled
by its selected template. Schema defaults document values; validation remains
strict in Recipe.from_dict and its cross-field/domain checks.
"""
from pydantic import TypeAdapter

from missiongen import __version__
from missiongen.recipe import Recipe, RECIPE_ENUMS
from missiongen.share import SHARE_SCHEMA


def recipe_json_schema() -> dict:
    schema = TypeAdapter(Recipe).json_schema()
    for name, values in RECIPE_ENUMS.items():
        schema['properties'][name]['enum'] = list(values)
    schema['x-engine-version'] = __version__
    schema['x-share-schema'] = SHARE_SCHEMA
    return schema
