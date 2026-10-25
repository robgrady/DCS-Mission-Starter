"""Read authored points back from native archives and the complete kit."""
import copy
import json
import zipfile

import anyio
import dcs.lua as lua
from fastapi.testclient import TestClient
from mcp import Client
import pytest

from missiongen import Recipe
from missiongen.recipe import RecipeError
from missiongen.share import encode_recipe, decode_recipe
from missiongen.authored_route import brief_lines
from server.app import app
from server.mcp_server import mcp
from server.mission_kit import build_kit
from test_precision_recipe import human_group, values, save

BASE = dict(map='caucasus', era='modern', aircraft='F_14B_U', start='air',
    start_position={'lat':42.1,'lon':42.1}, start_altitude=5000, start_time='09:17:23',
    bb_sams=False, bb_dressing=False, bb_ambient=False, bb_tanker=False, bb_awacs=False,
    bb_targets=False, bb_range=False, bb_branding=False, bb_navpoints=False, seed=321)
POINTS = [dict(id='join',name='JOIN',position={'lat':42.2,'lon':42.3},altitude=4100.25,speed=205.7777777778,purpose='rendezvous'),
          dict(id='exit',name='EXIT',position={'x':-240000,'y':660000},altitude=3200.5,speed=180.125,purpose='egress')]


@pytest.fixture(scope='module')
def kit(tmp_path_factory):
    directory=tmp_path_factory.mktemp('authored-kit')
    r=Recipe.from_dict({**BASE,'waypoints':copy.deepcopy(POINTS),'route_recovery':'home'})
    result=build_kit(r,directory)
    with zipfile.ZipFile(result['miz']) as archive:
        native=lua.loads(archive.read('mission').decode())['mission']
        cartridge=json.loads(archive.read('DTC/F-14B(U) DTC_1.dtc'))
    with zipfile.ZipFile(result['bundle']) as archive:
        navigation=json.loads(archive.read('navigation.json'))
        markdown=archive.read('brief.md').decode()
        assert archive.read('mission.miz')==result['miz'].read_bytes()
    return r,result,native,cartridge,navigation,markdown


def test_authored_native_order_units_recovery_and_kit(kit):
    r,result,native,cartridge,nav,markdown=kit
    group=human_group(native); points=list(values(group['route']['points']))
    assert [p.get('name') for p in points[1:]]==['JOIN','EXIT','RECOVERY']
    assert points[1]['alt']==4100.25 and points[1]['alt_type']=='BARO'
    assert points[1]['speed']==pytest.approx(205.7777777778)
    assert points[2]['speed']==pytest.approx(180.125)
    assert (points[2]['x'],points[2]['y'])==(-240000,660000)
    assert points[3]['type']=='Land' and points[3]['airdromeId']
    assert all(not p.get('ETA_locked') for p in points[1:])
    assert native['start_time']==33443
    assert nav['authored_waypoints']==POINTS
    assert nav['route_mode']=='authored' and nav['route_recovery']=='home'
    assert [p['id'] for p in nav['route']]==['join','exit','recovery']
    for row,p in zip(nav['route'],points[1:]):
        assert row['speed_mps']==pytest.approx(p['speed'])
        assert row['altitude_m']==p['alt'] and row['eta_s']==p['ETA']
        assert row['point']['x']==pytest.approx(p['x'])
        assert row['point']['y']==pytest.approx(p['y'])
    assert [p['name'] for p in cartridge['data']['NAV'][0]['waypoints']]==['JOIN','EXIT','RECOVERY']
    assert 'AUTHORED FLIGHT PLAN' in markdown and '4100.25 m MSL' in markdown
    assert '180.125 m/s TAS' in markdown and 'RECOVERY' in markdown
    assert 'NO\nobjectives, tasking or waypoints' not in str(native)
    assert result['manifest']['kit']['kneeboard_pages']>=4
    assert decode_recipe(encode_recipe(r)).to_dict()==r.to_dict()


def test_authored_route_is_deterministic_and_does_not_append_automatic_points(tmp_path):
    r=Recipe.from_dict({**BASE,'template':'qf_guns','waypoints':copy.deepcopy(POINTS), 'bb_kneeboard':False})
    _,_,a=save(r,tmp_path/'a.miz');save(r,tmp_path/'b.miz')
    pts=list(values(human_group(a)['route']['points']))
    assert [p.get('name') for p in pts[1:]]==['JOIN','EXIT']
    assert (tmp_path/'a.miz').read_bytes()==(tmp_path/'b.miz').read_bytes()


def test_ground_route_preserves_takeoff_and_named_airfield_recovery(tmp_path):
    args={k:v for k,v in BASE.items() if k not in ('start_position','start_altitude')}
    r=Recipe.from_dict({**args,'start':'warm','waypoints':copy.deepcopy(POINTS),'route_recovery':'Kobuleti'})
    _,_,native=save(r,tmp_path/'ground.miz')
    pts=list(values(human_group(native)['route']['points']))
    assert pts[0]['type'].startswith('TakeOff')
    assert [p.get('name') for p in pts if p.get('name') in ('JOIN','EXIT','RECOVERY')]==['JOIN','EXIT','RECOVERY']
    from dcs.terrain import Caucasus
    assert pts[-1]['airdromeId']==next(a.id for a in Caucasus().airport_list() if a.name=='Kobuleti')


@pytest.mark.parametrize('patch',[
    {'waypoints':[]},{'waypoints':POINTS*17},{'waypoints':[{}]},
    {'route_recovery':'Imaginary Field'}, {'bb_route':True},
    {'formation':'route'}, {'template':'wk_1_stepstart'},
    {'timing_anchor':'tot'}, {'timing_coach':True},{'timing_package':True},{'timing_hold_min':2},
])
def test_invalid_authored_routes_fail_before_build(patch):
    with pytest.raises(RecipeError):Recipe.from_dict({**BASE,'waypoints':copy.deepcopy(POINTS),**patch})


@pytest.mark.parametrize('change',[
    {'id':'bad id'},{'id':'recovery'},{'id':True},{'id':'x'*41},{'name':'RECOVERY'}, {'name':' JOIN'},
    {'name':'line\nbreak'},{'name':'x'*25}, {'position':{'lat':0,'lon':0}},
    {'position':{'x':True,'y':5}}, {'altitude':float('nan')},{'altitude':0},{'altitude':True},
    {'altitude':25001}, {'speed':0},{'speed':True},{'speed':1001},
    {'purpose':'attack'},{'task':'execute lua'},{'altitude_reference':'AGL'},
])
def test_invalid_waypoint_fields_are_rejected(change):
    points=copy.deepcopy(POINTS);points[0].update(change)
    with pytest.raises(RecipeError):Recipe.from_dict({**BASE,'waypoints':points})


def test_duplicate_ids_and_names_and_recovery_without_route_are_rejected():
    for key in ('name','id'):
        points=copy.deepcopy(POINTS);points[1][key]=points[0][key]
        with pytest.raises(RecipeError):Recipe.from_dict({**BASE,'waypoints':points})
    with pytest.raises(RecipeError):Recipe.from_dict({**BASE,'route_recovery':'home'})


def test_route_preview_projects_without_startup_or_generation():
    with TestClient(app) as client:
        response=client.post('/api/route-preview',json={'map':'caucasus','positions':[POINTS[0]['position']]})
        assert response.status_code==200,response.text
        data=response.json();p=data['points'][0]
        assert p['lat']==pytest.approx(42.2) and p['lon']==pytest.approx(42.3)
        assert 'x_min' in data['bounds'] and data['airfields']
        assert client.post('/api/route-preview',json={'map':'caucasus','positions':[{'lat':0,'lon':0}]}).status_code==400
        assert client.post('/api/route-preview',json={'map':'invented'}).status_code==400
        assert client.post('/api/route-preview',json={'map':'caucasus','positions':[{}]*33}).status_code==422


def test_mcp_canonical_schema_and_validation_accept_authored_route():
    async def run():
        async with Client(mcp) as client:
            schema=await client.call_tool('sortiestarter_get_recipe_schema')
            item=schema.structured_content['properties']['waypoints']['anyOf'][0]['items']
            assert {'id','name','position','altitude','speed'}<=set(item['required'])
            good=await client.call_tool('sortiestarter_validate_recipe',{'params':{'recipe':{**BASE,'waypoints':POINTS}}})
            assert not good.is_error,good.content
            bad=await client.call_tool('sortiestarter_validate_recipe',{'params':{'recipe':{**BASE,'waypoints':[{}]}}})
            assert bad.is_error
    anyio.run(run)


def test_long_authored_route_documents_paginate_without_losing_last_point():
    from dcs.terrain import Caucasus
    from missiongen.precision import point
    from missiongen.kneeboard import pages_text
    terrain=Caucasus()
    rows=[dict(to=f'LONG NAME {i:02d}',purpose='transit',point=point({'lat':42.2,'lon':42.3},terrain,'p','caucasus'),
        altitude_m=4000,speed_mps=200,heading=90,nm=10,eta='09:30:00') for i in range(32)]
    lines=brief_lines(rows)
    assert any('LONG NAME 31' in line for line in lines)
    assert len(pages_text('AUTHORED FLIGHT PLAN','Caucasus',lines))>2


def test_carrier_home_recovery_keeps_native_ship_link(tmp_path):
    args={k:v for k,v in BASE.items() if k not in ('start_position','start_altitude')}
    r=Recipe.from_dict({**args,'map':'iraq','home_airbase':'CARRIER','bb_carrier':True,
        'waypoints':[dict(id='sea',name='SEA',position={'lat':28.9,'lon':49.7},altitude=4000,speed=200)],'route_recovery':'home'})
    _,_,n=save(r,tmp_path/'carrier.miz')
    final=list(values(human_group(n)['route']['points']))[-1]
    assert final['type']=='Land' and final['linkUnit']==final['helipadId']
    assert 'airdromeId' not in final


def test_all_32_points_reach_native_and_paginated_kneeboard(tmp_path,monkeypatch):
    from PIL import ImageDraw
    from missiongen import generate
    drawn=[]; original=ImageDraw.ImageDraw.text
    def record(self,xy,text,*args,**kwargs):
        drawn.append(str(text));return original(self,xy,text,*args,**kwargs)
    monkeypatch.setattr(ImageDraw.ImageDraw,'text',record)
    pts=[{**POINTS[0],'id':f'point{i}','name':f'POINT {i:02d}'} for i in range(32)]
    r=Recipe.from_dict({**BASE,'waypoints':pts})
    path=tmp_path/'long.miz';result=generate(r,str(path))
    with zipfile.ZipFile(path) as archive:
        n=lua.loads(archive.read('mission').decode())['mission']
        assert len(list(values(human_group(n)['route']['points'])))==33
        assert len([name for name in archive.namelist() if name.startswith('KNEEBOARD/IMAGES/')])>5
    assert any('POINT 31' in text for text in drawn)


def test_long_route_summary_keeps_http_kit_header_bounded():
    from server.mission_manifest import kit_manifest
    stats={'route':' > '.join(['😀'*24]*32),'route_mode':'authored',
           'authored_waypoints':[{}]*32}
    kit=kit_manifest(stats)
    assert len(json.dumps(kit))<1800
    assert kit['route']=='Authored route: 32 waypoints'


def test_author_defined_routes_do_not_claim_historical_reconstruction():
    from missiongen.precision import dated_setting
    r=Recipe.from_dict({**BASE,'waypoints':POINTS})
    for classification in ('reconstruction','fictional_exercise'):
        preset=dated_setting(r,{'historical_classification':classification},{})
        assert preset['historical_classification']==('historically_inspired_adaptation' if classification=='reconstruction' else classification)
        assert any('not historically source-verified' in n for n in preset['historical_notes'])
