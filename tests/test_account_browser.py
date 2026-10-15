"""Mission shelf browsing, contextual saves and explicit sharing in Chromium."""
import base64
import json
import pytest
from test_refactor_browser import site


def setup_routes(page,user=True,items=None):
    state={'enabled':True,'user':{'id':'pilot','name':'Pilot <script>evil()</script>'} if user else None,'csrf':'csrf' if user else None}
    library={'items':items or [],'page_path':None}
    page.route('**/api/account',lambda route:route.fulfill(json=state))
    page.route('**/api/account/library',lambda route:route.fulfill(json=library))
    return state,library


def item(category='original',title='Phantom <mission>'):
    return {'id':'mission-id','kind':'mission','title':title,'category':category,'created_at':1,'version':'1.116.0',
            'details':{'map':'caucasus','era':'coldwar','aircraft':'F_4E_45MC','slots':4,'veteran_wingmen':3},
            'open_path':'/?r=example','miz_path':'/api/account/missions/mission-id/download?format=miz',
            'kit_path':'/api/account/missions/mission-id/download?format=kit','share_path':None}


@pytest.mark.parametrize('width',[1280,390])
def test_personal_page_is_browsable_and_sharing_requires_an_explicit_action(site,width):
    pw=pytest.importorskip('playwright.sync_api')
    with pw.sync_playwright() as p:
        browser=p.chromium.launch();page=browser.new_page(viewport={'width':width,'height':900});errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        state,library=setup_routes(page,items=[item(),{**item('setup','Viper practice'),'id':'setup-id','kind':'selection','details':{'map':'nevada','aircraft':'F_16C_50'}}])
        posts=[]
        def share(route):
            posts.append(route.request.post_data_json);library['items'][0]['share_path']='/shared/'+'a'*32
            route.fulfill(json={'path':library['items'][0]['share_path']})
        page.route('**/api/account/shares',share)
        page.goto(site+'/my-missions');page.wait_for_selector('.mission-card')
        assert page.locator('.mission-card').count()==2
        assert page.locator('.mission-card h2').first.inner_text()=='Phantom <mission>'
        assert page.locator('#mission_grid script').count()==0
        page.locator('#mission_search').fill('Viper');assert page.locator('.mission-card').count()==1
        page.locator('#mission_search').fill('F-16C Viper');assert page.locator('.mission-card').count()==1
        assert page.locator('.mission-card h2').inner_text()=='Viper practice'
        page.locator('#mission_search').fill('');page.get_by_role('button',name='Original files',exact=True).click()
        assert page.locator('.mission-card').count()==1
        assert page.get_by_role('link',name='Download .miz').get_attribute('href')==item()['miz_path']
        assert not posts
        page.get_by_role('button',name='Share',exact=True).click()
        assert 'other missions stay private' in page.locator('#dialog_body').inner_text()
        assert not posts
        page.get_by_role('button',name='Create share link').click();page.locator('#shared_url').wait_for()
        assert posts==[{'kind':'mission','id':'mission-id'}]
        assert page.locator('#shared_url').input_value()==site+'/shared/'+'a'*32
        page.evaluate("()=>{navigator.clipboard.writeText=async value=>{window.testCopiedLink=value}}")
        page.get_by_role('button',name='Copy link',exact=True).click()
        assert page.evaluate('window.testCopiedLink')==site+'/shared/'+'a'*32
        page.evaluate("()=>{navigator.clipboard.writeText=async()=>{throw new Error('clipboard blocked')}}")
        page.get_by_role('button',name='Copy link',exact=True).click()
        assert 'clipboard access is unavailable' in page.locator('#dialog_status').inner_text()
        assert page.locator('#shared_url').evaluate('(el)=>el===document.activeElement')
        page.keyboard.press('Escape');assert not page.locator('#shelf_dialog').evaluate('(el)=>el.open')
        page.get_by_role('button',name='Settings',exact=True).click()
        assert page.locator('#profile_name').input_value()==state['user']['name']
        page.locator('#auto_save').uncheck()
        page.keyboard.press('Escape');page.goto(site);page.wait_for_function('OPT !== null && SortieAccount.signedIn')
        assert page.evaluate('SortieAccount.generationRequest().url')=='/api/generate'
        assert page.locator('#viewtabs button').count()==4
        page.locator('#account_button').click();page.wait_for_url('**/my-missions')
        assert page.locator('body').evaluate('(el)=>el.scrollWidth<=window.innerWidth+1')
        assert not errors
        browser.close()


def test_contextual_save_keeps_builder_draft_and_opens_full_page(site):
    pw=pytest.importorskip('playwright.sync_api')
    with pw.sync_playwright() as p:
        browser=p.chromium.launch();page=browser.new_page();state,library=setup_routes(page);posts=[]
        def save(route):
            body=route.request.post_data_json;posts.append(body)
            library['items'].append({**item('setup',body.get('name','My saved setup')),'id':str(len(posts)),'kind':'selection'})
            route.fulfill(json={'id':str(len(posts))})
        page.route('**/api/account/selections',save)
        page.goto(site);page.wait_for_function('OPT !== null && SortieAccount.signedIn')
        page.evaluate('applyRecipe({...recipe(),slots:4,veteran_wingmen:3,seed:71});showView("builder");showScreen("review")')
        page.locator('#save_builder').click();page.locator('#save_notice').wait_for()
        page.wait_for_function('document.querySelector("#save_notice").textContent.includes("Saved to My missions.")')
        assert not page.locator('#account_dialog').evaluate('(el)=>el.open')
        assert posts[0]['recipe']['seed']==71 and posts[0]['recipe']['veteran_wingmen']==3
        page.evaluate('showView("library");openDetail(libItems().find(t=>!t.pack).k)')
        with page.expect_response(lambda response:response.url.endswith('/api/account/selections') and response.request.method=='POST'):
            page.locator('#save_library').click()
        page.wait_for_function('document.querySelector("#save_notice").textContent.includes("Saved to My missions.")')
        assert len(posts)==2 and page.evaluate('recipe().seed')==71
        page.evaluate('closeDetail()');page.get_by_role('link',name='View My missions',exact=True).click()
        page.wait_for_selector('.mission-card');assert page.locator('.mission-card').count()==2
        browser.close()


def test_clicked_save_resumes_after_sign_in_without_accepting_url_save_commands(site):
    pw=pytest.importorskip('playwright.sync_api')
    with pw.sync_playwright() as p:
        browser=p.chromium.launch();page=browser.new_page();state,library=setup_routes(page,user=False);posts=[]
        def selections(route):posts.append(route.request.post_data_json);route.fulfill(json={'id':'saved'})
        page.route('**/api/account/selections',selections)
        def sign_in(route):
            state.update(user={'id':'p','name':'Pilot'},csrf='c')
            route.fulfill(status=302,headers={'Location':site+'/?auth=signed_in'})
        page.route('**/auth/discord?*',sign_in)
        page.goto(site);page.wait_for_function('OPT !== null')
        page.evaluate('applyRecipe({...recipe(),seed:719});showView("builder");showScreen("review")')
        page.locator('#save_builder').click();page.get_by_role('button',name='Continue with Discord').click()
        page.wait_for_function('document.querySelector("#save_notice")?.textContent.includes("Saved to My missions.")')
        assert len(posts)==1 and posts[0]['recipe']['seed']==719
        assert page.evaluate('sessionStorage.getItem("ss_pending_selection")') is None
        page.goto(site+'/?auth=signed_in&save_recipe=malicious');page.wait_for_url('**/my-missions')
        assert len(posts)==1
        browser.close()


def test_guest_and_public_pages_explain_access_without_profile_controls(site):
    pw=pytest.importorskip('playwright.sync_api')
    with pw.sync_playwright() as p:
        browser=p.chromium.launch();page=browser.new_page();setup_routes(page,user=False)
        page.goto(site+'/my-missions');page.get_by_role('link',name='Continue with Discord').wait_for()
        assert 'private until' in page.locator('#mission_grid').inner_text()
        assert page.get_by_role('link',name='Continue with Discord').get_attribute('href').endswith('return_to=%2Fmy-missions')
        page.route('**/api/pilots/*',lambda route:route.fulfill(json={'name':'Shared pilot','items':[item()]}))
        page.goto(site+'/pilots/'+'a'*32);page.wait_for_selector('.mission-card')
        assert page.locator('#shelf_title').inner_text()=='Shared pilot’s missions'
        assert page.get_by_role('button',name='Share',exact=True).count()==0
        assert page.get_by_role('button',name='Remove',exact=True).count()==0
        assert page.get_by_role('link',name='Download .miz').count()==1
        assert page.get_by_role('button',name='Settings',exact=True).is_hidden()
        browser.close()
