"""The roadmap and the changelog are the owner's pages, not the public's.

Rob, on seeing the roadmap and the engineering log linked from the front
page: "not for people to read AI implementation thoughts." The roadmap and
CHANGELOG.md sit behind the admin password, and nothing public links to
them — including the old /api/roadmap address, which now only redirects.

What's new was retired in v1.105.0 ("get rid of the what's new section"):
the changelog is the one record. /api/whatsnew answers 410 rather than 404
because the footer linked it for eighty releases.
"""
from __future__ import annotations
from ui_source import ui_source, server_source

import importlib
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "hunter2")
    import server.admin as admin_mod
    import server.app as app_mod
    importlib.reload(admin_mod)
    importlib.reload(app_mod)
    admin_mod.log.disabled = True
    return TestClient(app_mod.app)


@pytest.fixture()
def unconfigured(monkeypatch):
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    import server.admin as admin_mod
    import server.app as app_mod
    importlib.reload(admin_mod)
    importlib.reload(app_mod)
    return TestClient(app_mod.app)


def _login(c):
    return c.post("/admin/login", data={"password": "hunter2"}, follow_redirects=False)


# --------------------------------------------------------------------------- #
# nothing public points at them
# --------------------------------------------------------------------------- #
def test_the_front_page_has_no_roadmap_link():
    src = ui_source()
    assert "/api/roadmap" not in src
    assert "/admin/roadmap" not in src and "/admin/changelog" not in src
    assert "/api/whatsnew" not in src, "What's new was retired in v1.105.0"


def test_whats_new_is_gone_and_says_so(client):
    """410, not 404: the address was public for eighty releases."""
    r = client.get("/api/whatsnew")
    assert r.status_code == 410
    assert "retired" in r.text.lower() and "changelog" in r.text.lower()
    assert not (ROOT / "docs" / "whatsnew.html").exists()
    assert not (ROOT / "docs" / "RELEASE_NOTES.md").exists()


def test_the_old_address_only_redirects(client):
    r = client.get("/api/roadmap", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/admin/roadmap"
    assert "roadmap" not in r.text.lower() or not r.text.strip()


# --------------------------------------------------------------------------- #
# closed without the password
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("path", ["/admin/roadmap", "/admin/roadmap/page", "/admin/changelog"])
def test_the_pages_are_closed_without_the_password(client, path):
    r = client.get(path)
    body = r.text.lower()
    assert "password" in body, "no login prompt"
    assert "changelog —" not in body and "where the product is today" not in body


@pytest.mark.parametrize("path", ["/admin/roadmap", "/admin/changelog"])
def test_the_pages_say_so_when_admin_is_not_configured(unconfigured, path):
    r = unconfigured.get(path)
    assert "isn't configured" in r.text
    assert "where the product is today" not in r.text.lower()


# --------------------------------------------------------------------------- #
# open with it
# --------------------------------------------------------------------------- #
def test_the_owner_sees_the_roadmap(client):
    _login(client)
    r = client.get("/admin/roadmap")
    assert r.status_code == 200 and "Roadmap" in r.text
    page = client.get("/admin/roadmap/page")
    assert page.status_code == 200
    assert "where the product is today" in page.text.lower()


def test_the_owner_sees_the_changelog_at_the_current_version(client):
    from missiongen import __version__
    _login(client)
    r = client.get("/admin/changelog")
    assert r.status_code == 200
    assert f"[{__version__}]" in r.text, "the changelog page is not the current file"
    assert "<h3>" in r.text and "<li>" in r.text, "the markdown was not rendered"


def test_the_tabs_carry_both_pages(client):
    _login(client)
    r = client.get("/admin")
    assert "/admin/roadmap" in r.text and "/admin/changelog" in r.text


def test_the_renderer_handles_what_the_two_files_use():
    from server.admin import _md_to_html
    out = _md_to_html("# T\n\n## [1.0.0] — x\n\n### Added\n- **a** `b`\n  cont\n- c\n\ntext **bold**\n\n---\n")
    assert "<h2>T</h2>" in out and "<h3>[1.0.0] — x</h3>" in out and "<h4>Added</h4>" in out
    assert "<li><b>a</b> <code>b</code> cont</li>" in out and "<li>c</li>" in out
    assert "<p>text <b>bold</b></p>" in out and "<hr>" in out
    assert "<script" not in _md_to_html("<script>alert(1)</script>")
