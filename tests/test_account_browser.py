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
        page.route('**/api/account/selections',lambda route:route.fulfill(json={'selections':[]}))
        page.goto(site);page.wait_for_function('OPT !== null && SortieAccount.signedIn')
        assert page.locator('#viewtabs button').count() == 4
        page.locator('#account_button').click()
        page.wait_for_selector('#account_missions article')
        assert page.locator('#account_name').input_value() == state['user']['name']
        assert page.locator('#account_content script').count() == 0
        assert page.locator('#account_missions h4').inner_text() == 'Original <mission>'
        assert page.get_by_role('link',name='Download original .miz').get_attribute('href') == '/api/account/missions/test-mission/download?format=miz'
        assert page.evaluate('SortieAccount.generationRequest().url') == '/api/account/generate'
        page.locator('#account_preferences').evaluate('(el)=>el.open=true')
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
        page.route('**/api/account/selections',lambda route:route.fulfill(json={'selections':[]}))
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
        page.route('**/api/account/selections',lambda route:route.fulfill(json={'selections':[]}))
        page.goto(site);page.wait_for_function('SortieAccount.signedIn')
        page.locator('#account_button').click();page.locator('#account_save').wait_for(state='attached')
        page.locator('#account_preferences').evaluate('(el)=>el.open=true')
        page.locator('#account_save').uncheck()
        assert page.evaluate('SortieAccount.generationRequest().url') == '/api/generate'
        assert 'applies to this tab' in page.locator('#account_status').inner_text()
        browser.close()


@pytest.mark.parametrize('width',[1280,390])
def test_explicit_saves_keep_builder_library_and_authored_selections(site,width):
    pw=pytest.importorskip('playwright.sync_api')
    with pw.sync_playwright() as p:
        browser=p.chromium.launch();page=browser.new_page(viewport={'width':width,'height':900})
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        state={'enabled':True,'user':{'id':'p','name':'Pilot'},'csrf':'save-csrf'}
        selected=[];posts=[];generations=[]
        page.route('**/api/account',lambda route:route.fulfill(json=state))
        page.route('**/api/account/missions',lambda route:route.fulfill(json={'missions':[]}))
        def selection_route(route):
            if route.request.method=='POST':
                assert route.request.headers['x-csrf-token']=='save-csrf'
                body=route.request.post_data_json;posts.append(body)
                selected.append({'id':str(len(posts)),'title':body.get('name','Selected mission'),
                                 'version':'1.116.0','payload':body})
                route.fulfill(json={'id':str(len(posts))})
            else:route.fulfill(json={'selections':selected})
        page.route('**/api/account/selections',selection_route)
        page.route('**/api/**generate',lambda route:(generations.append(route.request.url),route.abort()))
        page.goto(site);page.wait_for_function('OPT !== null && SortieAccount.signedIn')
        page.evaluate('applyRecipe({...recipe(),slots:4,veteran_wingmen:3,seed:71});showView("builder");showScreen("review")')
        page.locator('#save_builder').click();page.wait_for_selector('#account_selections article')
        assert posts[0]['recipe']['seed']==71 and posts[0]['recipe']['veteran_wingmen']==3
        assert 'Saved to My missions' in page.locator('#account_status').inner_text()
        page.get_by_role('button',name='Open in Builder',exact=True).click()
        assert page.evaluate('recipe().seed')==71
        page.evaluate('showView("library");openDetail(libItems().find(t=>!t.pack).k)')
        page.locator('#save_library').click();page.wait_for_function('document.querySelectorAll("#account_selections article").length===2')
        assert posts[1]['kind']=='recipe' and posts[1]['recipe']['template']
        assert page.evaluate('recipe().seed')==71  # Saving Library content preserves the Builder draft.
        page.locator('#account_close').click();page.evaluate('closeDetail()')
        page.evaluate('''()=>{const t=libItems().find(t=>!t.pack);OPT.templates.pack_test={...OPT.templates[t.k],
          label:'Published test collection',pack:{id:'test',version:'1.2.3',events:[{n:1,label:'Mission <one>',miz:'missions/one.miz'}]}};
          openDetail('pack_test');}''')
        page.locator('[data-save-event="0"]').click();page.wait_for_function('document.querySelectorAll("#account_selections article").length===3')
        assert posts[2]=={'kind':'pack','pack_id':'test','path':'missions/one.miz'}
        assert page.get_by_role('link',name='Download published mission').get_attribute('href')=='/api/pack/test/missions/one.miz'
        page.locator('#account_close').click();page.locator('#save_library').click()
        page.wait_for_function('document.querySelectorAll("#account_selections article").length===4')
        assert posts[3]=={'kind':'pack','pack_id':'test'}
        assert page.locator('#account_dialog').evaluate('(el)=>el.scrollWidth<=el.clientWidth+1')
        page.locator('#account_close').click();page.evaluate('closeDetail()');page.locator('#library_saved').click()
        page.wait_for_selector('#account_selections article')
        assert not generations and not errors
        browser.close()


def test_clicked_save_resumes_after_sign_in_without_accepting_url_save_commands(site):
    pw=pytest.importorskip('playwright.sync_api')
    with pw.sync_playwright() as p:
        browser=p.chromium.launch();page=browser.new_page()
        state={'enabled':True,'user':None,'csrf':None};posts=[]
        page.route('**/api/account',lambda route:route.fulfill(json=state))
        page.route('**/api/account/missions',lambda route:route.fulfill(json={'missions':[]}))
        def selections(route):
            if route.request.method=='POST':posts.append(route.request.post_data_json);route.fulfill(json={'id':'saved'})
            else:route.fulfill(json={'selections':[]})
        page.route('**/api/account/selections',selections)
        def sign_in(route):
            state.update(user={'id':'p','name':'Pilot'},csrf='c')
            route.fulfill(status=302,headers={'Location':site+'/?auth=signed_in'})
        page.route('**/auth/discord?*',sign_in)
        page.goto(site);page.wait_for_function('OPT !== null')
        page.evaluate('applyRecipe({...recipe(),seed:719});showView("builder");showScreen("review")')
        page.locator('#save_builder').click()
        page.get_by_role('button',name='Continue with Discord').click()
        page.wait_for_function('document.querySelector("#account_status").textContent.includes("Saved to My missions")')
        assert len(posts)==1 and posts[0]['recipe']['seed']==719
        assert page.evaluate('sessionStorage.getItem("ss_pending_selection")') is None
        page.goto(site+'/?auth=signed_in&save_recipe=malicious')
        page.wait_for_selector('#account_dialog[open]')
        assert len(posts)==1
        browser.close()
