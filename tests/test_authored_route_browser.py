"""Real Builder interactions, preserved recipes and deferred map loading."""
import pytest
from test_refactor_browser import site
from test_authored_route import BASE, POINTS


@pytest.mark.parametrize('width',[1280,390])
def test_route_editor_map_order_undo_and_share_roundtrip(site,width):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser=p.chromium.launch();page=browser.new_page(viewport={'width':width,'height':1000});errors=[];requests=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('request',lambda r:requests.append(r.url))
        page.goto(site);page.wait_for_function('NAV_READY')
        assert not any('/api/route-preview' in url for url in requests)
        page.evaluate('(r)=>{applyRecipe(r);showView("builder");showScreen("world");}',BASE)
        page.locator('#route_mode').select_option('authored')
        page.wait_for_function('document.getElementById("route_status").textContent.includes("Add your first")')
        page.locator('#route_add').click()
        page.wait_for_function('document.querySelectorAll(".route-marker").length===1')
        page.locator('#wp_name').fill('RENDEZVOUS');page.locator('#wp_name').press('Tab')
        page.locator('#wp_alt').fill('12000');page.locator('#wp_alt').press('Tab')
        page.locator('#wp_speed').fill('350');page.locator('#wp_speed').press('Tab')
        page.wait_for_function('document.querySelectorAll(".route-marker").length===1')
        page.locator('#route_map').click(position={'x':120,'y':100})
        page.locator('#route_add').click()
        page.wait_for_function('document.querySelectorAll(".route-marker").length===2')
        page.locator('#route_up').click()
        assert page.evaluate('recipe().waypoints[0].name')=='WP2'
        page.locator('#route_undo').click()
        assert page.evaluate('recipe().waypoints[0].name')=='RENDEZVOUS'
        page.locator('#route_recovery').select_option('home')
        recipe=page.evaluate('decodeRecipe(encodeRecipe(recipe()))')
        assert recipe['waypoints'][0]['altitude']==pytest.approx(3657.6)
        assert recipe['waypoints'][0]['speed']==pytest.approx(180.0555555556)
        assert recipe['route_recovery']=='home' and not recipe['bb_route']
        assert page.locator('#bb_route').is_disabled()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.reload();page.wait_for_function('NAV_READY')
        assert page.evaluate('recipe().waypoints')==recipe['waypoints']
        page.evaluate('showView("builder");showScreen("world")')
        page.locator('#route_mode').select_option('existing')
        assert page.evaluate('recipe().waypoints||null') is None
        assert page.locator('#bb_route').is_enabled()
        assert not errors
        browser.close()


def test_editing_name_preserves_exact_imported_speed_altitude_and_ids(site):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser=p.chromium.launch();page=browser.new_page()
        page.goto(site);page.wait_for_function('NAV_READY')
        page.evaluate('(r)=>{applyRecipe(r);showView("builder");showScreen("world");}',{**BASE,'waypoints':POINTS})
        page.wait_for_selector('.route-marker')
        page.locator('#wp_name').fill('JOIN ALPHA');page.locator('#wp_name').press('Tab')
        point=page.evaluate('recipe().waypoints[0]')
        assert point=={**POINTS[0],'name':'JOIN ALPHA'}
        page.locator('#wp_system').select_option('local')
        page.wait_for_function('document.getElementById("wp_system").value==="local"')
        assert 'x' in page.evaluate('recipe().waypoints[0].position')
        page.locator('#route_delete').click()
        page.locator('#route_undo').click()
        assert page.evaluate('recipe().waypoints[0].id')=='join'
        browser.close()


def test_drag_marker_has_one_undo_and_keeps_other_point(site):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser=p.chromium.launch();page=browser.new_page(viewport={'width':1280,'height':1000})
        page.goto(site);page.wait_for_function('NAV_READY')
        page.evaluate('(r)=>{applyRecipe(r);showView("builder");showScreen("world");}',{**BASE,'waypoints':POINTS})
        page.wait_for_selector('.route-marker');marker=page.locator('.route-marker').first
        marker.scroll_into_view_if_needed();box=marker.bounding_box();x=box['x']+box['width']/2;y=box['y']+box['height']/2
        page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+15,y+10,steps=5);page.mouse.up()
        page.wait_for_function('"x" in recipe().waypoints[0].position')
        assert page.evaluate('recipe().waypoints[1]')==POINTS[1]
        page.locator('#route_undo').click()
        assert page.evaluate('recipe().waypoints')==POINTS
        browser.close()


def test_changing_map_era_kind_and_template_retains_authored_route(site):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser=p.chromium.launch();page=browser.new_page()
        page.goto(site);page.wait_for_function('NAV_READY')
        page.evaluate('(r)=>applyRecipe(r)',{**BASE,'waypoints':POINTS,'route_recovery':'home'})
        for action in ["""document.querySelector('#maps .card[data-k="syria"]').click()""",
                       """document.querySelector('#eras .card[data-k="coldwar"]').click()""",
                       'pickKind("strike")','applyScenarioPreset("qf_guns", true)']:
            page.evaluate(action)
            assert page.evaluate('recipe().waypoints')==POINTS
            assert page.evaluate('recipe().route_recovery')=='home'
        assert not page.evaluate('recipe().bb_route')
        page.evaluate('applyScenarioPreset("qf_guns")')
        assert page.evaluate('recipe().waypoints') is None
        browser.close()


def test_fit_route_and_name_edit_at_native_numeric_limits(site):
    from playwright.sync_api import sync_playwright
    points=[{**POINTS[0],'altitude':25000,'speed':1000},POINTS[1]]
    with sync_playwright() as p:
        browser=p.chromium.launch();page=browser.new_page(viewport={'width':1280,'height':1000})
        page.goto(site);page.wait_for_function('NAV_READY')
        page.evaluate('(r)=>{applyRecipe(r);showView("builder");showScreen("world");}',{**BASE,'waypoints':points})
        page.wait_for_selector('.route-marker')
        old=page.locator('.route-line').bounding_box()['width']
        page.locator('#route_fit').click()
        assert page.locator('.route-line').bounding_box()['width']>old
        assert page.locator('#route_fit').inner_text()=='Show theatre'
        page.locator('#wp_name').fill('JOIN MAX');page.locator('#wp_name').press('Tab')
        assert page.evaluate('recipe().waypoints[0]')=={**points[0],'name':'JOIN MAX'}
        browser.close()
