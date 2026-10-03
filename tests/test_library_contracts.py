"""Assert the actors, stores and submitted presets behind the audited promises."""
import json
import pytest
from fastapi.testclient import TestClient
from missiongen import Recipe, generate, loadouts
from missiongen.templates import effective_recipe, templates
from scripts.audit_library import inspect_archive
from server.app import app
from test_mission_kit_wiring import run_js

AFFECTED = ('sead_range f14_bombcat_strike af_tic_cas af_convoy_overwatch '
            'f100_victor_alert f100_fulda_cas f100_iron_hand bc_ti1 '
            'wk_9_intercepts wk_10_threeship f100_sabre_dance_bfm '
            'cv_alpha_strike_escort carrier_qual f14_tarps_recon '
            'bc_lasdt1 wk_11_bfm bc_sat2').split()


def player_groups(m):
    return [g for g in m['groups'] if any(u['skill'] in ('Player', 'Client') for u in g['units'])]


def stores(group):
    return [p['CLSID'] for u in group['units']
            for p in (u.get('payload', {}).get('pylons') or {}).values()]


def tasks(point):
    return list((point.get('task', {}).get('params', {}).get('tasks') or {}).values())


@pytest.fixture(scope='module', params=AFFECTED)
def built(request, tmp_path_factory):
    key = request.param
    tmp = tmp_path_factory.mktemp(key)
    # Real native actors/tasks/stores with irrelevant ramp artwork disabled.
    rc = Recipe.from_dict({'template': key, 'seed': 7, 'bb_dressing': False,
                           'bb_briefing': False, 'bb_kneeboard': False,
                           'bb_branding': False})
    path = tmp / 'mission.miz'
    result = generate(rc, str(path))
    return key, rc, inspect_archive(path), result


def test_every_affected_entry_has_its_emitted_contract(built):
    key, rc, m, result = built
    players = player_groups(m)
    assert players
    payload = stores(players[0])
    cls = [loadouts.store_class(c) for c in payload]
    if key == 'sead_range':
        assert 'arm' in cls
    if key in ('f14_bombcat_strike', 'af_tic_cas', 'af_convoy_overwatch'):
        assert 'lgb' in cls or 'jdam' in cls
        assert 'pod' in cls
    if key in ('f100_victor_alert', 'f100_fulda_cas', 'f100_iron_hand', 'bc_sat2'):
        assert 'bomb' in cls and not any(c in cls for c in ('lgb', 'jdam', 'arm'))
    by_name = {g['name']: g for g in m['groups']}
    if key in ('bc_ti1', 'wk_9_intercepts', 'wk_10_threeship'):
        target = by_name['TRAINING Radar target']
        assert len(target['units']) == 1 and len(target['route']) == 2
        assert not stores(target)
        assert any(t['id'] == 'WrappedAction' and t['params']['action']['params'].get('value') == 4
                   for t in tasks(target['route'][0]))
        if key == 'wk_10_threeship':
            assert len(players[0]['units']) == 2
            assert [u['skill'] for u in players[0]['units']] == ['Player', 'Excellent']
    if key == 'af_convoy_overwatch':
        convoy = by_name['SCENARIO Friendly convoy']
        assert convoy['side'] == 'blue' and len(convoy['units']) == 4
        assert len(convoy['route']) == 2 and convoy['route'][1]['speed'] > 0
        assert by_name['SCENARIO Ambush']['late']
        assert any(t['comment'] == 'Convoy approaches ambush' for t in m['trigger_rules'])
    if key == 'af_tic_cas':
        assert by_name['SCENARIO Patrol in contact']['side'] == 'blue'
        jtac = by_name['SCENARIO JTAC Pointer']
        fac = next(t for t in tasks(jtac['route'][0]) if t['id'] == 'FAC_EngageGroup')
        assert fac['params']['frequency'] == 30000000 and fac['params']['modulation'] == 1
        assert fac['params']['groupId'] > 0
    if key == 'f100_fulda_cas':
        armor = by_name['SCENARIO Advancing armor']
        assert len(armor['units']) == 4 and len(armor['route']) == 2
        assert armor['route'][1]['speed'] > 0
    if key == 'f100_sabre_dance_bfm':
        bandit = by_name['Bandit BFM']
        assert not payload and not stores(bandit)
    if key == 'cv_alpha_strike_escort':
        strike = next(g for g in m['groups'] if g['name'].startswith('STRIKE '))
        assert 'bomb' in [loadouts.store_class(c) for c in stores(strike)]
        assert any(t['id'] == 'AttackGroup' for p in strike['route'] for t in tasks(p))
        assert strike['route'][-1]['action'] == 'Landing'
        assert strike['route'][-1]['linkUnit'] == strike['route'][-1]['helipadId']
    if key == 'carrier_qual':
        assert not payload and rc.home_airbase == 'CARRIER'
    if key == 'f14_tarps_recon':
        assert payload == ['{F14-TARPS}'] * len(players[0]['units'])
        assert {str(k): v['CLSID'] for k, v in players[0]['units'][0]['payload']['pylons'].items()} == {'6': '{F14-TARPS}'}
    if key in ('bc_lasdt1', 'wk_11_bfm', 'bc_sat2'):
        card = templates()[key]['library']
        assert card['disclosure'] in card['premise']
        assert card['disclosure'] in result['stats']['scenario_facts']


@pytest.mark.parametrize('key', AFFECTED)
def test_api_and_browser_resolve_every_advertised_preset_equally(key):
    with TestClient(app) as client:
        opt = client.get('/api/options').json()
    t = templates()[key]
    for era in t['eras']:
        for map_key in t.get('maps') or [effective_recipe(key, era)['map']]:
            data = run_js('const OPT=' + json.dumps(opt) + ';'
                          + 'console.log(JSON.stringify(presetRecipe(' + json.dumps(key)
                          + ',' + json.dumps(era) + ',' + json.dumps(map_key) + ')));', ['presetRecipe'])
            expected = effective_recipe(key, era, map_key)
            assert data == expected
            assert Recipe.from_dict({'template': key, 'era': era, 'map': map_key}).to_dict() == Recipe.from_dict({**expected, 'template': key}).to_dict()


def test_preset_reset_cannot_inherit_old_stores_slots_or_comms():
    with TestClient(app) as client:
        opt = client.get('/api/options').json()
    got = run_js('const OPT=' + json.dumps(opt) + ';'
        + "let S={era:'modern',map:'nevada',kind:'cas'};let applied;"
        + "const applyRecipe=r=>applied=r,renderKinds=()=>{},sum=()=>{},updateRail=()=>{};"
        + "applyScenarioPreset('bc_ti1');console.log(JSON.stringify(applied));",
        ['presetRecipe', 'applyScenarioPreset'])
    assert got['slots'] == 1 and got['mission_kind'] == 'a2a'
    assert got['player_fit'] == 'auto' and got['comms'] is None
    assert got['bb_targets'] is False


def test_explicit_api_edits_still_win_over_era_and_map_defaults():
    r = Recipe.from_dict({'template': 'wk_10_threeship', 'era': 'coldwar',
                          'map': 'sinai', 'slots': 3, 'home_airbase': 'Cairo West'})
    assert r.lineup == 'proud_phantom' and r.slots == 3 and r.home_airbase == 'Cairo West'


def test_lineup_airbases_are_used_by_the_actual_home_dropdown():
    with TestClient(app) as client:
        opt = client.get('/api/options').json()
    got = run_js('const OPT=' + json.dumps(opt) + ''';
const S={map:'sinai',era:'coldwar',engineSettings:{lineup:'proud_phantom'}};
const home={value:'',options:[],set innerHTML(v){this.options=[]},appendChild(o){this.options.push(o)}};
const document={getElementById:id=>id==='home'?home:{value:'blue'}};
const eraHull=()=>null,onHomeChange=()=>{},el=html=>({value:html.match(/value="([^"]*)"/)[1]});
fillHome();console.log(JSON.stringify(home.options.map(o=>o.value)));
''', ['selectedMapPreset', 'fillHome'])
    assert 'Beni Suef' in got and 'Cairo West' in got
    assert got == opt['maps']['sinai']['lineups']['proud_phantom']['blue_airbases']
