"""Evidence and symbols must survive native serialization without inventing operations."""
from datetime import datetime
from pathlib import Path
import math
import zipfile

import pytest
from dcs import Mission, lua, mapping
from fastapi.testclient import TestClient
from pyproj import Geod

from missiongen import __version__, corridors
from missiongen import Recipe, generate
from scripts.audit_library import inspect_archive
from missiongen.resolver import load_json, resolve_terrain
from missiongen.historical_coverage import report, element, temporal_status
from missiongen.airspace import add_historical_airspace
from missiongen import historical_symbols as symbols
from server.app import app
from test_refactor_browser import site


def objects(native):
    return [o for layer in native['drawings']['layers'].values()
            for o in layer.get('objects',{}).values()]


def save_read(m,tmp_path):
    path=tmp_path/'reference.miz';m.save(str(path))
    with zipfile.ZipFile(path) as z:
        assert not any(n.endswith('.lua') and 'l10n' not in n for n in z.namelist())
        return lua.loads(z.read('mission').decode())['mission']


def test_register_covers_every_supported_pair_and_drawn_element():
    maps=load_json('maps');r=report();register=load_json('historical_coverage')
    assert {(c['map'],c['era']) for c in r['map_eras']}=={(k,e) for k,m in maps.items() for e in m['presets']}
    assert len(r['map_eras'])==26 and len(maps)==13
    assert all(not c['dated_validity_certified'] for c in r['map_eras'])
    assert all(c['research'] and c['reviewed_on']=='2026-10-03' for c in r['map_eras'])
    expected=set()
    for mk in corridors.MAPS:
        expected.update(f"network/{mk}/{c['id']}" for c in corridors.data(mk)['corridors'])
    for mk,rows in load_json('air_corridors').items():
        if mk.startswith('_'):continue
        expected.update(f"tactical/{mk}/{c['name']}" for c in rows)
    for mk,ovs in load_json('historical_airspace').items():
        if mk.startswith('_'):continue
        for oid,ov in ovs.items():expected.update(f'overlay/{mk}/{oid}/{i}' for i in range(len(ov['features'])))
    assert set(register['elements'])==expected
    for e in register['elements'].values():
        assert e['evidence'] in ('documented_structure','reported_track','training_design')
        assert e['geometry_accuracy'] and e['limitations'] and e['source_date_notes']
    for f in register['research_findings']:
        assert f['sources'] and f['remaining_gap'] and f['access']
        assert all(u.startswith('https://') for u in f['sources'])


def test_reference_date_never_certifies_operational_validity():
    entry=element('overlay/falklands/total_exclusion_1982/0')
    assert entry['valid_from'] is None and entry['valid_to'] is None
    assert temporal_status(entry,'1982-05-21')=='operational_validity_unknown'
    entry['valid_from']='1982-04-30';entry['valid_to']='1982-06-14'
    assert temporal_status(entry,'1982-04-29')=='outside_recorded_validity'
    assert temporal_status(entry,'1982-05-21')=='within_recorded_validity'
    assert element(entry['id'])['valid_from'] is None
    original=element('overlay/nevada/groom_box/0')
    assert temporal_status(original,'1978-06-21')=='outside_recorded_validity'
    assert temporal_status(original,'1996-01-01')=='operational_validity_unknown'


def test_future_snapshots_and_other_eras_are_not_drawn():
    terrain=resolve_terrain(load_json('maps')['iraq']['terrain_class'])();m=Mission(terrain)
    m.start_time=datetime(1991,1,17,12)
    assert add_historical_airspace(m,'iraq','modern') == ([],[])
    m.start_time=datetime(1994,6,21,12)
    assert add_historical_airspace(m,'iraq','modern')[0] == ['southern_watch_1992']
    assert add_historical_airspace(m,'iraq','coldwar') == ([],[])


def test_recovery_chart_arrow_follows_ordered_homeward_fixes(monkeypatch):
    from missiongen import corridor_chart as chart
    arrows=[]
    monkeypatch.setattr(chart,'_arrow',lambda cv,a,b,*args:arrows.append((a,b)))
    c=corridors.corridor('cy_home','syria')
    assert c['points'][-1]=='AKROTIRI' and c['role']=='recovery'
    projection=chart.Proj(corridors.data('syria')['chart']['bounds'],900,700)
    chart._draw_lanes(chart.Canvas(900,700),projection,c,'syria',chart.TRANSIT,None,1,set())
    home=corridors.fix('AKROTIRI','syria')
    assert arrows[-1][1]==projection(home['lat'],home['lon'])


def test_new_research_retains_source_precision_and_missing_geometry():
    r=load_json('historical_coverage');findings={f['id']:f for f in r['research_findings']}
    assert findings['falklands-tez']['geometry']=={'center':[-51-40/60,-59.5],'radius_nm':200}
    assert '59°39' in findings['falklands-tez']['remaining_gap']
    assert findings['neptune']['geometry']['gate']==pytest.approx([49+45/60+30/3600,-(2+56/60+30/3600)])
    assert element('overlay/iraq/southern_watch_1996/0')['reference_date']=='1996-09'
    for id in ['afghan-airways','sinai-disengagement','sinai-mfo','guam-warning','nato-2014','black-buck']:
        assert findings[id]['geometry'] is None
    assert 'UL333' in findings['afghan-airways']['claim'] and 'M881' in findings['afghan-airways']['claim']
    assert all(e['evidence']=='training_design' for e in r['elements'].values() if e['dataset']=='tactical')


@pytest.mark.parametrize('mk,era,day,ids',[
    ('falklands','coldwar','1982-05-21',['total_exclusion_1982']),
    ('normandy','wwii','1944-06-21',['neptune_ingress']),
    ('iraq','gwot','2003-06-21',['southern_watch_1992','southern_watch_1996'])])
def test_dated_references_survive_native_readback_without_tasks_or_zone_enforcement(mk,era,day,ids,tmp_path):
    terrain=resolve_terrain(load_json('maps')[mk]['terrain_class'])();m=Mission(terrain)
    m.start_time=datetime.fromisoformat(day+'T12:00:00')
    drawn,brief=add_historical_airspace(m,mk,era)
    assert drawn==ids
    assert 'not airspace active on the mission date' in '\n'.join(brief)
    native=save_read(m,tmp_path);objs=objects(native)
    assert sum(symbols.LEGEND[0] in o.get('text','') for o in objs)==1
    assert not native.get('trigrules') and not native.get('triggers',{}).get('zones')
    assert 'REF' in '\n'.join(o.get('text','') for o in objs)
    if mk=='falklands':
        polygon=next(o for o in objs if len(o.get('points',{}))==97)
        assert polygon['style']=='boundry1'
        # Native relative vertices project back to the published geodesic circle.
        distances=[];geod=Geod(ellps='WGS84')
        for p in list(polygon['points'].values())[:-1]:
            point=mapping.Point(polygon['mapX']+p['x'],polygon['mapY']+p['y'],terrain).latlng()
            distances.append(geod.inv(-59.5,-51-40/60,point.lng,point.lat)[2])
        assert distances==pytest.approx([200*1852]*96,abs=0.1)
    elif mk=='normandy':
        assert any(o.get('style')=='dash' and len(o.get('points',{}))==3 for o in objs)
        assert any(len(o.get('points',{}))==5 for o in objs) # diamond gate, no invented lane
        assert 'Reconstructed terminals; no route width' in '\n'.join(o.get('text','') for o in objs)
    else:
        assert 'REF 1996-09' in '\n'.join(o.get('text','') for o in objs)


def test_f10_network_lanes_gates_and_training_geometry_are_distinct(tmp_path):
    terrain=resolve_terrain(load_json('maps')['nevada']['terrain_class'])();m=Mission(terrain)
    corridors.draw(m,map_key='nevada');symbols.legend(m)
    native=save_read(m,tmp_path);objs=objects(native)
    lane_count=sum(max(0,len(c['points'])-1) for c in corridors.data('nevada')['corridors'])
    polygons=[o for o in objs if len(o.get('points',{}))==5]
    assert all(o['style']=='dash' and o['fillColorString'].endswith('00') for o in polygons[:lane_count])
    assert len(polygons)==lane_count+len(corridors.data('nevada')['gates'])
    assert any(o.get('style')=='solid' and len(o.get('points',{}))==5 for o in objs)
    assert sum(o.get('polygonMode')=='circle' for o in objs)==1 # single-fix FLEX turnout, never a gate
    assert sum(symbols.LEGEND[0] in o.get('text','') for o in objs)==1
    assert any('TRAINING' in o.get('text','') for o in objs)
    assert symbols.style('illustrative_zone')[3].value=='dot'
    assert symbols.style('deconfliction_line')[3].value=='dotdash'
    assert symbols.label_tag(element('overlay/iraq/southern_watch_1992/0')).startswith('~ DOC')


@pytest.mark.parametrize('mk,era,aircraft,phrase',[
    ('falklands','coldwar','F_5E_3','1982 TOTAL EXCLUSION ZONE'),
    ('normandy','wwii','P_51D','NEPTUNE / ALBANY INGRESS'),
    ('iraq','gwot','F_16C_50','SEPT 1996 SOUTHERN WATCH')])
def test_reference_toggle_reaches_real_mission_briefs_without_changing_flight(mk,era,aircraft,phrase,tmp_path):
    recipe=dict(map=mk,era=era,aircraft=aircraft,seed=781,
                bb_dressing=False,bb_ambient=False,bb_sams=False,
                bb_tanker=False,bb_awacs=False,bb_kneeboard=False)
    before=tmp_path/'off.miz';after=tmp_path/'on.miz'
    generate(Recipe(**recipe,bb_historical_airspace=False),str(before))
    result=generate(Recipe(**recipe,bb_historical_airspace=True),str(after))
    old,new=inspect_archive(before),inspect_archive(after)
    for key in ('groups','date','weather','zones','trigger_rules','trig'):
        assert old[key]==new[key],key
    assert phrase in '\n'.join(new['embedded_text'].values())
    assert result['stats']['historical_airspace']


def test_public_api_filters_and_rejects_unknown_or_unsupported_pairs():
    with TestClient(app) as c:
        r=c.get('/api/historical-coverage?map=kola&era=coldwar')
        assert r.status_code==200 and r.json()['app_version']==__version__
        assert len(r.json()['map_eras'])==1
        assert r.json()['map_eras'][0]['research'][0]['id']=='vardoe-1975'
        for query in ['map=invalid','era=invalid','map=normandy&era=modern']:
            assert c.get('/api/historical-coverage?'+query).status_code==400
        assert c.get('/api/historical-symbols.svg').status_code==200
        assert c.get('/api/historical-symbols.png').headers['content-type']=='image/png'
        assert c.get('/api/historical-symbols.exe').status_code==404
        assert 'Historical coverage register' in c.get('/llms.txt').text


@pytest.mark.parametrize('width',[1280,390,320])
def test_real_browser_coverage_filters_links_and_mobile_fit(site,width):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True);page=browser.new_page(viewport={'width':width,'height':900});errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(site+'/api/historical-coverage/report')
        assert page.locator('article:visible').count()==26
        page.select_option('#map','falklands');page.select_option('#era','coldwar')
        assert page.locator('article:visible').count()==1
        page.locator('article:visible summary').first.click()
        assert '200-nautical-mile' in page.locator('article:visible').inner_text()
        assert page.locator('article:visible a').first.get_attribute('href').startswith('https://hansard.parliament.uk/')
        page.select_option('#map','normandy')
        assert page.locator('#empty').is_visible()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert not errors
        browser.close()
