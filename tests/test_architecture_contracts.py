"""Public boundaries retain their contracts after phase/module extraction."""
from dataclasses import fields
import json
import re

import pytest

from fastapi.testclient import TestClient

from missiongen import Recipe, generate
from missiongen.artifacts import generate as package_generate
from missiongen.build_context import EraViolation, prepare_world
from missiongen.builder import StarterBuilder
from missiongen.recipe import RECIPE_ENUMS
from server.app import app
from server.recipe_contract import recipe_json_schema
from test_mission_kit_wiring import ROOT, run_js


def test_openapi_and_public_recipe_schema_follow_the_dataclass():
    schema = recipe_json_schema()
    assert set(schema['properties']) == {f.name for f in fields(Recipe)}
    assert schema['properties']['slots']['type'] == 'integer'
    assert schema['properties']['bb_tanker']['type'] == 'boolean'
    for key, allowed in RECIPE_ENUMS.items():
        assert set(schema['properties'][key]['enum']) == set(allowed)
    with TestClient(app) as client:
        assert client.get('/api/recipe-schema').json() == schema
        doc = client.get('/openapi.json').json()
        request = doc['components']['schemas']['GenerateRequest']['properties']['recipe']
        assert request['properties'] == {name: {key: value for key, value in prop.items() if value is not None}
                                         for name, prop in schema['properties'].items()}
        asset = client.get('/assets/mission-results.js')
        assert asset.status_code == 200 and 'function generateMission' in asset.text


def test_public_generate_still_uses_the_packaging_phase():
    assert generate is package_generate
    from missiongen.builder import generate as old_import
    assert old_import is generate


def test_world_context_resolves_coalitions_and_carries_the_same_stats():
    rc = Recipe.from_dict({'map': 'thechannel', 'era': 'wwii',
                           'aircraft': 'SpitfireLFMkIX', 'bb_ambient': False,
                           'bb_dressing': False, 'bb_kneeboard': False})
    builder = StarterBuilder(rc)
    mission = builder.build()
    ctx = builder.context
    assert ctx.mission is mission and ctx.stats is builder.stats
    assert ctx.own_fields and ctx.enemy_fields
    assert ctx.red_country.name == 'Germany'
    assert 'Germany' in mission.coalition['red'].countries
    assert 'Germany' not in mission.coalition['blue'].countries
    assert ctx.country('Germany', 'red') is ctx.red_country


def test_changing_kind_detaches_a_template_before_applying_new_choices():
    out = run_js("""
let S={template:'rio_fleet_defense',engineSettings:{coach_gates:true}};
let appliedTemplate=null;
const document={querySelector:()=>null,getElementById:()=>null};
const kindDef=()=>({patch:{}}), renderKinds=()=>{},updateRail=()=>{},buildReview=()=>{},sum=()=>{appliedTemplate=S.template;};
pickKind('training');console.log(JSON.stringify({template:S.template,engine:S.engineSettings,kind:S.kind,appliedTemplate}));
""", ['pickKind'])
    assert out == {'template': None, 'engine': {}, 'kind': 'training', 'appliedTemplate': None}


@pytest.mark.parametrize('deck', [[], ['Tomcat']])
@pytest.mark.parametrize('template', [None, 'carrier_qualification'])
def test_reopening_carrier_recipe_restores_hull_deck_support_and_aircraft(deck, template):
    out = run_js("""
const sel=()=>{};
let S={}, RECIPE_ENGINE_FIELDS=[], BLOCKS=[['bb_carrier']], events=[];
const nodes={bb_carrier:{checked:false},
 carrier_cap:{checked:false},
 carrier_hull:{value:'',options:[]},
 carrier_layout:{value:'underway',options:[{value:'underway'},{value:'launch'}]},
 aircraft:{value:'Hornet',options:[{value:'Hornet'}]}};
let deck=[];
const document={getElementById:id=>nodes[id]||(nodes[id]={style:{}}),
 querySelector:sel=>sel.startsWith('#templates')&&TEMPLATE?{click:()=>{
   nodes.carrier_hull.value='Nimitz';nodes.carrier_layout.value='underway';nodes.carrier_cap.checked=false;
 }}:null,querySelectorAll:sel=>sel==='.deckac'?deck:[]};
const fillHome=()=>{},refreshCallsign=()=>{},setFlightMode=()=>{},refreshPatternUI=()=>{},
 setTimingUI=()=>{},refreshDressUI=()=>{},syncPlayerArm=()=>{},renderCorridors=()=>{},
 setCommOverrides=()=>{},refreshWingmen=()=>{};
function refreshCarrierUI(){
 events.push(nodes.bb_carrier.checked);
 if(nodes.bb_carrier.checked){nodes.carrier_hull.options=[{value:'Nimitz'},{value:'Forrestal'}];nodes.carrier_hull.value='Nimitz';}
}
function refreshDeckAircraft(){deck=['Tomcat','Intruder'].map(value=>({value,checked:true}));}
function refreshAircraft(){nodes.aircraft.options=[{value:'Hornet'},{value:'Tomcat'}];nodes.aircraft.value='Hornet';}
applyRecipe({era:'coldwar',map:'germany',aircraft:'Tomcat',home_airbase:'CARRIER',
 template:TEMPLATE,
 bb_carrier:true,carrier_hull:'Forrestal',carrier_layout:'launch',
 carrier_deck_aircraft:DECK,carrier_equipment:false,carrier_cap:true,carrier_aew:true,carrier_strike:true});
console.log(JSON.stringify({events,hull:nodes.carrier_hull.value,layout:nodes.carrier_layout.value,
 aircraft:nodes.aircraft.value,deck:deck.filter(c=>c.checked).map(c=>c.value),
 equipment:nodes.carrier_equipment.checked,cap:nodes.carrier_cap.checked,
 aew:nodes.carrier_aew.checked,strike:nodes.carrier_strike.checked}));
""".replace('DECK', json.dumps(deck)).replace('TEMPLATE', json.dumps(template)), ['applyRecipe', 'restoreCarrierRecipe'])
    assert out == {'events': [True], 'hull': 'Forrestal', 'layout': 'launch',
                   'aircraft': 'Tomcat', 'deck': deck, 'equipment': False,
                   'cap': True, 'aew': True, 'strike': True}


def test_navigation_carries_views_and_builder_steps_without_duplicate_entries():
    out = run_js("""
let NAV_READY=true; let entries=[];
const location={href:'https://example.test/?v=quick'};
const history={pushState:(state,unused,url)=>{entries.push({state,url:String(url)});location.href=String(url);},replaceState:()=>{}};
writeNavigation('builder','flight');writeNavigation('builder','flight');writeNavigation('pipeline','flight');
console.log(JSON.stringify({entries,train:normalizeView('train'),invalid:normalizeView('unknown')}));
""", ['normalizeView', 'writeNavigation'])
    assert len(out['entries']) == 2
    assert out['entries'][0]['url'].endswith('?v=builder&step=flight')
    assert out['entries'][1]['url'].endswith('?v=pipeline')
    assert out['train'] == 'pipeline' and out['invalid'] == 'entry'


def test_carrier_control_changes_update_the_saved_recipe():
    out = run_js("""
let listeners={}, saved=[];
const document={getElementById:id=>({addEventListener:(event,fn)=>{listeners[id]=fn;}})};
let current;
const sum=()=>saved.push(current);
bindCarrierRecipeChanges();
for(const id of Object.keys(listeners)){current=id;listeners[id]();}
console.log(JSON.stringify(saved));
""", ['bindCarrierRecipeChanges'])
    assert out == ['carrier_layout', 'carrier_equipment', 'carrier_cap',
                   'carrier_aew', 'carrier_strike', 'deck_aircraft']


@pytest.mark.parametrize('failure', ['network', 'http', 'json'])
def test_options_failure_shows_retry_and_does_not_initialize_partial_ui(failure):
    out = run_js("""
const banner={hidden:true}, retry={disabled:false};
const document={getElementById:id=>id==='loaderror'?banner:retry};
let OPT=null, attempts=0, partial=0;
const initGfxUI=()=>partial++, initCommUI=()=>partial++;
const fetch=async()=>{attempts++;
  if(FAILURE==='network') throw new Error('offline');
  return {ok:FAILURE!=='http',json:async()=>{throw new Error('invalid JSON');}};
};
(async()=>{await init(); await init();
  console.log(JSON.stringify({attempts,partial,options:OPT,visible:!banner.hidden,canRetry:!retry.disabled}));
})();
""".replace('FAILURE', json.dumps(failure)), ['init'])
    assert out == {'attempts': 2, 'partial': 0, 'options': None,
                   'visible': True, 'canRetry': True}
