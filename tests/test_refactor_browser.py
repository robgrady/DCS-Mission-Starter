"""Exercise the assembled controllers and offline release label in a real browser."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

import pytest
from missiongen import __version__
from ui_source import ROOT

@pytest.fixture(scope='module')
def site(tmp_path_factory):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0)); port = sock.getsockname()[1]
    directory = tmp_path_factory.mktemp('refactor-browser')
    env = dict(os.environ, PACKS_DATA_DIR=str(directory/'packs'),
               ANALYTICS_DATA_DIR=str(directory/'analytics'))
    env.pop('PACKS_OWNER_MACHINE',None); env.pop('FLY_MACHINE_ID',None)
    server = subprocess.Popen([sys.executable,'-m','uvicorn','server.app:app','--port',str(port)],
                              cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    url = f'http://127.0.0.1:{port}'
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(url+'/api/health',timeout=1); break
            except Exception:
                if server.poll() is not None:pytest.fail('local server failed to start')
                time.sleep(.1)
        else:pytest.fail('local server did not become ready')
        yield url
    finally:
        server.terminate(); server.wait(timeout=10)


def test_offline_options_still_show_the_current_release_and_retry(site):
    pw = pytest.importorskip('playwright.sync_api')
    with pw.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(); errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.route('**/api/options',lambda route:route.abort())
        page.goto(site)
        page.wait_for_selector('#loaderror:not([hidden])')
        assert page.locator('#appver').inner_text() == 'v'+__version__
        assert not errors
        page.unroute('**/api/options')
        page.locator('#loadretry').click()
        page.wait_for_function('OPT !== null')
        assert page.evaluate('libItems().length') > 0
        assert not errors
        browser.close()


@pytest.mark.parametrize('width',[1280,390])
def test_carrier_restore_share_and_library_use_the_assembled_controllers(site,width):
    pw = pytest.importorskip('playwright.sync_api')
    with pw.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width':width,'height':900}); errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(site); page.wait_for_function('OPT !== null')
        rc={'map':'caucasus','era':'coldwar','aircraft':'F_14A_135_GR',
            'bb_carrier':True,'home_airbase':'CARRIER','carrier_hull':'forrestal',
            'carrier_layout':'launch','carrier_cap':True,'seed':19,
            'comms':{'tanker':253.650},'slots':2}
        page.evaluate('(rc)=>{applyRecipe(rc);showView("builder");showScreen("review");}',rc)
        restored = page.evaluate('decodeRecipe(encodeRecipe(recipe()))')
        assert restored['map'] == 'caucasus' and restored['carrier_hull'] == 'forrestal'
        assert restored['home_airbase'] == 'CARRIER' and restored['slots'] == 2
        assert restored['comms']['tanker'] == 253.650
        page.evaluate('showView("library")')
        assert page.locator('#appver').inner_text() == 'v'+__version__
        assert page.evaluate('libItems().length') > 0
        page.evaluate('openDetail("qf_bfm")')
        page.wait_for_selector('#libdetail.on')
        page.keyboard.press('Escape')
        assert not page.locator('#libdetail').evaluate('(el)=>el.classList.contains("on")')
        page.go_back()
        assert page.evaluate('CURRENT_VIEW') == 'builder'
        assert not errors
        browser.close()


@pytest.mark.parametrize('width',[1280,390])
def test_historical_details_follow_the_selected_era_without_overflow(site,width):
    pw=pytest.importorskip('playwright.sync_api')
    with pw.sync_playwright() as p:
        browser=p.chromium.launch()
        page=browser.new_page(viewport={'width':width,'height':900});errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(site);page.wait_for_function('OPT !== null')
        page.evaluate('showView("library");openDetail("berlin_corridor_transit")')
        box=page.locator('#dHistorical')
        assert '1978-06-21' in box.inner_text()
        box.locator('summary').click()
        assert 'exercise limit' in box.inner_text()
        assert box.locator('a').count()==4
        assert box.evaluate('(el)=>el.scrollWidth <= el.clientWidth+1')
        page.keyboard.press('Escape')
        page.evaluate('openDetail("qf_bfm");pickEra("coldwar")')
        assert '1978-06-21' in page.locator('#dHistorical').inner_text()
        page.evaluate('pickEra("modern")')
        assert '2011-06-21' in page.locator('#dHistorical').inner_text()
        assert not errors
        browser.close()
