"""Placement results and pure browser presets expose explicit boundaries."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
from typing import get_type_hints
from dcs.unitgroup import ShipGroup, FlyingGroup
import json

import pytest
from fastapi.testclient import TestClient
from missiongen import Recipe
from missiongen.builder import StarterBuilder
from missiongen.build_context import prepare_world
from missiongen.phases.carrier import place_carrier, CarrierPlacement
from server.app import app
from test_mission_kit_wiring import run_js


def test_no_carrier_has_an_explicit_empty_result_without_stat_mutation():
    builder = StarterBuilder(Recipe(era="modern", bb_carrier=False))
    ctx = prepare_world(builder)
    before = deepcopy(ctx.stats)
    result = place_carrier(ctx, builder.recipe, builder.rng, builder.warnings)
    assert (result.group, result.brc, result.hull_key, result.strike) == (None,) * 4
    assert result.support_names == () and result.graphics == {}
    assert result.deck_statics is None and ctx.stats == before
    with pytest.raises(FrozenInstanceError):
        result.hull_key = 'forrestal'


def test_carrier_phase_returns_its_facts_without_mutating_world_stats():
    builder = StarterBuilder(Recipe.from_dict({'template':'cv_alpha_strike_escort', 'seed':19}))
    ctx = prepare_world(builder)
    before = deepcopy(ctx.stats)
    result = place_carrier(ctx, builder.recipe, builder.rng, builder.warnings)
    assert result.group and result.strike and result.hull_key == 'forrestal'
    assert result.group.name in result.support_names
    assert result.strike.name in result.support_names
    assert result.graphics['carrier'][0] == result.group.units[0].position
    assert ctx.stats == before


def test_pure_browser_presets_do_not_mutate_the_supplied_catalog():
    with TestClient(app) as client:
        opt = client.get('/api/options').json()
    out = run_js('const options=' + json.dumps(opt) + ''';
const before=JSON.stringify(options);
const result=effectiveScenarioPreset(options,'wk_10_threeship','coldwar','sinai');
const fields=effectiveMapPreset(options,'sinai','coldwar',result.lineup);
result.slots=4;console.log(JSON.stringify({unchanged:before===JSON.stringify(options),fields,home:result.home_airbase}));
''', [])
    assert out['unchanged'] and out['home'] == 'Beni Suef'
    assert out['fields']['blue_airbases'] == opt['maps']['sinai']['lineups']['proud_phantom']['blue_airbases']


def test_phase_result_annotations_resolve_native_pydcs_models():
    hints = get_type_hints(CarrierPlacement)
    assert hints['group'] == ShipGroup | None
    assert hints['strike'] == FlyingGroup | None
