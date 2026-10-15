"""Account controls, focus, private archive actions and mobile layout in Chromium."""
import json
import pytest
from test_refactor_browser import site


@pytest.mark.parametrize('width', [1280, 390])
def test_profile_and_archives_are_accessible_without_changing_guest_navigation(site, width):
    pw = pytest.importorskip('playwright.sync_api')
    with pw.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width':width,'height':900})
        errors = []
        page.on('pageerror',lambda error:errors.append(str(error)))
        state = {'enabled':True,'user':{'id':'test-profile','name':'Pilot <script>evil()</script>'},'csrf':'browser-csrf'}
        page.route('**/api/account',lambda route:route.fulfill(json=state))
        page.route('**/api/account/missions',lambda route:route.fulfill(json={'missions':[
            {'id':'test-mission','title':'Original <mission>','created_at':1,'version':'1.114.1',
             'recipe':{'map':'caucasus','era':'coldwar','aircraft':'F_4E_45MC','seed':71}}]}))
        page.goto(site);page.wait_for_function('OPT !== null && SortieAccount.signedIn')
        assert page.locator('#viewtabs button').count() == 4
        page.locator('#account_button').click()
        page.wait_for_selector('#account_missions article')
        assert page.locator('#account_name').input_value() == state['user']['name']
        assert page.locator('#account_content script').count() == 0
        assert page.locator('#account_missions h4').inner_text() == 'Original <mission>'
        assert page.get_by_role('link',name='Download original .miz').get_attribute('href') == '/api/account/missions/test-mission/download?format=miz'
        assert page.evaluate('SortieAccount.generationRequest().url') == '/api/account/generate'
        page.locator('#account_save').uncheck()
        assert page.evaluate('SortieAccount.generationRequest().url') == '/api/generate'
        page.keyboard.press('Escape')
        assert not page.locator('#account_dialog').evaluate('(el)=>el.open')
        assert page.locator('#account_button').evaluate('(el)=>el===document.activeElement')
        page.reload();page.wait_for_function('OPT !== null && SortieAccount.signedIn')
        assert page.evaluate('SortieAccount.generationRequest().url') == '/api/generate'
        page.locator('#account_button').click()
        page.wait_for_selector('#account_missions article')
        assert page.locator('#account_dialog').evaluate('(el)=>el.scrollWidth<=el.clientWidth+1')
        page.get_by_role('button',name='Edit in Builder',exact=True).click()
        assert page.evaluate('recipe().seed') == 71
        assert page.evaluate('CURRENT_VIEW') == 'builder'
        assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+1')
        assert not errors
        browser.close()


def test_guest_account_explains_saving_and_original_results_use_archived_kit(site):
    pw = pytest.importorskip('playwright.sync_api')
    with pw.sync_playwright() as p:
        browser = p.chromium.launch();page = browser.new_page()
        page.route('**/api/account',lambda route:route.fulfill(json={'enabled':True,'user':None,'csrf':None}))
        page.goto(site);page.wait_for_selector('#account_button:not([hidden])')
        page.locator('#account_button').click()
        page.get_by_role('button',name='Continue with Discord').wait_for()
        assert 'Existing downloads' in page.locator('#account_content').inner_text()
        assert page.get_by_role('button',name='Continue with Discord').count() == 1
        page.locator('#account_close').click()
        page.wait_for_function('OPT !== null')
        result = page.evaluate('kitRows({},"test.miz",null,{},"saved-id")')
        assert 'Saved privately' in result and 'Original Mission Kit' in result
        assert 'kit_kb' not in result
        browser.close()


def test_saving_can_be_disabled_when_browser_storage_is_blocked(site):
    pw = pytest.importorskip('playwright.sync_api')
    with pw.sync_playwright() as p:
        browser = p.chromium.launch();page=browser.new_page()
        page.add_init_script("Storage.prototype.setItem=function(){throw new Error('storage blocked');}")
        page.route('**/api/account',lambda route:route.fulfill(json={'enabled':True,'user':{'id':'p','name':'Pilot'},'csrf':'c'}))
        page.route('**/api/account/missions',lambda route:route.fulfill(json={'missions':[]}))
        page.goto(site);page.wait_for_function('SortieAccount.signedIn')
        page.locator('#account_button').click();page.locator('#account_save').wait_for()
        page.locator('#account_save').uncheck()
        assert page.evaluate('SortieAccount.generationRequest().url') == '/api/generate'
        assert 'applies to this tab' in page.locator('#account_status').inner_text()
        browser.close()
