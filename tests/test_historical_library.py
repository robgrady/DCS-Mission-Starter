"""Evidence boundaries, exact assignments and the assembled public reference shelf."""
from copy import deepcopy
import json
from pathlib import Path
import random
import zipfile
import xml.etree.ElementTree as ET

from fastapi.testclient import TestClient
import pytest
from missiongen import Recipe, generate, __version__
from missiongen.historical_library import catalog, profile, unit_history, validate, livery_matches, mission_references
from missiongen.historical_reference_chart import render_svg
from missiongen import dressing
from missiongen.resolver import load_json
from server.app import app
from test_refactor_browser import site


def test_edition_provenance_and_unknown_validity():
    data = catalog()
    assert len(data['entries']) == 18 and len(data['unit_records']) == 15
    assert len(data['profiles']['nevada-1981']['points']) == 32
    assert len(data['profiles']['nevada-2014']['points']) == 6
    assert all(not p['routing_enabled'] for p in data['profiles'].values())
    assert all(not r['valid_from'] and not r['valid_to'] for r in data['entries']+data['unit_records'])
    assert all(p['recipe_era'] is None for p in data['periods'].values())
    assert ('/'+'Volumes'+'/') not in json.dumps(data) and ('/'+'Users'+'/') not in json.dumps(data)
    assert validate(load_json('historical_library'))
    for mutation in ('page','path','validity','routing','coordinate'):
        bad=deepcopy(load_json('historical_library'))
        if mutation=='page':bad['entries'][0]['sources'][0]['pdf_pages']=[99999]
        if mutation=='path':bad['sources'][next(iter(bad['sources']))]['path']='/private/source.pdf'
        if mutation=='validity':bad['entries'][0]['valid_from']='1981-02-01'
        if mutation=='routing':bad['profiles']['nevada-1981']['routing_enabled']=True
        if mutation=='coordinate':bad['profiles']['nevada-1981']['points'][0]['latitude_decimal_degrees']+=.1
        with pytest.raises(ValueError):validate(bad)


def test_coordinates_stay_separate_and_returned_data_cannot_poison_cache():
    old=profile('nevada-1981'); new=profile('nevada-2014')
    flex=next(p for p in old['points'] if p['name']=='Flex')
    assert flex['coordinate_raw']=={'north_lat':'36-19.0','west_lon':'115-05.0'}
    assert flex['latitude_decimal_degrees']==pytest.approx(36+19/60)
    assert flex['longitude_decimal_degrees']==pytest.approx(-115-5/60)
    assert old['reference_date']!=new['reference_date']
    old['points'].clear()
    assert len(profile('nevada-1981')['points'])==32
    for edition in ('nevada-1981','nevada-2014'):
        svg=ET.fromstring(render_svg(edition));ns={'s':'http://www.w3.org/2000/svg'}
        markers=svg.findall(".//s:g[@class='reference-point']",ns)
        assert len(markers)==len(profile(edition)['points'])
        assert all(m.attrib['tabindex']=='0' and m.attrib['role']=='button' for m in markers)
        assert 'No route or boundary inferred' in render_svg(edition)
    assert 0 < render_svg('nevada-1981','local').count('class="reference-point"') < 32
    with pytest.raises(ValueError):render_svg('nevada-2014','local')


def test_unit_event_precision_never_becomes_continuous_occupancy():
    rows=unit_history(map_key='normandy',on='1944-07-07')['records']
    circa=next(r for r in rows if r['date_precision']=='circa')
    assert 'exact arrival unknown' in circa['date_relation']
    assert not any(r['occupancy_certified'] for r in rows)
    records=unit_history(map_key='germany',variant='F-15C',on='1977-01-01')['records']
    assert all(r['variant_status']=='variant_not_recorded' for r in records)
    assert any('F-15A' in r['aircraft_variants'] for r in records)
    for day in ('20261004','2026-W40-7','2026-02-30'):
        with pytest.raises(ValueError):catalog(on=day)


def dated_skin():
    return dict(livery_id='test-installed-id',dcs_type='F-4E-45MC',country='USA',base='Exact Base',
        unit='Verified Unit',variant='F-4E',valid_from='1980-01-01',valid_to='1980-12-31',
        sources=['verified edition, page 1'],installed_id_verified=True,date_precision='day',
        station_verified=True,variant_verified=True)


def test_exact_livery_assignment_and_actual_static_selector(monkeypatch):
    candidate=dated_skin();args=('F-4E-45MC','USA','Exact Base','1980-06-01')
    assert livery_matches(candidate,*args)
    for field in ('unit','sources','installed_id_verified','station_verified','variant_verified','valid_to'):
        bad=deepcopy(candidate);bad[field]=None
        assert not livery_matches(bad,*args)
    for mismatch in [('F-4E',*args[1:]),(args[0],'Iran',*args[2:]),(*args[:2],'Exact-Base',args[3]),(*args[:3],'1981-01-01')]:
        assert not livery_matches(candidate,*mismatch)
    pack={'_verified':False,'types':{'F-4E-45MC':{'historical':[candidate],'eras':{'coldwar':{'USA':['broad-era']}}}}}
    monkeypatch.setattr(dressing,'_STATIC_LIVERIES',pack['types'])
    assert dressing._pick_livery(args[0],args[1],random.Random(7),era='coldwar',base=args[2],on=args[3])=='test-installed-id'
    assert dressing._pick_livery(args[0],args[1],random.Random(7),era='coldwar',base='Other Base',on=args[3])=='broad-era'


def test_reference_filters_and_public_http_errors():
    with TestClient(app) as client:
        data=client.get('/api/historical-library/catalog?map=nevada&period=nevada-1981').json()
        assert len(data['entries'])==2
        assert all(r['period']=='nevada-1981' for r in data['entries'])
        assert client.get('/api/historical-library/catalog?on=20261004').status_code==400
        assert client.get('/api/historical-library/catalog?map=bogus').status_code==400
        assert client.get('/api/historical-library/profiles/bogus').status_code==404
        svg=client.get('/api/historical-library/profiles/nevada-1981/chart.svg?view=local')
        assert svg.status_code==200 and svg.headers['content-type'].startswith('image/svg+xml')
        assert client.get('/api/historical-library/profiles/nevada-2014/chart.svg?view=local').status_code==404
        assert client.get('/api/historical-library').status_code==200
        assert 'sortiestarter_get_historical_references' in client.get('/api/mcp-guide').text


def test_matching_readings_reach_native_mission_and_document_facts(tmp_path,monkeypatch):
    rows=mission_references('nevada','1981-02-14','F-4E-45MC')
    assert len(rows)==3 and all(r['reference_only'] for r in rows)
    assert any(r['period']=='nevada-1981' for r in rows)
    assert all(r['period']!='f4-reference' for r in mission_references('nevada','1980-06-01','F-16C_50'))
    path=tmp_path/'references.miz'
    from missiongen import StarterBuilder
    from missiongen.brief import build_brief
    builder=StarterBuilder(Recipe.from_dict({'map':'nevada','era':'coldwar',
        'aircraft':'F_4E_45MC','bb_kneeboard':False,'bb_ambient':False,'bb_dressing':False}))
    mission=builder.build();mission.save(str(path))
    expected=mission_references('nevada',mission.start_time.date().isoformat(),'F-4E-45MC')
    assert expected and builder.stats['historical_references']==expected
    with zipfile.ZipFile(path) as z:
        native=z.read('l10n/DEFAULT/dictionary').decode()
        assert 'HISTORICAL READING' in native
        assert all(row['url'] in native for row in expected)
    assert all(row['url'] in '\n'.join(builder.kb_ctx['historical_notes']) for row in expected)
    pdf=tmp_path/'brief.pdf';md=tmp_path/'brief.md'
    build_brief(builder.brief_ctx,builder.kb_ctx,str(pdf),str(md))
    assert all(row['url'] in md.read_text() for row in expected)
    assert pdf.read_bytes().startswith(b'%PDF')
    from missiongen import historical_library
    expanded=deepcopy(catalog())
    for i in range(4):
        extra=deepcopy(expanded['entries'][0]);extra.update(id=f'additional-reading-{i}',subject_from='1981-02-01',subject_to='1981-02-28')
        expanded['entries'].append(extra)
    with monkeypatch.context() as scope:
        scope.setattr(historical_library,'catalog',lambda **filters:expanded)
        assert len(mission_references('nevada','1981-02-14','F-4E-45MC'))==3



@pytest.mark.parametrize('width',[1280,390])
def test_real_browser_library_filters_chart_keyboard_and_date_limits(site,width,tmp_path):
    pw=pytest.importorskip('playwright.sync_api')
    with pw.sync_playwright() as p:
        browser=p.chromium.launch();page=browser.new_page(viewport={'width':width,'height':900});errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(site+'/api/historical-library')
        page.wait_for_selector('#history-count')
        assert page.locator('.reference-card:visible').count()==18
        page.locator('#history-map').select_option('nevada')
        page.locator('#history-period').select_option('nevada-1981')
        assert page.locator('.reference-card:visible').count()==2
        page.locator('#history-search').fill('no such reference xyz')
        assert page.locator('#history-empty').is_visible()
        page.locator('#history-reset').click()
        assert page.locator('.reference-card:visible').count()==18
        page.locator('#history-extent').select_option('local')
        marker=page.locator('.reference-profile:visible .point-diagram:visible .reference-point').first
        marker.focus();marker.press('Enter')
        assert 'datum unverified' in page.locator('#history-point-detail').inner_text().lower()
        assert page.locator('#history-chart-download').get_attribute('href').endswith('?view=local')
        page.locator('#history-profile').select_option('nevada-2014')
        assert page.locator('.reference-profile:visible .reference-point').count()==6
        assert not page.locator('#history-extent-label').is_visible()
        page.locator('#history-on').fill('1944-07-07')
        assert 'exact arrival unknown' in page.locator('tr[data-precision="circa"] .date-relation').inner_text()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
        assert not errors
        page.screenshot(path=str(tmp_path/f'history-{width}.png'),full_page=True)
        browser.close()


def test_content_ledger_retains_reviews_only_for_unchanged_evidence(monkeypatch):
    from scripts import audit_historical_content as audit
    first=audit.inventory()
    assert first['counts']['live_template'] > 1000
    assert first['counts']['published_collection_mission']==59
    reviewed=first['records'][0]
    reviewed['claim_assessment']={'status':'approximate','notes':'Bounded review; unit presence unknown.'}
    second=audit.inventory(first)
    assert all(row['change_status']=='unchanged_since_snapshot' for row in second['records'])
    assert second['records'][0]['claim_assessment']==reviewed['claim_assessment']
    original=audit.template_previews
    def changed(key):
        records=deepcopy(original(key))
        for maps in records.values():
            for history in maps.values():history['notes'].append('New evidence requiring review')
        return records
    monkeypatch.setattr(audit,'template_previews',changed)
    third=audit.inventory(first)
    assert third['records'][0]['change_status']=='changed_since_review'
    assert 'claim_assessment' not in third['records'][0]
    assert third['records'][0]['previous_claim_assessment']==reviewed['claim_assessment']
