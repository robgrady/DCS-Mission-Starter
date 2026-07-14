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

    # Airfields — broken into three focused, readable crops instead of one long shot.
    def clip_ids(ids, out, pad=10, max_h=None):
        """Screenshot the bounding union of the given element ids (CSS px)."""
        box = page.evaluate(
            """(ids)=>{const rs=ids.map(i=>document.getElementById(i))
                 .filter(Boolean).map(e=>e.getBoundingClientRect());
               if(!rs.length) return null;
               const top=Math.min(...rs.map(r=>r.top)), left=Math.min(...rs.map(r=>r.left)),
                     right=Math.max(...rs.map(r=>r.right)), bot=Math.max(...rs.map(r=>r.bottom));
               return {x:left, y:top, w:right-left, h:bot-top};}""", ids)
        if not box:
            return
        h = box["h"] if not max_h else min(box["h"], max_h)
        page.screenshot(path=str(OUT / out), clip={
            "x": max(0, box["x"]-pad), "y": max(0, box["y"]-pad),
            "width": box["w"]+2*pad, "height": h+2*pad})

    show(page, "airfields")
    # (A) the two ways to fill — theme mode: the mode toggle + theme dropdown + fill
    page.evaluate("""() => {
        const r = document.querySelector('input[name=dmode][value=theme]');
        r.checked = true; r.dispatchEvent(new Event('change'));
    }""")
    page.wait_for_timeout(300)
    clip_ids(["dress_mode_row", "theme_controls"], "airfields_mode.png")
    # (B) the Ramp Composer — compose mode, pre-populated from Red Flag (top only)
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
    clip_ids(["composer"], "airfields_compose.png", max_h=360)   # banner + Blue fighters/heavies
    # (C) placement mode + object toggles
    clip_ids(["dress_place_row", "dress_obj_row"], "airfields_place.png")

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
