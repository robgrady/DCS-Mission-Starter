#!/usr/bin/env python3
"""Capture screen-by-screen wizard screenshots for the user guide (section-nav UI).
Requires the app running (default http://localhost:8360). Writes docs/img/."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8360"
OUT = Path(__file__).parent.parent / "docs" / "img"
OUT.mkdir(parents=True, exist_ok=True)


def show(page, key):
    page.evaluate(f"showScreen('{key}')")
    page.wait_for_timeout(350)


with sync_playwright() as pw:
    browser = pw.chromium.launch(
        executable_path="/opt/pw-browsers/chromium"
        if Path("/opt/pw-browsers/chromium").exists() else None)
    page = browser.new_page(viewport={"width": 1380, "height": 900},
                            device_scale_factor=2)
    page.goto(BASE)
    page.wait_for_selector("#maps .card")
    page.wait_for_timeout(600)

    # a good showcase scenario: modern NTTR out of Nellis
    page.evaluate("""() => {
        document.querySelector('#eras .card[data-k=modern]').click();
        document.querySelector('#maps .card[data-k=nevada]').click();
    }""")
    page.wait_for_timeout(500)
    page.evaluate("""() => {
        const h = document.getElementById('home');
        const o = [...h.options].find(x => x.value === 'Nellis');
        if (o) { h.value = 'Nellis'; h.dispatchEvent(new Event('change')); }
    }""")
    page.wait_for_timeout(300)

    # hero — full chrome on the Theater screen (rail + screen + pinned preview bar)
    show(page, "theater")
    page.screenshot(path=str(OUT / "hero.png"),
                    clip={"x": 0, "y": 0, "width": 1380, "height": 820})
    page.locator("main").screenshot(path=str(OUT / "theater.png"))

    # Airfields — Compose mode, pre-populated from the Red Flag template
    show(page, "airfields")
    page.evaluate("""() => {
        const r = document.querySelector('input[name=dmode][value=compose]');
        r.checked = true; r.dispatchEvent(new Event('change'));
    }""")
    page.wait_for_timeout(300)
    page.evaluate("""() => {
        const s = document.getElementById('dress_theme');
        const o = [...s.options].find(x => x.text.includes('Red Flag'));
        if (o) { s.value = o.value; s.dispatchEvent(new Event('change')); }
    }""")
    page.wait_for_timeout(300)
    page.locator("main").screenshot(path=str(OUT / "airfields.png"))

    # Threats
    show(page, "threats")
    page.locator("main").screenshot(path=str(OUT / "threats.png"))

    # Review & generate
    show(page, "review")
    page.locator("main").screenshot(path=str(OUT / "review.png"))

    # Carrier — needs a coastal map + carrier home base
    page.evaluate("""() => {
        document.querySelector('#eras .card[data-k=modern]').click();
        document.querySelector('#maps .card[data-k=syria]').click();
    }""")
    page.wait_for_timeout(500)
    page.evaluate("""() => {
        const h = document.getElementById('home');
        const o = [...h.options].find(x => x.value === 'CARRIER');
        if (o) { h.value = 'CARRIER'; h.dispatchEvent(new Event('change')); }
    }""")
    page.wait_for_timeout(400)
    page.evaluate("""() => {
        const s = document.getElementById('carrier_hull');
        if ([...s.options].some(o => o.value === 'cvn_71')) {
            s.value = 'cvn_71'; s.dispatchEvent(new Event('change'));
        }
        document.getElementById('carrier_cap').checked = true;
        document.getElementById('carrier_aew').checked = true;
    }""")
    page.wait_for_timeout(300)
    show(page, "carrier")
    page.locator("main").screenshot(path=str(OUT / "carrier.png"))

    browser.close()
print("screenshots ->", OUT)
