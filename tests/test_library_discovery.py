"""Discovery promises exercised with installed archives, the real UI and native output."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

import pytest
from missiongen import Recipe, generate
from scripts.audit_library import inspect_archive
from ui_source import ROOT


@pytest.fixture(scope='module')
def library_site(tmp_path_factory):
    directory=tmp_path_factory.mktemp('library-discovery')
    env=dict(os.environ,PACKS_DATA_DIR=str(directory/'packs'),ANALYTICS_DATA_DIR=str(directory/'analytics'))
    env.pop('PACKS_OWNER_MACHINE',None);env.pop('FLY_MACHINE_ID',None)
    files=['wk_checkout','wk_proud_phantom','aar_probe_modern_FA_18C_hornet_kc135mprs','aar_boom_modern_F_16C_50_kc135','cq_case3_hornet']
    for name in files:
        if not (ROOT/'packs'/f'{name}.sspack').is_file():
            pytest.skip('Published-pack browser checks need local release packs; run scripts/build_pack.py first.')
    code='from pathlib import Path;from missiongen import packs;'+''.join(f"packs.install(Path('packs/{name}.sspack').read_bytes(),'{name}.sspack');" for name in files)
    result=subprocess.run([sys.executable,'-c',code],cwd=ROOT,env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    server=subprocess.Popen([sys.executable,'-m','uvicorn','server.app:app','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    url=f'http://127.0.0.1:{port}'
    try:
        for _ in range(100):
            try:urllib.request.urlopen(url+'/api/health',timeout=1);break
            except Exception:
                assert server.poll() is None,'Local server stopped'
                time.sleep(.1)
        else:pytest.fail('Local server did not start')
        yield url
    finally:server.terminate();server.wait(timeout=10)


@pytest.fixture
def page(library_site):
    pw=pytest.importorskip('playwright.sync_api')
    with pw.sync_playwright() as p:
        browser=p.chromium.launch();page=browser.new_page(viewport={'width':1280,'height':900});errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(library_site);page.wait_for_function('OPT !== null && NAV_READY');page.evaluate('showView("library")')
        yield page
        assert not errors,errors
        browser.close()


def keys(page):return page.evaluate('libItems().filter(libPasses).map(t=>t.k)')


def own(page,maps,aircraft,modules=()):
    page.evaluate('(owned)=>{ownSet_({...owned,set:true});clearFilters();toggleOwn();}',{'maps':maps,'aircraft':aircraft,'modules':list(modules)})


def test_aircraft_and_map_filters_find_all_collection_requirements_and_variants(page):
    page.evaluate("document.getElementById('lfAc').value='F_4E_45MC';renderLib()")
    got=keys(page)
    assert {'pack_wk_checkout','pack_wk_proud_phantom','form_close','form_check'}<=set(got)
    assert 'Squadron Checkout' in page.locator('#lgrid').inner_text() and 'Proud Phantom' in page.locator('#lgrid').inner_text()
    page.evaluate("clearFilters();document.getElementById('lfMap').value='persiangulf';renderLib()")
    assert any('aar_probe' in k for k in keys(page))
    page.locator('#lfSearch').fill('Phantom')
    assert 'pack_wk_checkout' not in keys(page) # Germany collection cannot match Persian Gulf.


def test_fixed_collections_require_every_map_aircraft_and_additional_module(page):
    own(page,['germany','sinai','persiangulf','nevada'],[])
    assert not any(k.startswith('pack_') for k in keys(page))
    own(page,['persiangulf'],['FA_18C_hornet'])
    assert any('aar_probe' in k for k in keys(page)) # Both terrains owned: Caucasus is free.
    # Caucasus is free, so the probe pack DOES have both terrains; Supercarrier recovery remains excluded.
    assert not any('cq_case3' in k for k in keys(page))
    own(page,['persiangulf'],['FA_18C_hornet'],['Supercarrier'])
    assert any('cq_case3' in k for k in keys(page))
    own(page,[],['FA_18C_hornet'])
    assert not any('aar_probe' in k for k in keys(page))
    page.evaluate('clearFilters();openDetail(libItems().find(t=>t.k.includes("aar_probe")).k)')
    body=page.locator('#dcardinner').inner_text()
    assert 'Needs:' in body and 'Persian Gulf' in body and '[object Object]' not in body
    assert 'Aircraft: F/A-18C' in body or 'Aircraft: FA-18C' in body
    assert 'your pick' not in body


def test_unknown_collection_dependencies_stay_unconfirmed(page):
    own(page,['germany'],['F_4E_45MC'])
    assert 'pack_wk_checkout' in keys(page)
    page.evaluate("OPT.templates.pack_wk_checkout.pack.requires.modules.push('Unknown author module');renderLib()")
    assert 'pack_wk_checkout' not in keys(page)
    page.evaluate("clearFilters();openDetail('pack_wk_checkout')")
    assert 'Compatibility unconfirmed' in page.locator('#dcardinner').inner_text()
    assert 'Unknown author module' in page.locator('#dcardinner').inner_text()


def test_matching_owned_variant_survives_detail_builder_and_native_generation(page,tmp_path):
    own(page,['nevada'],['F_4E_45MC'])
    page.evaluate("document.getElementById('lfAc').value='F_4E_45MC';document.getElementById('lfMap').value='nevada';document.getElementById('lfEra').value='coldwar';renderLib();openDetail('form_close')")
    assert 'Phantom' not in page.locator('#dSummary').inner_text() or 'F-4E' in page.locator('#dSummary').inner_text()
    assert 'F-4E' in page.locator('#dSummary').inner_text() and 'Nevada' in page.locator('#dSummary').inner_text()
    page.get_by_role('button',name='Customize in Builder',exact=True).click()
    recipe=page.evaluate('decodeRecipe(encodeRecipe(recipe()))')
    assert recipe['map']=='nevada' and recipe['era']=='coldwar' and recipe['aircraft']=='F_4E_45MC'
    rc=Recipe.from_dict({**recipe,'bb_dressing':False,'bb_ambient':False,'bb_branding':False,'bb_kneeboard':False,'bb_briefing':False})
    path=tmp_path/'from-library.miz';generate(rc,str(path));native=inspect_archive(path)
    assert native['theatre']=='Nevada'
    player=next(g for g in native['groups'] if any(u['skill']=='Player' for u in g['units']))
    assert player['units'][0]['type']=='F-4E-45MC'
    page.evaluate('showView("library")')
    assert page.locator('#lfAc').input_value()=='F_4E_45MC'


def test_detail_summary_and_historical_context_follow_era_aircraft_and_map(page):
    page.evaluate("openDetail('form_close');pickEra('coldwar')")
    n=page.locator('#dAcRow .pbtn').count()
    assert n>7 and f'{n} types available' in page.locator('#dSummary').inner_text()
    page.evaluate("pickAircraft('F_4E_45MC');pickMap('germany')")
    assert 'F-4E' in page.locator('#dSummary').inner_text() and 'Germany' in page.locator('#dSummary').inner_text()
    assert '1978-06-21' in page.locator('#dHistorical').inner_text()
    page.evaluate("pickEra('wwii')")
    assert 'F-4E' not in page.locator('#dSummary').inner_text()
    assert page.locator('#dHistorical').inner_text()


@pytest.mark.parametrize('width',[1280,390,320])
@pytest.mark.parametrize('mode',['paper','night'])
def test_catalog_layout_counts_unique_cards_and_keyboard_details(page,width,mode):
    page.set_viewport_size({'width':width,'height':900});page.evaluate('(mode)=>document.body.dataset.mode=mode',mode)
    assert page.locator('#lfeat .libcard').count()==3
    titles=page.locator('#library .libcard h3').all_text_contents();assert len(titles)==len(set(titles))
    assert 'items' in page.locator('#libcount').inner_text() and 'collections' in page.locator('#libcount').inner_text()
    assert page.locator('#lfeat .libcard').first.bounding_box()['y']<800
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert page.locator('#library .lnew').count()==0 and page.locator('#lfSort option[value="new"]').count()==0
    assert 'Threat:' in page.locator('#lfeat .libcard').first.inner_text()
    first=page.locator('#lfeat .libcard').first;first.focus();page.keyboard.press('Enter')
    assert page.locator('#libdetail').evaluate('(el)=>el.classList.contains("on")')
    assert page.get_by_role('button',name='Close details',exact=True).is_visible()
    page.keyboard.press('Escape');assert first.evaluate('(el)=>el===document.activeElement')
    page.locator('[data-lib-format="collection"]').click()
    assert page.locator('[data-lib-format="collection"]').get_attribute('aria-pressed')=='true'
    assert page.locator('#lfeatwrap').is_hidden()
    assert all(k.startswith('pack_') for k in keys(page))
    card=page.locator('#lgrid .libcard').first;card.click()
    primary=page.locator('#libdetail .dcta .prime');assert primary.bounding_box()['height']>=44
    style=primary.evaluate('(el)=>{const s=getComputedStyle(el);return [s.padding,s.fontSize,s.fontWeight]}')
    page.evaluate("openDetail('form_close')")
    assert page.locator('#dgen').evaluate('(el)=>{const s=getComputedStyle(el);return [s.padding,s.fontSize,s.fontWeight]}')==style
    page.evaluate("openDetail(libItems().find(t=>t.pack).k)")
    primary=page.locator('#libdetail .dcta .prime')
    assert page.locator('#libdetail .evlinks a').first.get_attribute('aria-label').startswith('Download mission ')
    page.locator('#dcardinner').evaluate('(el)=>el.scrollTop=el.scrollHeight')
    assert page.get_by_role('button',name='Close details',exact=True).is_visible()
    assert primary.is_visible()
    assert page.locator('#dcardinner').evaluate('(el)=>el.scrollWidth <= el.clientWidth')


def test_declared_supercarrier_is_saved_by_the_ownership_editor(page):
    page.locator('.libraryfilters summary').click()
    page.get_by_role('button',name='My DCS content',exact=True).click()
    checkbox=page.locator('.ochk').filter(has_text='DCS: Supercarrier')
    assert checkbox.get_attribute('aria-checked')=='false'
    checkbox.focus();page.keyboard.press('Space')
    assert checkbox.get_attribute('aria-checked')=='true'
    page.locator('#ownmodal').get_by_role('button',name='Save',exact=True).click()
    assert page.evaluate('JSON.parse(localStorage.ms_owned).modules')==['Supercarrier']
    assert page.locator('#lown').get_attribute('aria-checked')=='true'
    page.locator('#lchipbar').get_by_role('button',name='Clear all',exact=True).click()
    assert page.locator('#lown').get_attribute('aria-checked')=='false'


def test_preferred_training_variant_survives_unrelated_library_filter(page):
    page.evaluate("document.getElementById('lfMap').value='normandy';renderLib();openDetail('form_close',{era:'coldwar',aircraft:'F_4E_45MC'})")
    selected=page.evaluate('({era:libState.era,map:libState.map,aircraft:libState.aircraft})')
    assert selected=={'era':'coldwar','map':'caucasus','aircraft':'F_4E_45MC'}


def test_authored_requirements_and_filenames_are_rendered_as_data(page):
    page.evaluate(r"""const p=OPT.templates.pack_wk_checkout.pack;
      p.requires.modules.push('<img src=x onerror="window.catalogInjected=true">');
      p.events[0].miz='mission/quote" onclick="window.catalogInjected=true.miz';
      openDetail('pack_wk_checkout');""")
    assert page.locator('#libdetail img').count()==0
    assert not page.evaluate('Boolean(window.catalogInjected)')
    assert '<img src=x' in page.locator('#dcardinner').inner_text()
    link=page.locator('#libdetail .evlinks a').first
    assert link.get_attribute('onclick') is None
    assert '%22' in link.get_attribute('href') and '%20' in link.get_attribute('href')
