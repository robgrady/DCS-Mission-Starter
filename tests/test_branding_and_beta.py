"""A mission only carries a logo somebody chose to put there. And the site says
it is a beta.

Rob's report: "the Authentic Media Logo was showing up. I have not added that
back in." He was right, and the reason is a default nobody picked. The splash
logic read: active sponsor → sponsor logo; **no sponsor → the shipped Authentic
Media wordmark**. The house logo was the FALLBACK, so an empty sponsor store —
which is exactly what a fresh Fly deploy has, since the store lives on a volume
— branded every mission generated.

"Nothing configured" should mean nothing, not "our own logo". It is opt-in now.
"""
import re
import zipfile
from pathlib import Path

import pytest

from missiongen import Recipe, generate, sponsors

ROOT = Path(__file__).resolve().parent.parent
HTML = (ROOT / "frontend" / "index.html").read_text()


# --- the logo ---------------------------------------------------------------

def test_the_house_logo_is_off_by_default():
    """The default on a fresh install, which is the state that shipped it."""
    assert sponsors._default_manifest().get("house_brand") is False, \
        "the shipped default puts our own wordmark on everyone's missions"


def test_an_older_manifest_defaults_to_off(tmp_path, monkeypatch):
    """A store written before this key existed must not inherit 'on'. The live
    volume already has one, so this is the case that actually matters."""
    manifest = tmp_path / "sponsors.json"
    manifest.write_text('{"active": null, "branding_enabled": true, "sponsors": {}}')
    monkeypatch.setattr(sponsors, "_MANIFEST", manifest)
    assert sponsors._load().get("house_brand") is False


def test_a_mission_carries_no_logo_with_nothing_configured(tmp_path):
    """The end-to-end version of Rob's report."""
    out = str(tmp_path / "b.miz")
    res = generate(Recipe.from_dict(dict(
        map="syria", era="modern", aircraft="FA_18C_hornet",
        bb_ambient=False, seed=1)), out)
    if sponsors.active_splash() or sponsors.house_brand_enabled():
        pytest.skip("a sponsor or the house logo is configured on this machine")
    assert not res["stats"].get("branding"), \
        f"a logo was baked in with nothing configured: {res['stats']['branding']}"
    baked = [n for n in zipfile.ZipFile(out).namelist()
             if "brand" in n.lower() or "authentic" in n.lower()]
    assert not baked, f"brand art shipped inside the .miz: {baked}"


def test_the_house_logo_still_works_when_asked_for(monkeypatch, tmp_path):
    """Off by default is not the same as removed. Rob may well want it back on,
    and the switch has to actually do something."""
    monkeypatch.setattr(sponsors, "house_brand_enabled", lambda: True)
    monkeypatch.setattr(sponsors, "active_splash", lambda: None)
    monkeypatch.setattr(sponsors, "branding_enabled", lambda: True)
    out = str(tmp_path / "h.miz")
    res = generate(Recipe.from_dict(dict(
        map="syria", era="modern", aircraft="FA_18C_hornet",
        bb_ambient=False, seed=1)), out)
    assert res["stats"].get("branding") == "house", \
        "turning the house logo on did not put it in the mission"


def test_the_admin_can_switch_it(tmp_path, monkeypatch):
    monkeypatch.setattr(sponsors, "_MANIFEST", tmp_path / "s.json")
    monkeypatch.setattr(sponsors, "DATA_DIR", tmp_path)
    assert sponsors.house_brand_enabled() is False
    sponsors.set_house_brand(True)
    assert sponsors.house_brand_enabled() is True
    sponsors.set_house_brand(False)
    assert sponsors.house_brand_enabled() is False


def test_the_admin_page_exposes_the_switch():
    """A setting with no control is a setting only I can change, which is not
    much better than the hard-coded default it replaced."""
    admin = (ROOT / "server" / "admin.py").read_text()
    assert "/admin/housebrand" in admin, "no admin route for the house logo"
    assert "House logo" in admin, "the toggle is not labeled on the page"


def test_no_sponsor_means_no_fallback_in_the_builder():
    """Pinned in the source: the fallback branch is what caused this, and it is
    an easy thing to reintroduce while tidying."""
    src = (ROOT / "missiongen" / "builder.py").read_text()
    code = "\n".join(l.split("#", 1)[0] for l in src.splitlines())
    assert "house_brand_enabled" in code, \
        "the builder no longer checks whether the house logo was asked for"
    assert "elif branding.add_brand_splash(m)" not in code, \
        "the unconditional fallback to the shipped wordmark is back"


# --- the BETA label ---------------------------------------------------------

def test_the_site_says_it_is_a_beta():
    """Rob's call: people should know it is not perfect before they judge it by
    what it gets wrong."""
    assert re.search(r'class="beta"[^>]*>BETA<', HTML), \
        "no BETA badge next to the wordmark"
    assert ".topbar .beta" in HTML, "the BETA badge has no styling"


def test_the_badge_explains_itself():
    """A bare BETA badge tells someone the tool might be broken without telling
    them what to do about it. The tooltip and the landing note carry the useful
    half: it makes real missions, and the editor is your escape hatch."""
    m = re.search(r'class="beta"\s+title="([^"]+)"', HTML)
    assert m, "the BETA badge has no tooltip"
    assert len(m.group(1)) > 60, f"tooltip is a stub: {m.group(1)!r}"
    assert "This is a beta." in HTML, \
        "the landing page never says it in prose"
    assert "Mission Editor" in HTML.split("This is a beta.")[1][:400], \
        "the beta note does not point at the editor as the way out"
