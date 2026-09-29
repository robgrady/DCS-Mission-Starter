"""Thanks: owner-curated, publicly rendered, and therefore an injection surface.

Two separate things are being guarded here, and they pull in opposite
directions.

**The split has to hold.** Citations live in `docs/SOURCES.md` — versioned,
reviewed, byte-guarded, rebuilt by the release script. Thanks live on the data
volume so the owner can add a name without a deploy. If the thanks ever get
baked into the generated page, two failures follow at once: the owner cannot
edit them, and the next release silently wipes whatever they added. So the
injection must happen at REQUEST time, and `docs/sources.html` on disk must
stay free of them.

**It is free text on a public page.** The name and note are whatever the owner
typed, and the link is rendered as an anchor. That is an XSS surface with a
friendly face, so the URL is scheme-restricted at the storage layer and
everything is escaped at render.
"""
import json
import os
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent


@pytest.fixture()
def store(monkeypatch):
    """A fresh, isolated volume per test — these functions write to disk."""
    d = tempfile.mkdtemp()
    monkeypatch.setenv("CREDITS_DATA_DIR", d)
    import importlib
    from missiongen import credits as _cr
    importlib.reload(_cr)
    yield _cr
    importlib.reload(_cr)


def test_a_fresh_deploy_is_never_a_blank_page(store):
    """No volume, no manifest, first request. The seed is what stops the
    Sources page ending on an empty heading."""
    rows = store.load()
    assert len(rows) >= 4
    assert all(r.get("name") for r in rows)
    assert {"Sedlo", "Stewmanji"} <= {r["name"] for r in rows}


def test_add_edit_and_delete_round_trip(store):
    cid = store.add("Grim Reapers", "Testing videos", "https://example.com/x")
    assert cid
    got = next(r for r in store.load() if r["id"] == cid)
    assert got["name"] == "Grim Reapers" and got["url"].startswith("https://")

    assert store.update(cid, note="Something else", order=-5)
    got = next(r for r in store.load() if r["id"] == cid)
    assert got["note"] == "Something else"
    assert store.load()[0]["id"] == cid, "order did not take effect"

    assert store.delete(cid)
    assert cid not in {r["id"] for r in store.load()}


def test_a_credit_cannot_be_left_nameless(store):
    """An entry with no name renders as a bare dash on a public page."""
    assert store.add("   ", "note only") is None
    cid = store.add("Real Name")
    assert store.update(cid, name="  ") is False
    assert next(r for r in store.load() if r["id"] == cid)["name"] == "Real Name"


@pytest.mark.parametrize("bad", [
    "javascript:alert(1)",
    "JaVaScRiPt:alert(1)",
    "data:text/html;base64,PHNjcmlwdD4=",
    "vbscript:msgbox(1)",
    "file:///etc/passwd",
    "//evil.example.com",
])
def test_only_http_urls_are_stored(store, bad):
    """The credit link becomes an `<a href>` on a page every visitor can
    reach. Rejecting at the STORAGE layer means a bad value cannot reach the
    renderer even if a future renderer forgets to check."""
    cid = store.add("Someone", "", bad)
    assert next(r for r in store.load() if r["id"] == cid)["url"] == "", \
        f"{bad!r} was stored as a link"


def test_markup_in_a_name_is_escaped_when_served(store, monkeypatch):
    """Assert on the TAG, not on the string inside it.

    The first version of this failed on safely-escaped output: it looked for
    the substring `onerror=alert(2)`, which is still present — and inert —
    inside `&lt;img src=x onerror=alert(2)&gt;`. Escaping does not delete the
    text, it neutralises the angle brackets, so a substring search flags a
    correct implementation. (Second time this exact mistake has been made in
    this codebase. The rule: check that no live `<script`/`<img` element was
    emitted, not that a payload's characters are absent.)"""
    from fastapi.testclient import TestClient
    from server.app import app
    store.add("<script>alert(1)</script>", "<img src=x onerror=alert(2)>")
    body = TestClient(app).get("/api/sources").text
    thanks = body.split("<h2>Thanks</h2>", 1)[1]
    assert "<script" not in thanks, "an unescaped script element was emitted"
    assert "<img" not in thanks, "an unescaped img element was emitted"
    assert "&lt;script&gt;" in thanks, "the name vanished instead of being escaped"


def test_restore_puts_the_shipped_list_back(store):
    for r in store.load():
        store.delete(r["id"])
    assert store.load() == []
    assert store.restore_seed() >= 4
    assert "Sedlo" in {r["name"] for r in store.load()}


def test_the_thanks_are_served_but_not_baked_into_the_artifact(store):
    """The whole architectural point, asserted both ways.

    Present in the response — otherwise nobody is thanked. Absent from
    `docs/sources.html` on disk — otherwise the release script overwrites the
    owner's edits and `tests/test_sources.py` starts failing on data that is
    supposed to change."""
    from fastapi.testclient import TestClient
    from server.app import app
    store.add("Nobody Would Type This Name", "unique marker")
    body = TestClient(app).get("/api/sources").text
    assert "Nobody Would Type This Name" in body
    on_disk = (ROOT / "docs" / "sources.html").read_text()
    assert "Nobody Would Type This Name" not in on_disk
    assert "<h2>Thanks</h2>" not in on_disk, (
        "the Thanks block has been baked into the generated page — the owner "
        "can no longer edit it and the next release will wipe their changes")


def test_the_credits_endpoint_is_json_and_read_only(store):
    from fastapi.testclient import TestClient
    from server.app import app
    c = TestClient(app)
    r = c.get("/api/credits")
    assert r.status_code == 200
    assert {"name", "note", "url"} == set(r.json()["credits"][0])
    # No unauthenticated write path: editing is admin-only, and /admin is
    # disabled outright unless ADMIN_PASSWORD is set.
    assert c.post("/api/credits", json={"name": "x"}).status_code in (404, 405)


def test_editing_requires_the_admin(store, monkeypatch):
    """/admin is the only way in, and it is off entirely without a password."""
    from fastapi.testclient import TestClient
    from server.app import app
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    c = TestClient(app)
    r = c.post("/admin/credits", data={"name": "Uninvited"})
    assert "Uninvited" not in str(r.content)
    assert "Uninvited" not in {x["name"] for x in c.get("/api/credits").json()["credits"]}
