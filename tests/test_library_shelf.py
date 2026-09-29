"""What reaches the shelf, and what happens when a pack is uploaded.

THREE BUGS THIS FILE EXISTS BECAUSE OF, all reported by Rob in one sitting.

1. *"I haven't installed the pack yet but it is showing up in the library."*
   A track rendered its own Library card straight out of `tracks.json`,
   published or not. Unpublished, it advertised a syllabus whose whole-track
   download answers 409. Published, it sat NEXT TO the pack card that renders
   the same syllabus — and the two are not the same missions: the pack pins
   `seed = 4400 + n` so its printed guide stays true, the track card carries no
   seed at all and the server rolls one per request. Same name, different
   sortie. The shelf now lists a syllabus only as a published pack.

2. *"When I try to select a pack to upload, it doesn't recognize the file
   extension."* `packs.install` has accepted `.sspack` since format 2. The file
   input's `accept` said `.zip,.miz`, so the picker greyed out the one
   extension `scripts/build_pack.py` produces.

3. *"It threw an internal error when I uploaded the pack."* The upload
   SUCCEEDED. `_pack_edit_page` — the review screen the redirect lands on —
   still called `_packs._bundled()`, deleted in v1.80.0 along with bundled
   packs. So every successful upload ended in an AttributeError page for a pack
   that was already installed.

The through-line: three separate places still describing a product that had
moved on. The guards below are aimed at the DESCRIPTION matching the CODE, not
at the strings themselves.
"""
import os
import re
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
UI = (ROOT / "frontend" / "index.html").read_text()
ADMIN = (ROOT / "server" / "admin.py").read_text()
PACKS_PY = (ROOT / "missiongen" / "packs.py").read_text()


def _fn(src, name):
    """The source of a top-level `function name(...)`, brace-matched."""
    m = re.search(rf"function {name}\s*\([^)]*\)\s*{{", src)
    assert m, f"{name} is gone"
    i = m.end() - 1
    depth, j = 0, i
    while j < len(src):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[i:j + 1]
        j += 1
    raise AssertionError(f"unbalanced braces in {name}")


# --------------------------------------------------------------------------- #
# 1. the shelf
# --------------------------------------------------------------------------- #
def test_the_shelf_is_not_built_from_tracks():
    """`libItems` is the shelf. If it reads `OPT.tracks` at all it is back to
    manufacturing a card per track, which is what put an unpublished syllabus
    on the shelf and a duplicate next to every published one."""
    body = _fn(UI, "libItems")
    assert "OPT.tracks" not in body, \
        "libItems is building cards from tracks again"
    assert "'track_'" not in body and '"track_"' not in body, \
        "libItems is minting track_ keys again"


def test_the_track_panel_is_still_reachable():
    """Hiding the CARD must not delete the PANEL. Every link that ever pointed
    at `track_<id>` has to keep opening it — that is the same promise
    `trackOf` made when the loose ride cards came off the shelf."""
    assert "if(k.startsWith('track_')) return openTrack" in UI, \
        "openDetail no longer routes track_ keys to the panel"
    assert "OPT.tracks" in _fn(UI, "openTrack"), \
        "openTrack no longer reads the track out of OPT.tracks"


def test_a_ride_that_belongs_to_a_track_is_still_off_the_shelf():
    """The older half of the same rule. 44 numbered rides scattered through an
    alphabetical grid is not a syllabus."""
    assert "!trackOf(k)" in _fn(UI, "libItems")


@pytest.mark.parametrize("installed", [False, True])
def test_the_payload_offers_the_pack_only_when_it_is_installed(installed,
                                                               monkeypatch):
    """THE SERVER HALF, and only that.

    This was written as `..._appears_once_or_not_at_all` and it was a weak
    guard: it recomputed the shelf in Python, so putting `trackItems()` back
    into `libItems` left it green. It is kept, re-aimed and renamed at what it
    can actually see — that `_pack_templates` mints an entry exactly when a
    pack is on the volume, and that the track survives in the payload either
    way so old `track_<id>` links still open. The shelf itself is guarded by
    the source tests above and by `test_the_real_shelf_lists_no_track_cards`
    below, which reads `libItems()` out of a browser.
    """
    monkeypatch.setenv("PACKS_DATA_DIR", tempfile.mkdtemp())
    import importlib
    from missiongen import packs as _p
    importlib.reload(_p)
    src = ROOT / "packs" / "wk_proud_phantom.sspack"
    if not src.is_file():
        pytest.skip("packs/ not built in this checkout")
    if installed:
        _p.install(src.read_bytes(), "wk_proud_phantom.sspack")

    from fastapi.testclient import TestClient
    import server.app as _app
    importlib.reload(_app)
    o = TestClient(_app.app).get("/api/options").json()

    mine = [k for k in o["templates"] if k.endswith("wk_proud_phantom")]
    assert mine == (["pack_wk_proud_phantom"] if installed else []), mine
    assert "wk_proud_phantom" in o["tracks"], \
        "the track vanished from the payload — every old link now 404s"


# The browser probe, run as a subprocess so the server, the pack store and the
# module reloads live and die with it.
_PROBE = r"""
import json, os, sys, tempfile, threading, time
os.environ["PACKS_DATA_DIR"] = tempfile.mkdtemp()
sys.path[:0] = [%r, %r]
if os.environ.get("INSTALL") == "1":
    from missiongen import packs
    packs.install(open(%r, "rb").read(), "wk_proud_phantom.sspack")
import uvicorn
from server.app import app
srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8793,
                                    log_level="error"))
threading.Thread(target=srv.run, daemon=True).start()
time.sleep(3)
from playwright.sync_api import sync_playwright
JS = ("() => { const ks = libItems().map(x => x.k);"
      " openDetail('track_wk_proud_phantom');"
      " return {keys: ks,"
      "  painted: document.querySelectorAll('#lgrid > *').length,"
      "  zipBtn: !!document.querySelector"
      "            ('#libdetail a[href*=\\'all.zip\\']'),"
      "  deep: document.getElementById('libdetail')"
      "          .classList.contains('on')}; }")
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    pg.goto("http://127.0.0.1:8793/", wait_until="networkidle")
    pg.click("text=Library", timeout=15000); pg.wait_for_timeout(2500)
    out = pg.evaluate(JS)
    b.close()
print("RESULT " + json.dumps(out))
"""


@pytest.mark.parametrize("installed", [False, True])
def test_the_real_shelf_lists_no_track_cards(installed):
    """THE HONEST ONE. A real browser, the real page, `libItems()` as the page
    computes it — because every static guard above reads source text, and
    source text is not what a pilot sees.

    Proven both ways before it was written: with `trackItems()` restored the
    keys come back carrying four `track_` entries, and Proud Phantom appears
    twice once its pack is installed.
    """
    pytest.importorskip("playwright.sync_api")
    src = ROOT / "packs" / "wk_proud_phantom.sspack"
    if not src.is_file():
        pytest.skip("packs/ not built in this checkout")
    import json
    import subprocess
    import sys
    code = _PROBE % (str(ROOT), str(ROOT / "vendor"), str(src))
    env = dict(os.environ, INSTALL="1" if installed else "0")
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env,
                       capture_output=True, text=True, timeout=300)
    line = [x for x in r.stdout.splitlines() if x.startswith("RESULT ")]
    assert line, f"probe produced nothing:\n{r.stdout[-800:]}\n{r.stderr[-1500:]}"
    got = json.loads(line[0][7:])

    assert got["painted"] > 20, f"the grid barely rendered: {got['painted']}"
    assert not [k for k in got["keys"] if k.startswith("track_")], \
        "track cards are back on the shelf"
    mine = [k for k in got["keys"] if k.endswith("wk_proud_phantom")]
    assert mine == (["pack_wk_proud_phantom"] if installed else []), mine
    assert got["deep"], "the track_ deep link no longer opens the panel"
    # `published` is what gates the panel's whole-syllabus button, and it is
    # the only thing that gates it. Offering the button unpublished is how the
    # 502 became a 409 that still looked like a working download.
    assert got["zipBtn"] is installed, (
        "the panel offers a whole-syllabus download for a pack that is not "
        "installed" if got["zipBtn"] else
        "the panel hides the download for a pack that IS installed")


# --------------------------------------------------------------------------- #
# 2. the file picker
# --------------------------------------------------------------------------- #
def test_the_picker_offers_every_extension_the_server_installs():
    """Derived from `packs.install`, NOT a literal list. A hand-written
    `accept` is exactly how `.sspack` — the only extension this product
    produces — came to be missing from it for two releases."""
    accepted = set(re.findall(r"\.(?:miz|zip|sspack)\b", PACKS_PY))
    accepted = {e for e in accepted if e in (".miz", ".zip", ".sspack")}
    assert accepted >= {".miz", ".zip", ".sspack"}, accepted
    m = re.search(r"<input type=file name=file accept='([^']+)'", ADMIN)
    assert m, "the pack upload input lost its accept attribute"
    offered = {x.strip() for x in m.group(1).split(",")}
    assert accepted <= offered, \
        f"the picker greys out {sorted(accepted - offered)}"


def test_the_upload_note_leads_with_the_format_the_product_builds():
    """A note that opens with `.zip` teaches the author to rename his own
    output. `.sspack` is what `scripts/build_pack.py` writes."""
    # the NOTE, not the accept attribute — splitting on the input leaves
    # `,.zip,.miz` in the haystack and the test passes on nothing.
    note = ADMIN.split("accept='.sspack", 1)[1].split("<p class=note>", 1)[1][:500]
    assert note.index(".sspack") < note.index(".zip"), \
        "the note still offers .zip before the format the product builds"


# --------------------------------------------------------------------------- #
# 3. the review page after an upload
# --------------------------------------------------------------------------- #
def test_the_admin_calls_nothing_that_packs_does_not_define():
    """THE SHAPE OF BUG 3. `_pack_edit_page` called `_packs._bundled()` for two
    releases after `_bundled` was deleted, and nothing noticed because no test
    ever loaded the page. Every `_packs.<name>` in admin.py must exist."""
    import missiongen.packs as _p
    # CODE ONLY. This file's own comment explains the bug by naming
    # `_packs._bundled()`, and a scan that cannot tell prose from a call
    # fails forever on its own docstring.
    code = "\n".join(ln for ln in ADMIN.splitlines()
                      if not ln.lstrip().startswith("#"))
    used = set(re.findall(r"\b_packs\.([A-Za-z_][A-Za-z0-9_]*)", code))
    missing = sorted(n for n in used if not hasattr(_p, n))
    assert not missing, f"admin.py calls missiongen.packs.{missing} — gone"


@pytest.mark.parametrize("name", ["wk_proud_phantom.sspack",
                                  "wk_checkout.sspack"])
def test_uploading_a_pack_lands_on_a_page_and_not_an_error(name, monkeypatch):
    """THE BUG ROB HIT, end to end: post the file, FOLLOW THE REDIRECT, and
    read the page. Stopping at the 303 is what let this ship — the upload was
    never the part that broke."""
    src = ROOT / "packs" / name
    if not src.is_file():
        pytest.skip("packs/ not built in this checkout")
    monkeypatch.setenv("PACKS_DATA_DIR", tempfile.mkdtemp())
    monkeypatch.setenv("ADMIN_PASSWORD", "t")
    import importlib
    from missiongen import packs as _p
    importlib.reload(_p)
    import server.admin as _adm
    importlib.reload(_adm)
    import server.app as _app
    importlib.reload(_app)

    from fastapi.testclient import TestClient
    # raise_server_exceptions=True so an unhandled AttributeError surfaces as
    # itself rather than as a 500 the assertion would have to guess at.
    c = TestClient(_app.app, raise_server_exceptions=True)
    c.post("/admin/login", data={"password": "t"}, follow_redirects=True)
    r = c.post("/admin/packs",
               files={"file": (name, src.read_bytes(),
                               "application/octet-stream")},
               data={"pack_id": "", "label": ""}, follow_redirects=True)
    assert r.status_code == 200, r.status_code
    assert "Internal Server Error" not in r.text
    # ...and it is the REVIEW page, with the rides on it — not the pack list
    # bounced back with a flash, which would be a silent failure of its own.
    assert r.text.count("Mission title") == 11, r.text.count("Mission title")


def test_the_review_page_survives_a_pack_that_is_not_installed(monkeypatch):
    """An author bookmarks a pack's edit URL, deletes the pack, comes back.
    That branch had no coverage at all, which is how `_pack_edit_page` shipped
    an AttributeError above it for two releases — nothing ever loaded the page
    in either state."""
    monkeypatch.setenv("PACKS_DATA_DIR", tempfile.mkdtemp())
    monkeypatch.setenv("ADMIN_PASSWORD", "t")
    import importlib
    from missiongen import packs as _p
    importlib.reload(_p)
    import server.admin as _adm
    importlib.reload(_adm)
    import server.app as _app
    importlib.reload(_app)
    from fastapi.testclient import TestClient
    c = TestClient(_app.app, raise_server_exceptions=True)
    c.post("/admin/login", data={"password": "t"}, follow_redirects=True)
    r = c.get("/admin/packs/no_such_pack/edit")
    assert r.status_code == 200, r.status_code
    assert "not installed" in r.text
    assert "Internal Server Error" not in r.text


# --------------------------------------------------------------------------- #
# The waypoint story, told the same way everywhere
# --------------------------------------------------------------------------- #
def test_every_document_tells_the_same_waypoint_story():
    """ROB: "we don't provide a tool to make waypoints but automagically adds
    them." He is right that both halves are true — there is no waypoint
    editor, and the White Knights rides DO carry a flight plan — and the docs
    told only two-thirds of it: strike routes and the opt-in tickbox, with the
    training syllabi added in v1.76.1 and never written into the promise.
    Every place the promise is printed must now name all three cases."""
    docs = {
        "README.md": (ROOT / "README.md").read_text(),
        "docs/ROADMAP.md": (ROOT / "docs" / "ROADMAP.md").read_text(),
        "docs/USER_GUIDE.md": (ROOT / "docs" / "USER_GUIDE.md").read_text(),
        "REPLIT.md": (ROOT / "REPLIT.md").read_text(),
        "scripts/build_guide_pdf.py":
            (ROOT / "scripts" / "build_guide_pdf.py").read_text(),
    }
    for name, text in docs.items():
        low = text.lower()
        assert "automatic waypoints" in low, f"{name} lost the tickbox"
        assert "syllabus" in low and ("training ride" in low
                                      or "training rides" in low), \
            f"{name} still hides that curated training rides carry a route"
        assert "waypoint editor" in low or "no editor" in low or \
            "never place" in low or "never invents" in low or \
            "never given a flight plan" in low or \
            "never handed a flight plan" in low or \
            "no-waypoints rule" in low, \
            f"{name} no longer states that waypoints are not user-authored"


def test_the_footer_credits_the_flight_tester():
    """Rob: "I need to add Tricker for his feedback and help." Half the
    changelog's fixes started as his squawks; the footer says so."""
    assert "Tricker" in UI, "the footer credit is gone"
    readme = (ROOT / "README.md").read_text()
    assert "Tricker" in readme
