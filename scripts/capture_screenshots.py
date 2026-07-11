#!/usr/bin/env python3
"""Capture step-by-step wizard screenshots for the user guide.
Requires the app running (default http://localhost:8360). Writes docs/img/."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8360"
OUT = Path(__file__).parent.parent / "docs" / "img"
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium"
                                 if Path("/opt/pw-browsers/chromium").exists() else None)
    page = browser.new_page(viewport={"width": 1440, "height": 1000},
                            device_scale_factor=2)
    page.goto(BASE)
    page.wait_for_selector("#maps .card")
    page.wait_for_timeout(600)

    # hero: full wizard top
    page.screenshot(path=str(OUT / "hero.png"),
                    clip={"x": 0, "y": 0, "width": 1440, "height": 700})

    steps = page.locator(".step")

    # step 1+2: map & era cards (selected state)
    steps.nth(0).screenshot(path=str(OUT / "step1_map.png"))
    steps.nth(1).screenshot(path=str(OUT / "step2_era.png"))

    # step 3: coalition / basing / aircraft
    steps.nth(2).screenshot(path=str(OUT / "step3_basing.png"))

    # step 4: building blocks — check carrier so the panel appears
    page.check("#bb_carrier")
    page.wait_for_timeout(400)
    steps.nth(3).screenshot(path=str(OUT / "step4_blocks.png"))

    # step 4b: carrier deck configuration — era gate means the Roosevelt needs
    # a modern era, so switch to Syria/Modern first
    page.evaluate("""() => {
        document.querySelector('#maps .card[data-k="syria"]').click();
        document.querySelector('#eras .card[data-k="modern"]').click();
    }""")
    page.wait_for_timeout(400)
    page.select_option("#carrier_hull", "cvn_71")
    page.check("#carrier_cap")
    page.check("#carrier_aew")
    page.wait_for_timeout(300)
    page.locator("#carrierstep").screenshot(path=str(OUT / "step5_carrier.png"))

    # step 5: template pack cards
    steps.nth(5).screenshot(path=str(OUT / "step6_template.png"))

    # generate bar
    page.locator(".genbar").screenshot(path=str(OUT / "step7_generate.png"))

    browser.close()
print("screenshots ->", OUT)
