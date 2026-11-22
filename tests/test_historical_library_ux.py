"""Historical discovery through the normal browser entry points."""

from pathlib import Path

import pytest

from missiongen.packfmt import mission_facts
from test_refactor_browser import site


@pytest.mark.parametrize('width', [1280, 390])
def test_home_and_library_promote_the_historical_starter(site, width, tmp_path):
    pw = pytest.importorskip('playwright.sync_api')
    with pw.sync_playwright() as runner:
        browser = runner.chromium.launch()
        page = browser.new_page(viewport={'width': width, 'height': 900})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(site)
        page.get_by_role('link', name='Browse historical missions', exact=True).click()
        page.wait_for_function('typeof NAV_READY !== "undefined" && NAV_READY')
        historical = page.locator('[data-lib-shelf="historical"]')
        assert historical.get_attribute('aria-pressed') == 'true'
        assert page.locator('[data-lib-mission="berlin_corridor_transit"]').is_visible()
        assert page.locator('[data-lib-mission="form_close"]').count() == 0
        starter = page.locator('#library-starters .history-starter').first
        assert starter.is_visible()
        assert 'Kandahar' in starter.inner_text()
        page.screenshot(path=str(tmp_path / f'historical-library-{width}.png'))

        dks = 'https://www.digitalkneeboardsimulator.com/'
        page.context.route(dks, lambda route: route.fulfill(status=200, body='DKS planner'))
        handoff = starter.get_by_role('link', name='Download .miz & open DKS')
        with page.expect_popup() as popup, page.expect_download() as download:
            handoff.click()
        popup.value.wait_for_url(dks)
        popup.value.close()
        assert download.value.suggested_filename.endswith('.miz')
        assert mission_facts(Path(download.value.path()).read_bytes()) == {
            'theatre': 'Afghanistan', 'date': '2010-01-01', 'aircraft': 'A-10C',
        }
        assert 'v=library' in page.url

        page.locator('#lfSearch').fill('354th')
        assert starter.is_visible()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
        starter.get_by_role('link', name='Open Kandahar starter in Builder').click()
        page.wait_for_function('typeof NAV_READY !== "undefined" && NAV_READY && CURRENT_VIEW === "builder"')
        recipe = page.evaluate('recipe()')
        assert recipe['mission_date'] == '2010-01-01'
        assert recipe['map'] == 'afghanistan' and recipe['slots'] == 2
        assert recipe['bb_historical_airspace'] and not recipe['player_arm']
        assert not errors
        browser.close()


def test_mission_link_opens_detail_and_sources_return_to_library(site):
    pw = pytest.importorskip('playwright.sync_api')
    with pw.sync_playwright() as runner:
        browser = runner.chromium.launch()
        page = browser.new_page()
        page.goto(site + '/?v=library&mission=berlin_corridor_transit')
        page.wait_for_selector('#libdetail.on')
        assert 'Berlin' in page.locator('#libdetail h2').inner_text()
        assert page.locator('#dHistorical').inner_text()
        page.get_by_role('button', name='Close details', exact=True).click()
        assert page.locator('#libdetail').is_hidden()
        page.goto(site + '/api/historical-library')
        page.get_by_role('link', name='Back to Library').click()
        page.wait_for_function('typeof NAV_READY !== "undefined" && NAV_READY')
        assert page.locator('[data-lib-shelf="historical"]').get_attribute('aria-pressed') == 'true'
        assert page.locator('#library').is_visible()
        browser.close()


def test_balad_starter_search_and_builder_state(site):
    pw = pytest.importorskip('playwright.sync_api')
    with pw.sync_playwright() as runner:
        browser = runner.chromium.launch()
        page = browser.new_page(viewport={'width': 390, 'height': 900})
        page.goto(site + '/?v=library')
        page.wait_for_function('typeof NAV_READY !== "undefined" && NAV_READY')
        page.locator('#lfSearch').fill('Balad')
        card = page.locator('#library-starters .history-starter')
        assert card.count() == 1
        assert card.get_by_role('heading', name='Balad: 14th EFS F-16 planning starter').is_visible()
        assert 'DCS Iraq map and F-16C Viper module' in card.inner_text()
        assert card.get_by_role('link', name='View historical sources').get_attribute('href').endswith(
            '#oif-balad-al-asad-2007-01-28'
        )
        assert card.get_by_role('link', name='Download .miz & open DKS').get_attribute('data-dks-download').startswith('/api/dl?r=')
        card.get_by_role('link', name='Open Balad Airbase starter in Builder').click()
        page.wait_for_function('typeof NAV_READY !== "undefined" && NAV_READY && CURRENT_VIEW === "builder"')
        recipe = page.evaluate('recipe()')
        assert (recipe['map'], recipe['home_airbase'], recipe['aircraft']) == ('iraq', 'Balad Airbase', 'F_16C_50')
        assert (recipe['mission_date'], recipe['slots'], recipe['player_slot']) == ('2007-01-28', 2, 'client')
        assert recipe['start'] == 'cold' and not recipe['player_arm']
        browser.close()
