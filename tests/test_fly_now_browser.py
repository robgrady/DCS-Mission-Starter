"""Verify that the compact Fly Now picker still produces and restores real recipes."""

import re

import pytest

from test_refactor_browser import site


@pytest.mark.parametrize("width", [390, 1280])
def test_fly_now_search_and_restore_a_valid_setup(site, width):
    pw = pytest.importorskip("playwright.sync_api")
    with pw.sync_playwright() as playwright, playwright.chromium.launch() as browser:
        page = browser.new_page(viewport={"width": width, "height": 844})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.add_init_script("""
            localStorage.setItem('ms_owned', JSON.stringify({
                set: true, aircraft: ['F_16C_50'], maps: [], modules: []
            }));
        """)
        page.goto(site + "/?v=quick")
        quick = page.locator("#quick")
        aircraft = quick.get_by_label("Aircraft", exact=True)
        search = quick.get_by_role("searchbox", name="Search compatible aircraft")
        generate = quick.get_by_role("button", name="Generate & download .miz")
        pw.expect(generate).to_be_disabled()

        quick.get_by_role("button", name=re.compile("^BFM Merge")).click()
        search.fill("hornet")
        pw.expect(quick.locator("#qf_aircraft_status")).to_have_text("No compatible aircraft match this search.")
        search.fill("f16 viper")
        pw.expect(aircraft.locator("optgroup option")).to_have_count(1)
        aircraft.select_option("F_16C_50")
        quick.get_by_role("button", name=re.compile("^Caucasus")).click()
        quick.get_by_role("button", name=re.compile("Defensive perch")).click()
        quick.get_by_role("button", name=re.compile("^Calm")).click()
        pw.expect(generate).to_be_enabled()
        pw.expect(quick.locator("#qf_selection")).to_have_text("BFM Merge · F-16C-50 · Viper · Caucasus")
        pw.expect(aircraft.locator('optgroup[label="Recent aircraft"] option')).to_have_count(1)
        if width == 390:
            dock = generate.bounding_box()
            assert dock and dock["y"] + dock["height"] <= 844
            assert quick.evaluate("panel => panel.scrollWidth === panel.clientWidth")
        recipe = page.evaluate("qfRecipe()")
        assert recipe["bfm_setup"] == "defensive"
        assert recipe["threat_intensity"] == 1

        page.reload()
        pw.expect(generate).to_be_enabled()
        pw.expect(aircraft).to_have_value("F_16C_50")
        pw.expect(aircraft.locator('optgroup[label="Recent aircraft"] option')).to_have_count(1)
        assert page.evaluate("qfRecipe()") == recipe
        assert not errors


def test_fly_now_rejects_stale_saved_pairing_and_keeps_mobile_train_in_bounds(site):
    pw = pytest.importorskip("playwright.sync_api")
    with pw.sync_playwright() as playwright, playwright.chromium.launch() as browser:
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.add_init_script("""
            localStorage.setItem('ss_fly_now_v1', JSON.stringify({
                setup: {type: 'qf_bfm', ac: 'F_16C_50', map: 'removed-map', seed: 12},
                recent: ['missing-aircraft'],
            }));
        """)
        page.goto(site + "/?v=quick")
        quick = page.locator("#quick")
        aircraft = quick.get_by_label("Aircraft", exact=True)
        pw.expect(aircraft.locator("optgroup option").first).to_be_attached()
        pw.expect(quick.get_by_role("button", name="Generate & download .miz")).to_be_disabled()
        pw.expect(aircraft.locator('optgroup[label="Recent aircraft"]')).to_have_count(0)

        page.get_by_role("link", name="DCS SORTIE STARTER").click()
        start = page.get_by_role("link", name="Start your training")
        pw.expect(start).to_be_visible()
        bounds = start.bounding_box()
        assert bounds and bounds["y"] + bounds["height"] <= 844
        start.click()
        pipeline = page.locator("#pipeline")
        pw.expect(pipeline.locator(".unit").first).to_be_visible()
        assert pipeline.evaluate("panel => panel.scrollWidth === panel.clientWidth")
