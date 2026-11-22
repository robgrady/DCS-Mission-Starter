"""Home, Train and browser history stay usable while mission options load."""
import base64
import json

import pytest

from test_authored_route import BASE, POINTS
from test_refactor_browser import site


def tab(page, name):
    return page.locator(f'#viewtabs button[data-v="{name}"]')


@pytest.mark.parametrize('width', [1280, 390])
def test_home_and_train_work_through_slow_and_failed_options(site, width):
    pw = pytest.importorskip('playwright.sync_api')
    with pw.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': width, 'height': 900})
        requests, errors, pending = [], [], []
        page.on('request', lambda req: requests.append(req.url))
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.route('**/api/options', lambda route: pending.append(route))

        page.goto(site, wait_until='domcontentloaded')
        assert page.locator('#entry.on').is_visible()
        assert page.locator('#loadstatus').is_hidden()
        assert not any('/api/options' in url or '/api/courses' in url or '/api/first-flight' in url for url in requests)
        with page.expect_request('**/api/options'):
            tab(page, 'builder').click()
        assert page.locator('#loadstatus').is_visible()
        assert page.url.endswith('?v=builder&step=theater')

        with page.expect_request('**/api/first-flight'), page.expect_request('**/api/courses'):
            tab(page, 'pipeline').click()
        assert page.locator('#pipeline.on').is_visible()
        assert page.locator('#loadstatus').is_hidden()
        page.locator('#pcourses h2').wait_for()
        assert page.locator('#first_flight h2').is_visible()
        assert len(pending) == 1

        pending[0].fulfill(status=503, json={'detail': 'Unreachable'})
        page.wait_for_function('optionsError && optionsRequest === null')
        assert page.locator('#loaderror').is_hidden()
        page.go_back()
        assert page.locator('#loaderror').is_visible()
        assert tab(page, 'builder').get_attribute('aria-current') == 'page'
        page.go_forward()
        assert page.locator('#pipeline.on').is_visible()
        assert page.locator('#loaderror').is_hidden()
        assert len(pending) == 1

        page.go_back()
        page.unroute('**/api/options')
        page.locator('#loadretry').click()
        page.wait_for_function('NAV_READY && CURRENT_VIEW === "builder"')
        assert page.locator('#maps').is_visible()
        assert page.locator('#loaderror').is_hidden()
        assert not errors
        browser.close()


def test_pending_share_restores_exact_recipe_and_screen_via_history(site):
    pw = pytest.importorskip('playwright.sync_api')
    recipe = {**BASE, 'waypoints': POINTS, 'route_recovery': 'home', 'seed': 814}
    code = base64.urlsafe_b64encode(json.dumps(recipe).encode()).decode().rstrip('=')
    with pw.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        pending, errors = [], []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.route('**/api/options', lambda route: pending.append(route))

        with page.expect_request('**/api/options'):
            page.goto(f'{site}/?r={code}&step=world', wait_until='domcontentloaded')
        assert page.evaluate('CURRENT_VIEW') == 'builder'
        tab(page, 'pipeline').click()
        page.locator('#pcourses h2').wait_for()
        assert 'r=' not in page.url
        assert len(pending) == 1
        pending[0].continue_()
        page.wait_for_function('NAV_READY')
        assert page.locator('#pipeline.on').is_visible()

        page.go_back()
        assert page.evaluate('CURRENT_VIEW') == 'builder'
        assert page.evaluate('CUR_SCREEN') == 'world'
        assert page.evaluate('recipe().waypoints') == POINTS
        assert page.evaluate('recipe().route_recovery') == 'home'
        assert page.evaluate('recipe().seed') == 814
        assert not errors
        browser.close()


def test_train_retries_courses_and_loads_full_options_only_for_a_lesson(site):
    pw = pytest.importorskip('playwright.sync_api')
    with pw.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        requests, errors = [], []
        page.on('request', lambda req: requests.append(req.url))
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.route('**/api/courses', lambda route: route.abort())
        page.route('**/api/options', lambda route: route.abort())

        page.goto(site + '/?v=train')
        retry = page.locator('#pcourses').get_by_role('button', name='Retry')
        retry.wait_for()
        assert page.locator('#first_flight h2').is_visible()
        assert not any('/api/options' in url for url in requests)
        page.unroute('**/api/courses')
        retry.click()
        lesson = page.locator('#pbody').get_by_role('link', name='Open track').first
        lesson.wait_for()
        assert not any('/api/options' in url for url in requests)

        lesson.click()
        lesson_retry = page.locator('#pbody').get_by_role('link', name='Retry opening lesson')
        lesson_retry.wait_for()
        assert page.locator('#loaderror').is_hidden()
        page.unroute('**/api/options')
        lesson_retry.click()
        page.locator('#libdetail.on').wait_for()
        assert page.locator('#pipeline.on').is_visible()
        assert not errors
        browser.close()
