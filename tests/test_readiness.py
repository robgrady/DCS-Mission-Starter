"""Readiness never substitutes a recipe, authored flight or survey for emitted evidence."""
import hashlib
import json
import zipfile
import pytest
from fastapi.testclient import TestClient
from missiongen import Recipe, __version__
from missiongen.readiness import selection_report
from server.app import app
from server.mission_kit import build_kit
from scripts.audit_library import inspect_archive
from test_refactor_browser import site
from test_mission_kit_wiring import run_js


def test_selection_humans_carrier_and_survey_limits():
    report=selection_report(Recipe.from_dict({'era':'modern','slots':4,'veteran_wingmen':3}))
    assert report['flight']['human_aircraft']==1 and report['flight']['ai_aircraft']==3
    assert report['validation']=={'selection':'checked','generated_file':'not_built','dcs_flight':'unverified','dcs_version':None,'module_versions':None}
    assert report['parking']['measured_directions']>0
    assert 'Static directions' in report['parking']['text']
    carrier=selection_report(Recipe.from_dict({'era':'modern','aircraft':'FA_18C_hornet','home_airbase':'CARRIER','carrier_hull':'cvn_71'}))
    assert any(r['key']=='Supercarrier' for r in carrier['requirements'])
    assert carrier['parking']['status']=='not_applicable'
    assert 'not fully certified' in carrier['dependencies']


@pytest.mark.parametrize('recipe, phrase',[
 ({'map':'bogus'},'known theater'),({'slots':4,'veteran_wingmen':4},'veteran_wingmen'),
 ({'era':'modern','aircraft':'F_16C_50','home_airbase':'CARRIER','carrier_hull':'cvn_71'},'cannot operate'),
 ({'era':'modern','home_airbase':'CARRIER','coalition':'red'},'blue coalition')])
def test_bad_setup_api_is_actionable_without_generating(recipe,phrase):
    with TestClient(app) as c:r=c.post('/api/readiness',json={'recipe':recipe})
    assert r.status_code==400 and phrase in r.json()['detail']


@pytest.fixture(scope='module')
def routed_kit(tmp_path_factory):
    return build_kit(Recipe.from_dict({'era':'modern','aircraft':'F_14B_U','slots':4,'veteran_wingmen':3,'bb_route':True,'bb_targets':True,'bb_dressing':False,'bb_ambient':False,'bb_sams':False}),tmp_path_factory.mktemp('readiness-kit'))


def test_generated_counts_and_navigation_match_native_mission(routed_kit):
    manifest=routed_kit['manifest']; report=manifest['readiness']
    assert report['stage']=='generated'
    assert report['validation']['dcs_flight']=='unverified'
    native=inspect_archive(routed_kit['miz'])
    group=next(g for g in native['groups'] if any(u['skill']=='Player' for u in g['units']))
    assert [u['skill'] for u in group['units']]==['Player','High','High','High']
    assert report['flight']['human_aircraft']==1 and report['flight']['ai_aircraft']==3
    assert manifest['kit']['flight']==report['flight']
    with zipfile.ZipFile(routed_kit['bundle']) as z:
        nav=json.loads(z.read('navigation.json'))
        assert len(nav['route'])>=3
        assert nav['native_units']['ETA']=='seconds from mission start'
        assert nav['mission_start_seconds']==43200
        assert {'x','y','latitude','longitude'} <= nav['route'][0]['point'].keys()
        points=nav['flights'][0]['points']
        assert len(points)==len(group['route'])
        for actual,wanted in zip(points,group['route']):
            for key in ('name','x','y','alt','speed','ETA'):assert actual[key]==wanted[key]
        assert manifest['mission']['sha256']==hashlib.sha256(z.read('mission.miz')).hexdigest()
        assert 'dtc_setup_card.md' in z.namelist()


def test_mission_kit_single_player_install_uses_actual_human_count():
    out=run_js('''
const esc=v=>String(v); const rc={slots:4,veteran_wingmen:3};
console.log(JSON.stringify(kitRows({flight:{human_aircraft:1,ai_aircraft:3,text:'1 human + 3 AI'}},'test.miz',null,rc)));
''',['kitRows'])
    assert 'Single-player' in out and 'No single-player slot' not in out and '3 AI' in out


@pytest.mark.parametrize('width',[1280,390,320])
def test_real_browser_readiness_all_generation_doors(site,width):
    pw=pytest.importorskip('playwright.sync_api')
    with pw.sync_playwright() as p:
        browser=p.chromium.launch();page=browser.new_page(viewport={'width':width,'height':900});errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(site);page.wait_for_function('OPT !== null && NAV_READY')
        page.evaluate('showView("builder"); applyRecipe({...recipe(),era:"modern",slots:4,veteran_wingmen:3}); showScreen("review")')
        page.wait_for_function('document.querySelector("#builder_readiness").textContent.includes("Selection checked")')
        text=page.locator('#builder_readiness').inner_text()
        assert '1 human aircraft + 3 veteran AI' in text and 'DCS flight unverified' in text
        assert __version__ in text
        page.evaluate('showView("library");openDetail("f14_tarps_recon")')
        page.wait_for_function('document.querySelector("#library_readiness").textContent.includes("Selection checked")')
        assert 'F-14BU' in page.locator('#library_readiness').inner_text()
        page.evaluate('closeDetail();showView("quick");QF.type="qf_bfm";QF.ac="F_16C_50";QF.map="caucasus";qfRender()')
        page.wait_for_function('document.querySelector("#quick_readiness").textContent.includes("Selection checked")')
        assert 'Single-player' in page.locator('#quick_readiness').inner_text()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert not errors
        browser.close()


def test_authored_crew_requirements_follow_actual_aircraft():
    assert selection_report(Recipe.from_dict({'template':'backseat_intercept','era':'modern'}))['requirements'][1]['key']=='F_14B_U'
    assert selection_report(Recipe.from_dict({'template':'rio_fleet_defense','era':'coldwar'}))['requirements'][1]['key']=='F_14A_135_GR'


def test_stale_readiness_response_cannot_overwrite_newer_selections():
    import subprocess, shutil
    from pathlib import Path
    source=(Path(__file__).parents[1]/'frontend/assets/readiness.js').read_text()
    result=subprocess.run([shutil.which('node'),'-e',source+'''
const box={innerHTML:'',isConnected:true}, waiting=[];
const esc=v=>String(v), catalogOwnsAircraft=()=>true;
const c=createReadinessController({document:{getElementById:()=>box},fetch:()=>new Promise(resolve=>waiting.push(resolve)),ownedMaps:()=>null,ownedAc:()=>null,ownedModules:()=>null,esc});
(async()=>{
 const old=c.refresh('box',{seed:1}), fresh=c.refresh('box',{seed:2});
 waiting[1]({ok:false,json:async()=>({detail:'new selection'})}); await fresh;
 waiting[0]({ok:false,json:async()=>({detail:'stale selection'})}); await old;
 console.log(box.innerHTML);
})();
'''],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert 'new selection' in result.stdout and 'stale selection' not in result.stdout


def test_validation_pack_preserves_native_contracts_and_unflown_status(tmp_path):
    from scripts.build_validation_pack import build, CASES
    from test_library_contracts import test_every_affected_entry_has_its_emitted_contract
    archive=build(tmp_path/'flight')
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        manifest=json.loads(z.read('manifest.json'))
        assert len(manifest['cases'])==5
        for name,inputs,_ in CASES:
            record=json.loads(z.read(name+'/expected.json'))
            assert record['dcs_flight']=='not_run' and record['dks_import']=='not_run'
            assert record['mission_sha256']==hashlib.sha256(z.read(name+'/mission.miz')).hexdigest()
            if name!='dks':
                test_every_affected_entry_has_its_emitted_contract((inputs['template'],Recipe.from_dict(inputs),record['native'],{}))


def test_skipped_carrier_has_no_spurious_module_requirement():
    r=selection_report(Recipe.from_dict({'map':'nevada','era':'modern','aircraft':'FA_18C_hornet','bb_carrier':True,'carrier_hull':'cvn_71'}))
    assert not any(item['key']=='Supercarrier' for item in r['requirements'])
    assert any('skipped' in w for w in r['warnings'])


def readiness_js(code):
    import subprocess, shutil
    from pathlib import Path
    source=(Path(__file__).parents[1]/'frontend/assets/library-catalog.js').read_text()+'\n'+(Path(__file__).parents[1]/'frontend/assets/readiness.js').read_text()
    r=subprocess.run([shutil.which('node'),'-e',source+code],capture_output=True,text=True)
    assert r.returncode==0,r.stderr
    return r.stdout


def test_cleared_readiness_stays_empty_when_pending_request_finishes():
    output=readiness_js('''
const box={innerHTML:'',isConnected:true,set textContent(v){this.innerHTML=v;}}, waiting=[];
const c=createReadinessController({document:{getElementById:()=>box},fetch:()=>new Promise(resolve=>waiting.push(resolve)),ownedMaps:()=>null,ownedAc:()=>null,ownedModules:()=>null,esc:v=>v});
(async()=>{
 const old=c.refresh('box',{seed:1});c.clear('box');
 waiting[0]({ok:false,json:async()=>({detail:'obsolete selection'})});await old;
 console.log(JSON.stringify(box.innerHTML));
})();
''')
    assert output.strip()=='""'


def test_owned_carrier_aircraft_family_confirms_forrestal_dependency():
    report=selection_report(Recipe.from_dict({'era':'coldwar','aircraft':'F_14A_135_GR','bb_carrier':True,'carrier_hull':'forrestal'}))
    hull=next(r for r in report['requirements'] if r['key']=='F-14 Tomcat')
    assert hull['ownership']=={'aircraft':'F_14B'}
    output=readiness_js('''
const box={innerHTML:'',isConnected:true};
const c=createReadinessController({document:{getElementById:()=>box},fetch:async()=>({ok:true,json:async()=>REPORT}),ownedMaps:()=>new Set(['caucasus']),ownedAc:()=>new Set(['F_14A_135_GR']),ownedModules:()=>new Set(),esc:v=>v});
c.refresh('box',{}).then(()=>console.log(box.innerHTML));
'''.replace('REPORT','('+json.dumps(report)+')'))
    assert 'Matches your declared content' in output and 'Ownership not confirmed' not in output
