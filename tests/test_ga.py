"""Google Analytics: on the page, off by default, and honestly described.

Three separate promises here, and each one has a way of quietly breaking.

  1. **It ships off.** The measurement id comes from the environment, so a
     self-hosted copy of this app makes no third-party request and reports into
     nobody's property. Hard-coding the id into index.html would silently turn
     every unzipped folder into a data source for our account. This is the
     guard that stops a "simplification" doing that.

  2. **It is on every page, not just the front one.** The roadmap, the what's
     new page, the sources page and the 404 are all real pages people land on.

  3. **The footer tells the truth.** The site used to promise "No IP address,
     no account, no name — nothing that says who you are", full stop, with an
     off-switch and Do Not Track honored. Google Analytics collects an IP, a
     user agent and device details, sets cookies, and reads neither the switch
     nor DNT. Running it under the old wording would put a false statement on
     the privacy notice, which is the worst place this product could have one —
     and v1.57.0's own release notes had specifically celebrated removing
     Google Fonts so the page "no longer tells Google your IP address just to
     draw letters".

     Rob's call was: run it always, and rewrite the footer to match. So these
     guards hold the footer to the second half of that bargain.
"""
import importlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "frontend" / "index.html"
GOOD_ID = "G-B406V24KN5"


@pytest.fixture
def ga_mod(monkeypatch):
    """The module, reloaded so the environment is read fresh each time."""
    def _load(value):
        if value is None:
            monkeypatch.delenv("GA_MEASUREMENT_ID", raising=False)
        else:
            monkeypatch.setenv("GA_MEASUREMENT_ID", value)
        from server import ga
        return importlib.reload(ga)
    return _load


# --------------------------------------------------------------------------- #
# 1. It ships off
# --------------------------------------------------------------------------- #
def test_no_measurement_id_is_hardcoded_in_the_page():
    """A self-hosted copy must not report into our property.

    This app is distributed as a zip and REPLIT.md is a brief for re-hosting
    it. An id in the page source would mean every copy anyone runs sends its
    visitors to our Google account — our numbers become 'everyone who ever ran
    this', and their users are measured by a party they have never heard of.
    """
    src = INDEX.read_text()
    ids = re.findall(r"G-[A-Z0-9]{4,20}", src)
    assert not ids, f"index.html carries a measurement id: {ids}"
    assert "googletagmanager.com" not in src, (
        "index.html loads gtag.js directly; it must come from server/ga.py so "
        "an unconfigured deployment makes no third-party request")


def test_an_unconfigured_deployment_emits_no_tag(ga_mod):
    ga = ga_mod(None)
    html = "<html><head></head><body>x</body></html>"
    assert ga.inject(html) == html
    assert ga.snippet() == ""
    assert ga.measurement_id() == ""


@pytest.mark.parametrize("bad", [
    "not-an-id", "UA-12345-1", "G-", "g-b406v24kn5", "",
    "G-ABC123'; alert(1); //", 'G-ABC" onload="x',
    "G-ABC123 G-DEF456",
])
def test_a_malformed_id_is_refused_rather_than_interpolated(ga_mod, bad):
    """The id goes inside a <script> block. It comes from an operator's
    environment rather than a user, so this is not the front line of anything —
    but a quote in that value would be an injection in the most literal sense,
    and a typo would produce broken JavaScript that takes the page down."""
    ga = ga_mod(bad)
    assert ga.measurement_id() == "", bad
    assert ga.snippet() == "", bad


def test_a_good_id_produces_the_tag_google_asks_for(ga_mod):
    ga = ga_mod(GOOD_ID)
    tag = ga.snippet()
    assert f'src="https://www.googletagmanager.com/gtag/js?id={GOOD_ID}"' in tag
    assert "async" in tag
    assert f"gtag('config', '{GOOD_ID}')" in tag
    assert "window.dataLayer = window.dataLayer || []" in tag


def test_the_tag_goes_in_the_head(ga_mod):
    ga = ga_mod(GOOD_ID)
    out = ga.inject("<html><head><title>t</title></head><body>b</body></html>")
    assert out.index("gtag/js") < out.index("</head>")


def test_injection_is_idempotent(ga_mod):
    """Every HTML response runs through the injector and one of them is already
    passed through a second transform. A double injection would load gtag.js
    twice and double every page view — a reporting error that looks like
    growth."""
    ga = ga_mod(GOOD_ID)
    once = ga.inject("<html><head></head><body></body></html>")
    assert ga.inject(once) == once
    assert once.count("googletagmanager.com") == 1


# --------------------------------------------------------------------------- #
# 2. Every page, not just the front one
# --------------------------------------------------------------------------- #
def test_every_html_response_runs_through_the_injector():
    """Sources, roadmap, what's new and the 404 are real landing pages.

    Read out of the source rather than by hitting each route, because the point
    is that NO HTML response is left out — a new page added next year should
    fail this line, not slip through because nobody wrote a route test for it.
    """
    src = (ROOT / "server" / "app.py").read_text()
    responses = re.findall(r"HTMLResponse\(([^\n]*)", src)
    assert responses, "no HTMLResponse calls found — has app.py moved?"
    for r in responses:
        assert "_ga.inject" in r, (
            f"an HTML response does not carry the analytics tag: {r.strip()}")
    # and the bare `return FRONTEND.read_text()` path, which is an HTMLResponse
    # by decorator rather than by call
    assert "_ga.inject(FRONTEND.read_text())" in src, (
        "the front page itself is served without the tag")


def test_fly_config_sets_the_id_for_our_deployment_only():
    fly = (ROOT / "fly.toml").read_text()
    assert f"GA_MEASUREMENT_ID = '{GOOD_ID}'" in fly, (
        "the deployment does not set a measurement id, so the live site has "
        "no analytics at all")


# --------------------------------------------------------------------------- #
# 3. The footer tells the truth
# --------------------------------------------------------------------------- #
def _footer():
    src = INDEX.read_text()
    i = src.index("<footer")
    return src[i:src.index("</footer>", i)]


def test_the_footer_names_google_analytics():
    f = _footer()
    assert "Google Analytics" in f, (
        "the site runs Google Analytics and the privacy notice does not say so")


def test_the_footer_no_longer_makes_a_promise_the_page_breaks():
    """The old text said "No IP address, no account, no name" as a statement
    about the site. It is still true of OUR counting and it is not true of the
    page as a whole. The claim must be attached to the thing it describes."""
    f = _footer()
    assert "IP address" in f
    # the no-IP claim and the word "ours"/"Ours" must be in the same breath
    i = f.index("No IP address")
    window = f[max(0, i - 400):i]
    assert "Ours" in window or "our " in window.lower(), (
        "the no-IP claim is not scoped to our own counting, so it reads as a "
        "statement about the whole page — which now includes Google")
    assert "IP address" in f.split("Google Analytics", 1)[1], (
        "the footer names Google Analytics without saying that Google receives "
        "an IP address")


def test_the_footer_says_the_off_switch_does_not_cover_google():
    f = _footer()
    assert re.search(r"does <b>not</b> turn that off|not turn that off", f), (
        "the page has an analytics off-switch and does not say that it leaves "
        "Google Analytics running — a switch that lies about what it did is "
        "worse than no switch")


def test_the_off_switch_label_says_which_counter_it_governs():
    """`renderPrivacy` writes the live state line next to the switch. "Counting
    is off" unqualified, with GA still running, is the same false statement in
    a second place."""
    src = INDEX.read_text()
    i = src.index("function renderPrivacy(")
    body = src[i:i + 1400]
    assert "Google Analytics" in body, (
        "the switch's own status line never mentions Google Analytics")
    for phrase in ("<b>Our</b> counting is <b>on</b>",
                   "<b>Our</b> counting is <b>off</b>"):
        assert phrase in body, f"the status line is unscoped: {phrase!r} missing"

    # THE DO NOT TRACK BRANCH, SEPARATELY — and it is the one that matters most.
    # A visitor who has switched DNT on has said, explicitly, that they do not
    # want to be tracked. Telling that person "we're counting nothing from this
    # browser" while Google Analytics runs is the most misleading sentence the
    # page could carry, and it is aimed at exactly the reader who cares.
    dnt_branch = body[body.index("dnt"):body.index("dnt") + 500]
    assert "Do Not Track" in dnt_branch
    assert "counting nothing from this browser" not in dnt_branch, (
        "a Do Not Track visitor is told nothing is counted, while Google "
        "Analytics — which does not read that signal — is still running")
    assert "our" in dnt_branch.lower() and "Google" in dnt_branch, (
        "the Do Not Track line does not say which counter it is talking about")


def test_do_not_track_is_still_honoured_for_our_own_counting():
    """GA does not read DNT and we are not pretending otherwise. What must not
    happen is our OWN counting quietly losing the check while attention was on
    Google."""
    src = INDEX.read_text()
    assert "function dntOn()" in src
    i = src.index("function visitorId()")
    assert "dntOn()" in src[i:i + 400], (
        "visitorId no longer checks Do Not Track")


# --------------------------------------------------------------------------- #
# 4. The events
# --------------------------------------------------------------------------- #
def test_the_ga_helper_cannot_break_the_app():
    """gtag is absent on any deployment without an id, and absent for every
    visitor running a content blocker. A missing analytics tag must never be
    able to stop a button working."""
    src = INDEX.read_text()
    i = src.index("function ga(name, params)")
    body = src[i:i + 500]
    assert "typeof gtag !== 'function'" in body, (
        "ga() calls gtag without checking it exists")
    assert "try{" in body and "catch" in body, "ga() is not exception-safe"


@pytest.mark.parametrize("event", [
    "generate", "generate_error", "view_change", "library_open",
    "track_open", "contact_open", "kneeboard_download",
])
def test_the_behaviours_that_matter_are_instrumented(event):
    src = INDEX.read_text() + '\n' + (INDEX.parent / 'assets/mission-results.js').read_text()
    assert f"ga('{event}'" in src, f"nothing reports {event!r} to GA"


def test_generate_reports_which_door_was_used():
    """Builder, Library and Fly Now are three products sharing one endpoint.
    A generate count that cannot tell them apart answers no question anyone
    has."""
    src = INDEX.read_text()
    results = (INDEX.parent / 'assets/mission-results.js').read_text()
    assert "ga('generate',{source})" in results
    assert "source=options.source||'builder'" in results
    assert "{source:'quick', rc}" in src
    assert "{source:'library', rc:recipe()" in src


def test_the_view_change_event_exists_because_ga_cannot_see_it_otherwise():
    """GA4's automatic page_view fires once, on load. This app never navigates
    again — Library, Fly Now and Builder are the same document — so without an
    explicit event two of the three doors are invisible in the reports."""
    src = INDEX.read_text()
    i = src.index("function showView(v,")
    assert "ga('view_change', {view: v})" in src[i:i + 600]


def test_the_old_track_helper_still_feeds_both_ledgers():
    src = INDEX.read_text()
    i = src.index("function track(ev)")
    body = src[i:i + 700]
    assert "/api/ev" in body, "track() stopped feeding our own counter"
    assert "ga(ev)" in body, "track() does not forward to GA"


def test_the_recipe_is_not_sent_to_google():
    """The server-side ledger already records map, aircraft and mission type
    against the recipe. Sending the same facts to a second system is how two
    numbers start disagreeing, and it widens what a third party learns about a
    user for no analytical gain."""
    src = INDEX.read_text()
    i = src.index("function ga(name, params)")
    for bad in ("gtag('event', 'generate', rc", "map: rc.", "aircraft: rc."):
        assert bad not in src, f"the recipe is being sent to GA: {bad}"


# --------------------------------------------------------------------------- #
# 5. The honest one: a real browser, a real server
# --------------------------------------------------------------------------- #
_PROBE = r"""
import json, os, sys, threading, time
sys.path[:0] = [%r, %r]
os.environ["GA_MEASUREMENT_ID"] = %r
import uvicorn
from server.app import app
srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8797,
                                    log_level="error"))
threading.Thread(target=srv.run, daemon=True).start()
time.sleep(3)
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    hits = []
    # gtag.js is a real network request to Google. Block it so the test does
    # not depend on the internet, and record that the page asked for it.
    pg.route("**://www.googletagmanager.com/**",
             lambda route: (hits.append(route.request.url), route.abort()))
    pg.goto("http://127.0.0.1:8797/", wait_until="domcontentloaded")
    pg.wait_for_timeout(1500)
    out = pg.evaluate("() => ({dl: Array.isArray(window.dataLayer),"
                      "  n: (window.dataLayer||[]).length,"
                      "  gaFn: typeof ga === 'function',"
                      "  survives: (function(){ try { ga('probe_event');"
                      "      return true; } catch(e){ return false; } })()})")
    b.close()
print("RESULT " + json.dumps({**out, "hits": hits}))
"""


def test_the_tag_is_really_requested_and_the_app_survives_it_failing():
    """Everything above reads source text, and source text is not what a
    browser does. This loads the real page off the real server with gtag.js
    BLOCKED — which is what an ad blocker does to most of our visitors — and
    checks two things: the page did ask Google for the script, and with the
    script never arriving the app's own ga() helper still runs without
    throwing."""
    pytest.importorskip("playwright.sync_api")
    code = _PROBE % (str(ROOT), str(ROOT / "vendor"), GOOD_ID)
    r = subprocess.run([sys.executable, "-c", code], capture_output=True,
                       text=True, timeout=180, cwd=str(ROOT))
    line = next((l for l in r.stdout.splitlines() if l.startswith("RESULT ")),
                None)
    assert line, f"probe produced nothing:\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}"
    out = json.loads(line[len("RESULT "):])
    assert out["hits"], "the served page never requested gtag.js"
    assert GOOD_ID in out["hits"][0], out["hits"]
    assert out["dl"], "window.dataLayer was never created"
    assert out["n"] >= 2, f"the config calls did not run (dataLayer={out['n']})"
    assert out["gaFn"], "the app's ga() helper is missing"
    assert out["survives"], (
        "ga() throws when gtag.js is blocked — an ad blocker would break the "
        "app for the visitor running it")
