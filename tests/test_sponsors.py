"""Sponsor-ads MVP: store pipeline, SSRF guard, build wiring, and admin section."""
import io
import zipfile
import tempfile
from pathlib import Path

import pytest
from PIL import Image

from missiongen import sponsors, Recipe, generate


@pytest.fixture
def store(tmp_path, monkeypatch):
    """Point the sponsor store at a temp dir for the duration of a test."""
    monkeypatch.setattr(sponsors, "DATA_DIR", tmp_path)
    monkeypatch.setattr(sponsors, "_MANIFEST", tmp_path / "manifest.json")
    monkeypatch.setattr(sponsors, "_CACHE", tmp_path / "cache")
    return tmp_path


def _logo_bytes():
    return sponsors._DEFAULT_ASSET.read_bytes()


def test_render_splash_is_pil_only_and_downscales():
    img = sponsors.render_splash(_logo_bytes(), panel_opacity=90)
    assert img.mode == "RGBA"
    assert img.size[0] <= 1600
    # the panel makes the corners semi-transparent (not fully opaque)
    assert img.getpixel((1, 1))[3] < 255


def test_ssrf_guard_blocks_bad_urls():
    for bad in ["http://example.com/a.png",      # not https
                "https://127.0.0.1/a.png",         # loopback
                "https://169.254.169.254/a.png",   # cloud metadata
                "https://localhost/a.png"]:
        with pytest.raises(ValueError):
            sponsors.fetch_image(bad)


def test_manifest_crud_and_active(store):
    assert sponsors.branding_enabled() is True          # default with no store
    assert sponsors.active_splash() is None             # nothing active -> fallback

    a = sponsors.add_sponsor("Authentic Media", image_bytes=_logo_bytes(), make_active=True)
    b = sponsors.add_sponsor("Pimax", image_bytes=_logo_bytes(), splash_size=25)
    assert sponsors.list_sponsors()["active"] == a      # first add auto-active

    sponsors.set_active(b)
    act = sponsors.active_splash()
    assert act["id"] == b and act["size"] == 25 and Path(act["path"]).exists()

    sponsors.increment_impressions(b)
    sponsors.increment_impressions(b)
    assert sponsors.list_sponsors()["sponsors"][b]["impressions"] == 2

    sponsors.delete_sponsor(b)
    assert b not in sponsors.list_sponsors()["sponsors"]
    assert sponsors.list_sponsors()["active"] == a       # active reassigned
    assert not sponsors.cache_path(b).exists()


def test_add_requires_name_and_source(store):
    with pytest.raises(ValueError):
        sponsors.add_sponsor("", image_bytes=_logo_bytes())
    with pytest.raises(ValueError):
        sponsors.add_sponsor("NoSource")


def test_branding_toggle(store):
    sponsors.set_branding_enabled(False)
    assert sponsors.branding_enabled() is False
    sponsors.set_branding_enabled(True)
    assert sponsors.branding_enabled() is True


_RECIPE = {"map": "caucasus", "era": "modern", "coalition": "blue",
           "aircraft": "F_16C_50", "seed": 1}


def test_build_falls_back_to_default_when_no_sponsor(store):
    r = Recipe.from_dict(_RECIPE)
    res = generate(r, tempfile.mktemp(suffix=".miz"))
    assert res["stats"].get("branding") is True          # shipped Authentic asset


def test_build_uses_active_sponsor_and_embeds_it(store):
    sid = sponsors.add_sponsor("Pimax", image_bytes=_logo_bytes(),
                               splash_size=25, make_active=True)
    r = Recipe.from_dict(_RECIPE)
    out = tempfile.mktemp(suffix=".miz")
    res = generate(r, out)
    assert res["stats"].get("branding") == sid           # sponsor id -> impressions
    with zipfile.ZipFile(out) as z:
        assert any(n.lower().endswith(".png") for n in z.namelist())


def test_build_skips_branding_when_disabled(store):
    sponsors.add_sponsor("Pimax", image_bytes=_logo_bytes(), make_active=True)
    sponsors.set_branding_enabled(False)
    r = Recipe.from_dict(_RECIPE)
    res = generate(r, tempfile.mktemp(suffix=".miz"))
    assert "branding" not in res["stats"]


# --------------------------------------------------------------------------- #
# Admin section
# --------------------------------------------------------------------------- #
@pytest.fixture
def client(store, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "hunter2")
    from starlette.testclient import TestClient
    from server.app import app
    return TestClient(app)


def test_admin_requires_password(client):
    r = client.get("/admin")
    assert r.status_code == 200 and "Sign in" in r.text          # login gate
    assert client.post("/admin/login", data={"password": "nope"}).status_code == 200
    assert "ss_admin" not in client.cookies                       # no session on bad pw


def test_admin_login_and_manage(client):
    client.post("/admin/login", data={"password": "hunter2"})
    assert "ss_admin" in client.cookies

    r = client.post("/admin/sponsors",
                    data={"name": "Pimax", "url": "", "splash_size": "25",
                          "panel_opacity": "90", "make_active": "1"},
                    files={"file": ("pimax.png", _logo_bytes(), "image/png")})
    assert r.status_code == 200 and "Pimax" in r.text
    sid = list(sponsors.list_sponsors()["sponsors"])[0]
    assert sponsors.list_sponsors()["active"] == sid
    assert client.get(f"/admin/sponsors/{sid}/thumb.png").status_code == 200


def test_admin_actions_require_auth(client):
    # seed a sponsor as an authed admin
    client.post("/admin/login", data={"password": "hunter2"})
    client.post("/admin/sponsors",
                data={"name": "Pimax", "make_active": "1"},
                files={"file": ("p.png", _logo_bytes(), "image/png")})
    sid = list(sponsors.list_sponsors()["sponsors"])[0]

    # a fresh (unauthenticated) client must not be able to mutate
    from starlette.testclient import TestClient
    from server.app import app
    anon = TestClient(app)
    anon.post(f"/admin/sponsors/{sid}/delete", follow_redirects=False)
    assert sid in sponsors.list_sponsors()["sponsors"]            # not deleted
    assert anon.get(f"/admin/sponsors/{sid}/thumb.png").status_code == 401


def test_admin_disabled_without_password(store, monkeypatch):
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    from starlette.testclient import TestClient
    from server.app import app
    c = TestClient(app)
    r = c.get("/admin")
    assert r.status_code == 200 and "isn't configured" in r.text
    # and login can't be forced
    c.post("/admin/login", data={"password": ""})
    assert "ss_admin" not in c.cookies
