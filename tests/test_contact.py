"""The contact channel — store, public API, anti-abuse, admin inbox.

Spec: docs/contact-form-spec.md. The properties worth defending, in order of
what it costs to get them wrong:

  1. A message a user was told we received must actually be stored.
  2. The admin inbox must not be readable without the admin password.
  3. Text typed by a stranger must not execute in Rob's authenticated session.
  4. The anti-abuse layers must reject bots WITHOUT ever eating a real message.
  5. The contact store and the anonymous analytics ledger must not bleed into
     each other — that separation is the whole privacy argument.
"""
from ui_source import ui_source, server_source
import importlib
import json
import time

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def store(tmp_path, monkeypatch):
    """A contact store rooted in a temp dir, reloaded so DATA_DIR follows."""
    monkeypatch.setenv("CONTACT_DATA_DIR", str(tmp_path / "contact"))
    from missiongen import contact as _c
    importlib.reload(_c)
    yield _c
    importlib.reload(_c)


@pytest.fixture()
def client(store, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "hunter2")
    import server.app as app_mod
    import server.admin as admin_mod
    importlib.reload(admin_mod)
    importlib.reload(app_mod)
    app_mod.contact_store = store          # the reloaded, temp-dir store
    admin_mod.log.disabled = True
    c = TestClient(app_mod.app)
    c._app_mod = app_mod
    yield c


def _submit(c, **over):
    """A valid submission, with the time floor honestly satisfied."""
    t = c.get("/api/contact/token").json()
    body = dict(name="Rob Grady", email="rob@example.com", topic="bug",
                comment="The Syria map crashed when I pressed generate.",
                context={"view": "builder", "recipe": "abc"},
                issued=t["issued"] - 10, sig=None)
    # re-sign the backdated issue time the way the server would
    body["sig"] = c._app_mod._contact_sign(body["issued"])
    body.update(over)
    return c.post("/api/contact", json=body)


# ------------------------------------------------------------------- the store
def test_a_message_survives_the_round_trip(store):
    mid = store.add("Rob", "rob@example.com", "bug", "Something broke badly.",
                    {"version": "1.64.0", "view": "builder", "recipe": "x"})
    assert mid
    msgs = store.load()
    assert len(msgs) == 1
    m = msgs[0]
    assert m["name"] == "Rob" and m["topic"] == "bug" and m["read"] is False
    assert m["context"]["version"] == "1.64.0"


def test_read_state_folds_and_the_last_op_wins(store):
    mid = store.add("A", None, "feature", "Please add the Viggen module.")
    assert store.unread_count() == 1
    store.mark_read(mid)
    assert store.get(mid)["read"] is True and store.unread_count() == 0
    store.mark_read(mid, False)
    assert store.get(mid)["read"] is False and store.unread_count() == 1


def test_delete_removes_it_from_the_inbox(store):
    mid = store.add("A", None, "other", "Just saying hello there.")
    store.delete(mid)
    assert store.load() == [] and store.get(mid) is None


def test_marking_read_does_not_rewrite_the_original_line(store):
    """The append-only contract. If a future 'optimisation' rewrites lines in
    place, a truncated write costs every message in the month — so the base
    record must still be on disk verbatim after a mutation."""
    mid = store.add("A", None, "bug", "A message worth not losing at all.")
    f = sorted(store.DATA_DIR.glob("messages-*.jsonl"))[0]
    before = f.read_text().splitlines()[0]
    store.mark_read(mid)
    lines = f.read_text().splitlines()
    assert lines[0] == before, "the original record was rewritten"
    assert json.loads(lines[-1])["op"] == "read"


def test_a_corrupt_line_costs_one_message_not_the_inbox(store):
    store.add("A", None, "bug", "The first message, before the corruption.")
    f = sorted(store.DATA_DIR.glob("messages-*.jsonl"))[0]
    with open(f, "a") as fh:
        fh.write('{"id": "truncated", "ts"\n')      # power loss mid-append
    store.add("B", None, "bug", "The second message, after the corruption.")
    assert len(store.load()) == 2


@pytest.mark.parametrize("field,value,bad", [
    ("name", "", True), ("name", "R", False),
    ("topic", "nonsense", True), ("topic", "bug", False),
    ("comment", "too short", True), ("comment", "x" * 10, False),
    ("comment", "x" * 4001, True),
    ("email", "", False),                 # OPTIONAL by design
    ("email", "not-an-email", True), ("email", "a@b.co", False),
    ("email", "a@b", True),
])
def test_validation_bounds(store, field, value, bad):
    kw = {"name": "Rob", "email": "", "topic": "bug", "comment": "A valid comment."}
    kw[field] = value
    assert bool(store.validate(**kw)) is bad, f"{field}={value!r}"


def test_the_store_refuses_to_write_an_invalid_message(store):
    assert store.add("", None, "bug", "short") is None
    assert store.load() == []


# --------------------------------------------------------------- the public API
def test_a_real_submission_is_stored(client, store):
    r = _submit(client)
    assert r.status_code == 200 and r.json()["ok"] is True
    msgs = store.load()
    assert len(msgs) == 1 and msgs[0]["name"] == "Rob Grady"


def test_the_server_stamps_the_version_itself(client, store):
    """A client-supplied version in a bug report is worthless — it is exactly
    the field a stale cached page would lie about."""
    from missiongen import __version__
    _submit(client, context={"version": "0.0.1-lies", "view": "builder"})
    assert store.load()[0]["context"]["version"] == __version__


def test_the_honeypot_swallows_a_bot_silently(client, store):
    r = _submit(client, website="http://buy-followers.example")
    assert r.status_code == 200 and r.json()["ok"] is True   # bot sees success
    assert store.load() == [], "honeypot submission was stored"


def test_a_forged_token_is_rejected(client, store):
    r = _submit(client, sig="deadbeef" * 4)
    assert r.status_code == 200 and r.json()["ok"] is True
    assert store.load() == []


def test_a_submission_faster_than_a_human_is_rejected(client, store):
    t = client.get("/api/contact/token").json()
    r = client.post("/api/contact", json=dict(
        name="Bot", email="", topic="bug", comment="Instant machine submission.",
        issued=t["issued"], sig=t["sig"]))
    assert r.status_code == 200 and r.json()["ok"] is True
    assert store.load() == [], "a sub-second submission was stored"


def test_the_client_never_trips_the_time_floor_itself():
    """The corollary, and the bug this caught during the build: the server
    silently DISCARDS a too-fast submission, so if our own form could post
    inside the floor, a quick human would be told 'sent' and lose their
    words. The client holds the request until the floor has passed."""
    from pathlib import Path
    fe = ui_source()
    assert "const MINMS = 3200" in fe
    assert "Math.max(0, MINMS - waited)" in fe


def test_validation_errors_come_back_per_field(client, store):
    r = _submit(client, name="", comment="nope")
    assert r.status_code == 422
    errs = r.json()["errors"]
    assert "name" in errs and "comment" in errs
    assert store.load() == []


def test_the_rate_limit_stops_a_flood_and_says_so(client, store):
    """The one rejection a user is TOLD about: a real person who hits it needs
    to know their message did not go through."""
    codes = [_submit(client).status_code for _ in range(7)]
    assert 429 in codes, codes
    assert codes.count(200) <= 5


def test_no_ip_address_is_ever_written_to_the_store(client, store):
    _submit(client)
    raw = "".join(p.read_text() for p in store.DATA_DIR.glob("*.jsonl"))
    for needle in ("testclient", "127.0.0.1", "client_host", "ip"):
        assert needle not in raw.lower() or needle == "ip" and '"ip"' not in raw
    assert '"ip"' not in raw


# ----------------------------------------------------------------- the admin
def _login(c):
    return c.post("/admin/login", data={"password": "hunter2"}, follow_redirects=False)


@pytest.mark.parametrize("method,path", [
    ("get", "/admin/contact"),
    ("post", "/admin/contact/anything/read"),
    ("post", "/admin/contact/anything/delete"),
])
def test_the_inbox_is_closed_without_the_password(client, store, method, path):
    store.add("Private", "a@b.co", "bug", "Something confidential in here.")
    r = (client.get(path) if method == "get"
         else client.post(path, data={"read": "1"}))
    body = r.text.lower()
    assert "password" in body, "no login prompt"
    assert "something confidential" not in body, "message leaked to an anonymous caller"


def test_the_inbox_lists_messages_once_authenticated(client, store):
    store.add("Rob Grady", "rob@example.com", "feature", "Add the Viggen please.")
    _login(client)
    body = client.get("/admin/contact").text
    assert "Rob Grady" in body and "Add the Viggen please." in body
    assert "Feature request" in body


def test_the_tab_badge_counts_only_unread(client, store):
    import re
    mid = store.add("A", None, "bug", "An unread message for the badge.")
    _login(client)
    assert re.search(r"<span class=tbadge>1</span>", client.get("/admin/contact").text)
    client.post(f"/admin/contact/{mid}/read", data={"read": "1"}, follow_redirects=True)
    assert not re.search(r"<span class=tbadge>\d+</span>", client.get("/admin/contact").text)


def test_read_and_unread_round_trip_through_the_admin(client, store):
    mid = store.add("A", None, "bug", "Toggle me back and forth please.")
    _login(client)
    client.post(f"/admin/contact/{mid}/read", data={"read": "1"}, follow_redirects=True)
    assert store.get(mid)["read"] is True
    client.post(f"/admin/contact/{mid}/read", data={"read": "0"}, follow_redirects=True)
    assert store.get(mid)["read"] is False


def test_delete_through_the_admin(client, store):
    mid = store.add("A", None, "bug", "Delete this one from the inbox.")
    _login(client)
    client.post(f"/admin/contact/{mid}/delete", follow_redirects=True)
    assert store.get(mid) is None


def test_a_stranger_cannot_inject_script_into_the_admin(client, store):
    """The inbox renders text typed by anonymous strangers into an
    authenticated session — the one place in this product where an XSS would
    be worth something."""
    payload = '<script>alert(1)</script><img src=x onerror="alert(2)">'
    store.add(payload, "a@b.co", "bug", "Comment with " + payload)
    _login(client)
    body = client.get("/admin/contact").text
    # Escaped text may legitimately CONTAIN the string "onerror=" (inside
    # &lt;img ... &gt;) — what must not exist is a real tag. Assert on the
    # tag openers, which is the thing a browser would actually execute.
    assert "<script" not in body and "<img" not in body
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in body, \
        "the payload should be visible to the admin, but inert"


def test_the_unread_filter_narrows_the_list(client, store):
    a = store.add("Unread Person", None, "bug", "This one stays unread here.")
    b = store.add("Read Person", None, "bug", "This one gets marked as read.")
    store.mark_read(b)
    _login(client)
    body = client.get("/admin/contact?unread=1").text
    assert "Unread Person" in body and "Read Person" not in body


# -------------------------------------------------- the two stores stay apart
def test_contact_data_never_lands_in_the_analytics_ledger(client, store, tmp_path,
                                                          monkeypatch):
    """The privacy argument in one test: the anonymous ledger must stay
    anonymous even though a sibling module now holds names and emails."""
    monkeypatch.setenv("ANALYTICS_DATA_DIR", str(tmp_path / "analytics"))
    from missiongen import analytics
    importlib.reload(analytics)
    _submit(client, name="Identifiable Person", email="secret@example.com")
    raw = "".join(p.read_text() for p in (tmp_path / "analytics").glob("*.jsonl")) \
        if (tmp_path / "analytics").exists() else ""
    assert "Identifiable Person" not in raw and "secret@example.com" not in raw
    importlib.reload(analytics)
