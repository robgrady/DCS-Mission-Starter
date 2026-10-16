"""Explicit authoring promises checked against saved native missions and SDK."""
import json
import zipfile

import anyio
import dcs.lua as lua
from fastapi.testclient import TestClient
from mcp import Client
import pytest

from missiongen import Recipe
from missiongen.builder import StarterBuilder
from missiongen.recipe import RecipeError
from missiongen.share import encode_recipe, decode_recipe
from server.app import app
from server.mcp_server import mcp
from test_precision_recipe import human_group

STORES = {'1': '{LAU-138 wtip - AIM-9M}', '2': '{SHOULDER AIM_54A_Mk47 L}',
          **{str(p): '{AIM_54A_Mk47}' for p in (4, 5, 6, 7)},
          '9': '{SHOULDER AIM_54A_Mk47 R}', '10': '{LAU-138 wtip - AIM-9M}'}
BASE = dict(map='syria', era='coldwar', aircraft='F_14B_U', start='air',
            mission_date='1971-11-15', start_position={'lat':33.6,'lon':31.6},
            start_altitude=12192, player_slot='player',
            map_view={'center':{'lat':33.6,'lon':31.6},'zoom':150000},
            start_speed=205.7777777778, start_time='09:17:23',
            player_stores=STORES, allow_anachronistic_stores=True,
            callsign='Dodge', comms={'flight_common':251.0}, seed=19711115,
            bb_dressing=False, bb_sams=False, bb_ambient=False,
            bb_awacs=False, bb_tanker=False, bb_kneeboard=False, bb_branding=False)


def build(data, path):
    b = StarterBuilder(Recipe.from_dict(data)); m = b.build(); m.save(str(path))
    with zipfile.ZipFile(path) as z:
        native = lua.loads(z.read('mission').decode())['mission']
    return b, native


@pytest.fixture(scope='module')
def exact(tmp_path_factory):
    directory=tmp_path_factory.mktemp('exact-authoring')
    b, n = build(BASE, directory/'one.miz')
    build(BASE, directory/'two.miz')
    assert (directory/'one.miz').read_bytes() == (directory/'two.miz').read_bytes()
    return b, n


def test_six_phoenix_two_sidewinders_exact_speed_and_clock_survive_native_save(exact):
    b, n = exact
    g = human_group(n); u = g['units'][1]; point = g['route']['points'][1]
    assert {str(p): v['CLSID'] for p, v in u['payload']['pylons'].items()} == STORES
    assert len(u['payload']['pylons']) == 8  # no preset Sparrows or tanks left over
    assert u['speed'] == pytest.approx(BASE['start_speed'])
    assert point['speed'] == pytest.approx(BASE['start_speed'])
    assert n['start_time'] == 9*3600+17*60+23
    assert n['date'] == {'Year':1971,'Month':11,'Day':15}
    assert u['alt'] == 12192 and u['skill'] == 'Player'
    assert n['map']['centerX'] == pytest.approx(u['x'])
    assert n['map']['centerY'] == pytest.approx(u['y'])
    assert n['map']['zoom'] == 150000
    assert u['Radio'][1]['channels'][1] == u['Radio'][2]['channels'][1] == 251
    assert b.context.historical.classification == 'fictional_exercise'
    assert any('fictional equipment' in note for note in b.context.historical.notes)
    assert len([w for w in b.warnings if w.startswith('Fictional equipment override:')]) == 8
    assert '09:17' in b._mission.description_text()


def test_explicit_clean_fit_does_not_fall_back_to_preset(tmp_path):
    _, n = build({**BASE,'player_stores':{},'allow_anachronistic_stores':False},tmp_path/'clean.miz')
    assert human_group(n)['units'][1]['payload']['pylons'] == {}


def test_explicit_fit_replaces_existing_stores_on_every_unit(tmp_path):
    from missiongen.authoring import apply_explicit
    b, _ = build({**BASE, 'slots':4, 'veteran_wingmen':3},tmp_path/'flight.miz')
    group=b.phases[1].player_group
    for unit in group.units:
        unit.pylons[3]={'CLSID':'{F14-300gal}'}
    apply_explicit(group,{'pylons':STORES})
    assert all({str(p):v['CLSID'] for p,v in unit.pylons.items()} == STORES for unit in group.units)
    apply_explicit(group,{'pylons':{}})
    assert all(unit.pylons=={} for unit in group.units)


@pytest.mark.parametrize('changes,part', [
    ({'allow_anachronistic_stores':False},'recorded service'),
    ({'player_stores':{'1':'invented'}},'not listed'),
    ({'player_stores':{'99':'{AIM_54A_Mk47}'}},'station'),
    ({'player_stores':{'01':'{AIM_54A_Mk47}'}},'station'),
    ({'player_stores':{'1':True}},'not listed'),
    ({'player_stores':{'1':'{SHOULDER AIM_54A_Mk47 L}'}},'not listed'),
    ({'player_stores':None},'requires an explicit'),
    ({'player_arm':False},'player_arm'),
    ({'player_fit':'guns'},'player_fit'),
    ({'template':'wk_1_stepstart'},'fixed training'),
    ({'start_speed':True},'start_speed'), ({'start_speed':float('nan')},'start_speed'),
    ({'start_speed':0},'start_speed'), ({'start_speed':1001},'start_speed'),
    ({'start':'cold'},'airborne'), ({'start_time':'24:00'},'start_time'),
    ({'start_time':'9:12'},'start_time'), ({'start_time':'01:20:99'},'start_time'),
    ({'start_time':'01:20+03:00'},'start_time'),
    ({'mission_date':None,'timing_anchor':'tot','timing_at':'12:30'},'start_time'),
])
def test_invalid_authoring_fails_in_validation_before_generation(changes, part):
    with pytest.raises(RecipeError,match=part):
        Recipe.from_dict({**BASE,**changes})


def test_exact_fields_survive_server_and_browser_share_roundtrips():
    from test_recipe_contract import _browser_codec
    r = Recipe.from_dict(BASE)
    code = encode_recipe(r)
    assert decode_recipe(code).to_dict() == r.to_dict()
    browser = _browser_codec('decode',code)['result']
    assert all(browser[k] == BASE[k] for k in ('start_speed','start_time','player_stores','allow_anachronistic_stores'))
    assert decode_recipe(_browser_codec('encode',browser)['result']).to_dict() == r.to_dict()


def test_sdk_discovers_and_validates_exact_fit_and_scoped_catalogs():
    async def run():
        async with Client(mcp) as c:
            for name in ('validate_recipe','generate_mission'):
                tool = next(t for t in (await c.list_tools()).tools if t.name.endswith(name))
                fields = tool.input_schema['properties']['params']['properties']['recipe']['properties']
                assert {'start_speed','start_time','player_stores','allow_anachronistic_stores'} <= fields.keys()
                assert 'metres/second' in fields['start_speed']['description']
            v = await c.call_tool('sortiestarter_validate_recipe',{'params':{'recipe':BASE}})
            assert not v.is_error, v.content
            assert v.structured_content['recipe']['player_stores'] == STORES
            generated = await c.call_tool('sortiestarter_generate_mission', {'params':{'recipe':BASE}})
            assert not generated.is_error, generated.content
            manifest = generated.structured_content['manifest']
            assert manifest['mission']['bytes'] > 0
            assert all(manifest['recipe'][key] == value for key,value in BASE.items())
            assert any(w.startswith('Fictional equipment override:') for w in manifest['warnings'])
            result = await c.call_tool('sortiestarter_list_catalog', {'params':{'kind':'stores','aircraft':'F_14B_U',
                'era':'coldwar','on':'1971-11-15','query':'AIM-54A','limit':2}})
            assert not result.is_error,result.content
            data=result.structured_content
            assert len(data['items']) == 2 and data['has_more'] and data['next_offset'] == 2
            assert all(row['historical_status'] == 'outside_recorded_window' for row in data['items'])
            row = data['items'][0]
            item = await c.call_tool('sortiestarter_get_catalog_item', {'params':{'kind':'stores','aircraft':'F_14B_U',
                'era':'coldwar','on':'1971-11-15','key':row['key']}})
            assert not item.is_error and item.structured_content['item'] == row
            bad = await c.call_tool('sortiestarter_list_catalog', {'params':{'kind':'stores'}})
            assert bad.is_error
            bad = await c.call_tool('sortiestarter_validate_recipe',{'params':{'recipe':{**BASE,'allow_anachronistic_stores':False}}})
            assert bad.is_error and 'recorded service' in bad.content[0].text
    anyio.run(run)


def test_http_catalogs_bound_results_and_do_not_invent_liveries():
    with TestClient(app) as c:
        response = c.get('/api/authoring-catalog',params={'kind':'stores','aircraft':'F_14B_U','limit':1})
        assert response.status_code == 200 and len(response.json()['items']) == 1
        loadouts = c.get('/api/authoring-catalog',params={'kind':'loadouts','aircraft':'F_14B_U','era':'coldwar','on':'1971-11-15'}).json()
        assert loadouts['items'] and all(row['year']==1971 for row in loadouts['items'])
        liveries = c.get('/api/authoring-catalog',params={'kind':'liveries','aircraft':'F_14B_U'}).json()
        assert liveries['items'] == [] and 'partial' in liveries['limitations']
        liveries = c.get('/api/authoring-catalog',params={'kind':'liveries','aircraft':'F_4E_45MC','era':'coldwar'}).json()
        assert liveries['items'][0]['livery_id'] == '421st_TFS_SEA_68-336'
        assert not liveries['items'][0]['historical_identity_verified']
        for params in ({'kind':'stores','aircraft':'fake'}, {'kind':'loadouts','aircraft':'F_14B_U'},
                       {'kind':'stores','aircraft':'F_14B_U','on':'20260101'}):
            assert c.get('/api/authoring-catalog',params=params).status_code == 400
        assert c.get('/api/authoring-catalog',params={'kind':'stores','aircraft':'F_14B_U','limit':51}).status_code == 422
