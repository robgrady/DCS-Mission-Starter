"""Explicit agent recipe inputs must survive validation, sharing and native save."""
from datetime import date
import json
import zipfile

import anyio
import dcs.lua as lua
from mcp import Client
import pytest

from missiongen import Recipe
from missiongen.builder import StarterBuilder
from missiongen.recipe import RecipeError
from missiongen.share import encode_recipe, decode_recipe
from server.recipe_contract import recipe_json_schema
from server.mcp_server import mcp

BASE = dict(era='modern', start='air', bb_dressing=False, bb_ambient=False,
            bb_sams=False, bb_kneeboard=False, bb_branding=False)
EXACT = dict(mission_date='2001-02-03', start_position={'lat':42.1,'lon':42.1},
             start_altitude=4100.5, player_slot='client',
             map_view={'center':{'lat':42.2,'lon':42.2},'zoom':145000,'visibility':'allies'})
FIELDS = set(EXACT)


def values(obj):
    return obj.values() if isinstance(obj, dict) else obj


def human_group(native):
    for side in native['coalition'].values():
        for country in values(side.get('country', {})):
            for group in values(country.get('plane', {}).get('group', {})):
                if any(u['skill'] in ('Player','Client') for u in values(group['units'])):
                    return group
    pytest.fail('no human flight saved')


def save(recipe, path):
    builder = StarterBuilder(recipe)
    mission = builder.build()
    mission.save(str(path))
    with zipfile.ZipFile(path) as archive:
        native = lua.loads(archive.read('mission').decode())['mission']
    return builder, mission, native


def test_exact_fields_reach_native_file_and_historical_facts(tmp_path):
    r = Recipe.from_dict({**BASE, **EXACT, 'slots':4, 'veteran_wingmen':3})
    b, m, n = save(r, tmp_path/'exact.miz')
    assert n['date'] == {'Year':2001,'Month':2,'Day':3}
    assert b.context.historical.mission_date == b.document_facts.mission_date == date(2001,2,3)
    assert b.context.historical.classification == 'fictional_exercise'
    assert any('Author-selected date' in s for s in b.context.historical.notes)
    g = human_group(n)
    units = list(values(g['units']))
    p = list(values(g['route']['points']))[0]
    lead = units[0]
    requested = b.phases[1].player_group.points[0].position.latlng()
    assert requested.lat == pytest.approx(42.1)
    assert requested.lng == pytest.approx(42.1)
    assert lead['x'] == pytest.approx(p['x'])
    assert lead['y'] == pytest.approx(p['y'])
    assert all(u['alt'] == 4100.5 for u in units)
    assert p['alt'] == 4100.5 and p['alt_type'] == 'BARO'
    assert [u['skill'] for u in units] == ['Client','High','High','High']
    assert len({(u['x'],u['y']) for u in units}) == 4
    assert n['map']['zoom'] == 145000
    center = m.map.position.latlng()
    assert center.lat == pytest.approx(42.2) and center.lng == pytest.approx(42.2)
    assert n['forcedOptions']['optionsView'] == 'optview_allies'
    assert decode_recipe(encode_recipe(r)).to_dict() == r.to_dict()
    save(r, tmp_path/'again.miz')
    assert (tmp_path/'exact.miz').read_bytes() == (tmp_path/'again.miz').read_bytes()


def test_exact_start_survives_target_relative_automatic_reposition(tmp_path):
    # Template normally replaces player placement once targets exist.
    r = Recipe.from_dict({**BASE, **EXACT, 'template':'qf_guns','bb_targets':True})
    b, m, n = save(r, tmp_path/'target.miz')
    p = b.phases[1].player_group.points[0]
    assert p.position.latlng().lat == pytest.approx(42.1)
    assert p.alt == 4100.5


def test_local_coordinates_and_solo_player_slot(tmp_path):
    r = Recipe.from_dict({**BASE, 'start_position':{'x':-296000,'y':653000},
                         'start_altitude':3000, 'player_slot':'player',
                         'map_view':{'center':{'x':-296000,'y':653000},'visibility':'map_only'}})
    _, _, n = save(r, tmp_path/'local.miz')
    g = human_group(n)
    u = next(iter(values(g['units'])))
    assert (u['x'],u['y'],u['alt'],u['skill']) == (-296000,653000,3000,'Player')
    assert n['forcedOptions']['optionsView'] == 'optview_onlymap'
    assert n['map']['centerX'] == -296000 and n['map']['centerY'] == 653000


@pytest.mark.parametrize('extra', [
    {'mission_date':'2001-02-30'}, {'mission_date':'20010203'}, {'mission_date':'1944-06-06'},
    {'mission_date':'2001-02-03','timing_anchor':'tot'},
    {'start_position':{'lat':42}}, {'start_position':{'lat':True,'lon':42}},
    {'start_position':{'lat':91,'lon':42}}, {'start_position':{'x':float('nan'),'y':1}},
    {'start_position':{'x':1,'y':2,'alt':3}}, {'start_position':{'x':1,'y':2},'start':'cold'},
    {'start_altitude':True}, {'start_altitude':0}, {'start_altitude':25001},
    {'start_altitude':float('inf')}, {'start_altitude':3000,'home_airbase':'CARRIER'},
    {'start_altitude':3000,'formation':'route'}, {'start_altitude':3000,'template':'wk_1_stepstart'},
    {'player_slot':'gunner'}, {'player_slot':'player','slots':2},
    {'map_view':{}}, {'map_view':{'zoom':True}}, {'map_view':{'zoom':100}},
    {'map_view':{'visibility':'enemy_only'}}, {'map_view':{'center':{'x':1}}},
    {'map_view':{'centerX':1}},
])
def test_invalid_precision_fields_fail_before_generation(extra):
    with pytest.raises(RecipeError):
        Recipe.from_dict({**BASE, **extra})


@pytest.mark.parametrize('extra', [
    {'start_position':{'lat':0,'lon':0}},
    {'map_view':{'center':{'x':1e12,'y':1e12}}},
])
def test_coordinates_outside_selected_terrain_are_rejected(extra):
    with pytest.raises(RecipeError, match='outside.*map bounds'):
        StarterBuilder(Recipe.from_dict({**BASE, **extra})).build()


def test_default_fields_do_not_change_existing_share_codes():
    assert not FIELDS.intersection(json.loads(__import__('base64').urlsafe_b64decode(encode_recipe(Recipe())+'=='))['r'])
    assert all(getattr(Recipe(), f) is None for f in FIELDS)


def test_mcp_discovery_and_validation_publish_all_five_fields_inline():
    async def run():
        async with Client(mcp) as c:
            for tool in (await c.list_tools()).tools:
                schema = tool.input_schema
                assert '$ref' not in json.dumps(schema)
                if tool.name.endswith(('validate_recipe','generate_mission')):
                    props = schema['properties']['params']['properties']['recipe']['properties']
                    assert FIELDS <= props.keys()
                    assert props['start_altitude']['description'].startswith('Airborne')
            result = await c.call_tool('sortiestarter_validate_recipe', {'params':{'recipe':{**BASE, **EXACT}}})
            assert not result.is_error, result.content
            assert all(result.structured_content['recipe'][k] == v for k,v in EXACT.items())
            bad = await c.call_tool('sortiestarter_list_catalog', {'params':{'kind':'maps','limit':51}})
            assert bad.is_error
    anyio.run(run)
    canonical = recipe_json_schema()
    assert 'allOf' in canonical
    assert FIELDS <= canonical['properties'].keys()


def test_direct_builder_refuses_conflicting_precision_inputs():
    with pytest.raises(RecipeError, match='normal airborne'):
        StarterBuilder(Recipe(era='modern', start_altitude=4000)).build()


def test_browser_share_codec_preserves_advanced_recipe_fields():
    from test_recipe_contract import _browser_codec
    r = Recipe.from_dict({**BASE, **EXACT})
    decoded = _browser_codec('decode', encode_recipe(r))['result']
    assert all(decoded[k] == v for k,v in EXACT.items())
    assert decode_recipe(_browser_codec('encode', decoded)['result']).to_dict() == r.to_dict()


def test_discovery_and_canonical_schemas_are_valid_json_schema():
    import jsonschema
    jsonschema.Draft202012Validator.check_schema(recipe_json_schema())
    async def run():
        for tool in await mcp.list_tools():
            jsonschema.Draft202012Validator.check_schema(tool.input_schema)
            jsonschema.Draft202012Validator.check_schema(tool.output_schema)
    anyio.run(run)


def test_date_override_downgrades_reconstruction_without_promoting_fiction():
    from missiongen.precision import dated_setting
    r = Recipe(mission_date='1985-01-02')
    era = {'year':1985,'window':[1946,1990]}
    original = {'scenario_date':'1985-01-01', 'historical_classification':'reconstruction'}
    result = dated_setting(r, original, era)
    assert result['historical_classification'] == 'historically_inspired_adaptation'
    assert original['scenario_date'] == '1985-01-01'
    original['historical_classification'] = 'fictional_exercise'
    assert dated_setting(r, original, era)['historical_classification'] == 'fictional_exercise'
