#!/usr/bin/env python3
"""Capture the UI screenshots used by the user guide. Writes docs/img/.

    python3 scripts/capture_screenshots.py [http://localhost:8360]

WHY THIS IS DRIVEN OFF THE LIVE UI
----------------------------------
The previous version hardcoded the wizard's screen keys and its entry path. Both
moved: v1.19 put a landing page in front of the Builder, and v1.46 renamed and
re-cut the screens ("threats" -> "opposition", "carrier" became a block on the
Flight screen). The script did not move with them, so it timed out on a selector
that no longer resolved — and because nothing ran it, nobody found out. The
screenshots in the guide silently described an eight-step wizard that had not
existed for three releases.

So: enter through the real navigation, read `SCREENS` out of the running page,
and fail loudly if a screen this guide documents has disappeared. A rename now
breaks the release instead of quietly freezing the pictures.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8360"
OUT = Path(__file__).parent.parent / "docs" / "img"
OUT.mkdir(parents=True, exist_ok=True)

# Screen key -> output file, for the shots the guide lays out by name. Keys are
# checked against the running app's SCREENS table before anything is captured.
SCREEN_SHOTS = {
    "theater": "theater.png",
    "opposition": "threats.png",     # guide filename predates the rename
    "airfields": "airfields.png",
    "review": "review.png",
}
# The carrier deck is a conditional block on the Flight screen (it only appears
# when you are actually flying off a boat), so it needs its own scenario rather
# than a plain screen shot.
CARRIER_SHOT = ("flight", "carrier.png")


def enter_builder(page):
    """Click through the landing page. The wizard is not on screen at load."""
    page.wait_for_function('OPT !== null && NAV_READY', timeout=30000)
    page.wait_for_selector("text=Builder", timeout=15000)
    page.click("text=Builder")
    page.wait_for_function(
        "() => { const e = document.getElementById('maps');"
        " return e && !!e.offsetParent; }", timeout=15000)
    page.wait_for_timeout(400)


def show(page, key):
    page.evaluate(f"showScreen({key!r})")
    page.wait_for_timeout(400)


def dismiss_banners(page):
    """Close the "learn more" strip. It is correct product behavior and wrong
    in a manual — it sits across the top of every shot explaining the screen the
    caption underneath is already explaining."""
    # Also drop the pinned chrome. A full-height element screenshot is stitched
    # from several viewports, and anything `position: fixed` re-renders in EVERY
    # slice — so the nav bar and the Back/Next bar print across the middle of a
    # tall screen, clipping the section headings underneath them.
    page.evaluate("""() => {
        document.querySelectorAll('#whatbanner, .banner, [id$=banner]')
            .forEach(b => b.style.display = 'none');
        document.querySelectorAll('*').forEach(e => {
            const s = getComputedStyle(e);
            if (s.position === 'fixed' || s.position === 'sticky')
                e.style.visibility = 'hidden';
        });
        window.scrollTo(0, 0);
        document.querySelectorAll('button, .x, .close').forEach(b => {
            if (b.textContent.trim() === '\u00d7') b.click();
        });
    }""")
    page.wait_for_timeout(250)


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path="/opt/pw-browsers/chromium"
            if Path("/opt/pw-browsers/chromium").exists() else None)
        page = browser.new_page(viewport={"width": 1380, "height": 900},
                                device_scale_factor=2)
        page.goto(BASE)

        # Landing shots, before we go anywhere.
        page.wait_for_timeout(1200)
        page.screenshot(path=str(OUT / "quick.png"),
                        clip={"x": 0, "y": 0, "width": 1380, "height": 820})

        enter_builder(page)
        dismiss_banners(page)

        keys = page.evaluate("() => SCREENS.map(s => s.key)")
        missing = [k for k in SCREEN_SHOTS if k not in keys]
        if missing:
            raise SystemExit(
                f"ERROR: the guide documents screens that no longer exist: "
                f"{missing}. The app now has {keys}. Update SCREEN_SHOTS and "
                f"the guide text together — do not just delete the entry.")

        # A showcase scenario: modern Nevada out of Nellis.
        page.evaluate("""() => {
            document.querySelector('#eras .card[data-k=modern]')?.click();
            document.querySelector('#maps .card[data-k=nevada]')?.click();
        }""")
        page.wait_for_timeout(600)
        page.evaluate("""() => {
            const h = document.getElementById('home');
            const o = h && [...h.options].find(x => x.value === 'Nellis');
            if (o) { h.value = 'Nellis'; h.dispatchEvent(new Event('change')); }
        }""")
        page.wait_for_timeout(400)

        show(page, "theater")
        page.screenshot(path=str(OUT / "hero.png"),
                        clip={"x": 0, "y": 0, "width": 1380, "height": 820})

        def shot(key, fname):
            show(page, key)
            dismiss_banners(page)
            target = page.locator("main")
            (target if target.count() else page).screenshot(path=str(OUT / fname))

        for key, fname in SCREEN_SHOTS.items():
            shot(key, fname)

        # Carrier: needs a coastal map and a deck to fly from, or the panel the
        # shot exists to show is (correctly) not rendered at all.
        page.evaluate("""() => {
            document.querySelector('#maps .card[data-k=syria]')?.click();
        }""")
        page.wait_for_timeout(600)
        page.evaluate("""() => {
            const cb = document.getElementById('bb_carrier');
            if (cb && !cb.checked) { cb.checked = true; cb.dispatchEvent(new Event('change')); }
        }""")
        page.wait_for_timeout(400)
        page.evaluate("""() => {
            const h = document.getElementById('home');
            const o = h && [...h.options].find(x => x.value === 'CARRIER');
            if (o) { h.value = 'CARRIER'; h.dispatchEvent(new Event('change')); }
            const a = document.getElementById('aircraft');
            const ao = a && [...a.options].find(x => x.value === 'FA_18C_hornet');
            if (ao) { a.value = 'FA_18C_hornet'; a.dispatchEvent(new Event('change')); }
        }""")
        page.wait_for_timeout(600)
        if not page.evaluate("() => !!document.getElementById('carrierstep')?.offsetParent"):
            show(page, CARRIER_SHOT[0])
        if not page.evaluate("() => !!document.getElementById('carrierstep')?.offsetParent"):
            raise SystemExit(
                "ERROR: the carrier deck panel never became visible, so "
                "carrier.png would document a screen without a carrier on it. "
                "Check STEP_COND.carrierstep in frontend/index.html.")
        shot(*CARRIER_SHOT)

        # Airfields, broken into readable crops rather than one long shot.
        show(page, "airfields")

        def clip_ids(ids, out, pad=10, max_h=None):
            box = page.evaluate(
                """(ids)=>{const rs=ids.map(i=>document.getElementById(i))
                     .filter(Boolean).filter(e=>e.offsetParent)
                     .map(e=>e.getBoundingClientRect());
                   if(!rs.length) return null;
                   const top=Math.min(...rs.map(r=>r.top)),
                         left=Math.min(...rs.map(r=>r.left)),
                         right=Math.max(...rs.map(r=>r.right)),
                         bot=Math.max(...rs.map(r=>r.bottom));
                   return {x:left, y:top, w:right-left, h:bot-top};}""", ids)
            if not box or box["w"] < 20 or box["h"] < 20:
                print(f"  ! {out}: {ids} not visible — skipped")
                return
            h = box["h"] if not max_h else min(box["h"], max_h)
            page.screenshot(path=str(OUT / out), clip={
                "x": max(0, box["x"] - pad), "y": max(0, box["y"] - pad),
                "width": box["w"] + 2 * pad, "height": h + 2 * pad})

        page.evaluate("""() => {
            const r = document.querySelector('input[name=dmode][value=theme]');
            if (r) { r.checked = true; r.dispatchEvent(new Event('change')); }
        }""")
        page.wait_for_timeout(300)
        clip_ids(["dress_mode_row", "theme_controls"], "airfields_mode.png")

        page.evaluate("""() => {
            const r = document.querySelector('input[name=dmode][value=compose]');
            if (r) { r.checked = true; r.dispatchEvent(new Event('change')); }
        }""")
        page.wait_for_timeout(400)
        clip_ids(["composer"], "airfields_compose.png", max_h=360)

        page.evaluate("""() => {
            const r = document.querySelector('input[name=dmode][value=theme]');
            if (r) { r.checked = true; r.dispatchEvent(new Event('change')); }
        }""")
        page.wait_for_timeout(300)
        clip_ids(["dress_place_row", "dress_obj_row"], "airfields_place.png")

        browser.close()
    print("screenshots ->", OUT)


if __name__ == "__main__":
    main()
