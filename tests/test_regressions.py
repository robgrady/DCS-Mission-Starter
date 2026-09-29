"""Production 500s, pinned one at a time.

Everything here is a bug a user actually hit on sortiestarter.com. They have
nothing in common technically — a header encoding rule, a divide-by-zero in a
chart, a data pack — and that is the point: each one is here because it shipped,
not because it fit a category.

The two that reached users were both invisible in a unit test of the thing that
broke. `_header_safe` was never wrong; the *engine* produced prose containing an
em dash, and Starlette refused to put it in a header. `people()` was never
wrong; the *admin page* divided by a max() of an all-zero list. Both needed the
whole stack in the test to fail, so these go through the real ASGI app.
"""
import json
import os
import shutil
import tempfile

import pytest
from fastapi.testclient import TestClient

from missiongen import Recipe, generate
from missiongen.resolver import load_json, validate_data_packs


@pytest.fixture(scope="module")
def client():
    from server.app import app
    return TestClient(app)


# --- the latin-1 header 500 -------------------------------------------------
# Every carrier mission with a tanker failed to download, including the
# Library's Carrier Qualification card. HTTP headers are latin-1 by spec and
# Starlette enforces it; the engine's own warning — "Carrier tanker is the KA-6D
# (A-6E) — the air wing's own gas" — contains an em dash. One punctuation
# character turned the whole response into a 500 and the user got no mission.

def test_engine_prose_can_always_survive_a_response_header(client):
    from server.app import _header_safe
    for s in ["Carrier tanker is the KA-6D (A-6E) — the air wing's own gas",
              "2× R-60 · 800 L tank … “quoted” ‘apostrophes’ → done ✓ • bullet",
              "R-27ER + R-73 – dash, −minus"]:
        out = _header_safe(s)
        out.encode("latin-1")           # the assertion is that this does not raise
        assert "?" not in out or "?" in s, \
            f"a character was replaced rather than transliterated: {out!r}"


def test_every_warning_the_engine_can_emit_is_header_safe():
    """Guarding `_header_safe` is not the same as guarding the warnings. A new
    warning with a new typographic character is the same bug again, so build
    the missions that produce the most warnings and check the real strings."""
    from server.app import _header_safe
    for label, rc in [
        ("carrier+tanker", dict(map="persiangulf", era="coldwar",
                                aircraft="F_14A_135_GR", bb_carrier=True,
                                home_airbase="CARRIER", bb_tanker=True,
                                bb_awacs=True, carrier_cap=True, seed=31)),
        ("dressed", dict(map="caucasus", era="modern", aircraft="FA_18C_hornet",
                         dress_fill=100, bb_ambient=False, seed=32)),
    ]:
        d = tempfile.mkdtemp()
        try:
            res = generate(Recipe.from_dict(rc), os.path.join(d, "m.miz"))
        finally:
            shutil.rmtree(d, ignore_errors=True)
        joined = "; ".join(res["warnings"])
        _header_safe(joined)[:900].encode("latin-1")


def test_a_carrier_mission_with_a_tanker_actually_downloads(client):
    """The end-to-end version. This is the request that 500'd."""
    r = client.post("/api/generate", json={"recipe": dict(
        map="persiangulf", era="coldwar", aircraft="F_14A_135_GR",
        bb_carrier=True, home_airbase="CARRIER", bb_tanker=True, bb_awacs=True,
        bb_ambient=False, seed=33), "source": "builder"})
    assert r.status_code == 200, f"{r.status_code}: {r.text[:400]}"
    assert r.content[:2] == b"PK", "the response is not a zip"
    assert "X-Warnings" in r.headers


def test_the_mission_kit_header_stays_inside_its_budget(client):
    """`X-Kit` is JSON the frontend parses. A TRUNCATED payload is worse than a
    missing one — JSON.parse throws and the panel silently loses every row — so
    the engine sheds enemy_air rows until it fits rather than slicing."""
    r = client.post("/api/generate", json={"recipe": dict(
        map="caucasus", era="modern", aircraft="FA_18C_hornet",
        threat_intensity=5, bb_sams=True, bb_ambient=False, seed=34),
        "source": "builder"})
    assert r.status_code == 200, r.text[:300]
    kit = json.loads(r.headers["X-Kit"])        # must parse, not just exist
    assert len(r.headers["X-Kit"]) <= 2000
    assert isinstance(kit.get("enemy_air"), list)


# --- the analytics divide-by-zero 500 ---------------------------------------
# /admin/analytics returned a bare 500, which also took down the Sponsor ads and
# Mission packs tabs, because they are reached through this page's tab bar.
# `max((v for _, v in buckets), default=1)` returns 0 from a NON-empty list of
# zeros — `default` only applies to an empty iterable — and the bar widths
# divided by it. Every window on a site whose ledger pre-dates v1.43.0 hits it,
# because those events carry no anonymous id.

def _people(**over):
    base = {"days": 30, "visitors": 0, "returning": 0, "returning_pct": 0,
            "new": 0, "avg_missions": 0, "median_missions": 0,
            "top_builder_missions": 0, "one_and_done_pct": 0,
            "opted_out_events": 0, "opted_out_pct": 0,
            "buckets": [("1 mission", 0), ("2-4", 0), ("5-9", 0), ("10+", 0)]}
    base.update(over)
    return base


def test_the_chart_survives_a_bucket_list_that_is_all_zeros(monkeypatch):
    """The scale factor is computed BEFORE the empty-state branch, off a
    non-empty list of zeros — the case `default=1` looks like it covers and
    does not, because `default` only applies to an empty iterable. Two guards
    stand between this and a 500; this exercises the inner one by handing the
    page a state the outer one waves through."""
    from missiongen import analytics
    from server import admin
    monkeypatch.setattr(analytics, "people",
                        lambda days=30: _people(visitors=3, returning=1))
    page = admin._analytics_page(30)
    assert page.status_code == 200
    assert "Analytics unavailable" not in page.body.decode(), \
        "the missions-per-person chart is dividing by zero again"


def test_the_admin_analytics_page_renders_with_an_empty_ledger(client, monkeypatch):
    """An admin page must never be able to lock the operator out of the admin."""
    monkeypatch.setenv("ADMIN_PASSWORD", "test-only-not-a-real-secret")
    from missiongen import analytics
    monkeypatch.setattr(analytics, "people", lambda days=30: {
        "days": days, "visitors": 0, "returning": 0, "returning_pct": 0,
        "new": 0, "avg_missions": 0, "median_missions": 0,
        "top_builder_missions": 0, "one_and_done_pct": 0,
        "opted_out_events": 0, "opted_out_pct": 0,
        "buckets": [("1 mission", 0), ("2-4", 0), ("5-9", 0), ("10+", 0)]})
    from server import admin
    page = admin._analytics_page(30)
    assert page.status_code == 200
    body = page.body.decode()
    assert "Analytics unavailable" not in body, "the page fell through to its error shell"
    assert "can be attributed to a browser" in body, \
        "an empty window should explain itself, not draw four zero-length bars"


def test_an_ledger_with_pre_v1_43_events_still_reports(monkeypatch, tmp_path):
    """The real shape of the data that broke it: generate events with no
    `visitor` key at all, because the anonymous id did not exist yet."""
    import datetime as dt

    from missiongen import analytics
    day = dt.datetime.now(dt.timezone.utc)
    monkeypatch.setattr(analytics, "_iter_events", lambda days: [
        {"kind": "generate", "source": "builder", "era": "modern",
         "map": "caucasus", "aircraft": "FA_18C_hornet",
         "ts": day.isoformat()} for _ in range(12)])
    pe = analytics.people(30)
    assert pe["visitors"] == 0
    assert pe["opted_out_events"] == 12 and pe["opted_out_pct"] == 100
    assert pe["avg_missions"] == 0 and pe["returning_pct"] == 0
    s = analytics.stats(30)
    assert s["generates"] == 12 and s["brief_attach_pct"] == 0


def test_the_analytics_ledger_records_no_identifying_data(monkeypatch, tmp_path):
    """The standing constraint on this feature: no IP, no user agent, no
    fingerprint. A field added to `record()` in a hurry is how that slips."""
    monkeypatch.setattr("missiongen.analytics.DATA_DIR", tmp_path)
    from missiongen import analytics
    analytics.record("generate", "builder",
                     Recipe.from_dict(dict(map="caucasus", era="modern",
                                           aircraft="FA_18C_hornet", seed=1)),
                     visitor="abc123")
    # only the append-only event ledger; DATA_DIR also holds the hash salt
    written = [json.loads(l) for f in sorted(tmp_path.rglob("*.jsonl"))
               for l in f.read_text().splitlines() if l.strip()]
    assert written, "record() wrote nothing"
    BANNED = {"ip", "ip_address", "remote_addr", "user_agent", "ua",
              "referer", "referrer", "fingerprint", "email", "name",
              "host", "session", "cookie"}
    for e in written:
        leaked = BANNED & {k.lower() for k in e}
        assert not leaked, f"the ledger recorded {leaked}: {e}"


# --- health and the data packs ----------------------------------------------

def test_health_is_honest_about_the_data_packs(client):
    r = client.get("/api/health")
    assert r.status_code in (200, 503)
    body = r.json()
    assert body["ok"] is not None
    assert body["data_pack_errors"] == validate_data_packs()
    assert r.status_code == (503 if body["data_pack_errors"] else 200), \
        "a broken data pack must return 503, not a 200 with ok:false — a load " \
        "balancer reads the status code, not the body"


def test_health_reports_whether_liveries_are_verified(client):
    """v1.46.4: parked statics wear stock skins until someone runs
    dump_liveries.py against a real install. That state has to be visible from
    outside, or the only way to know is to build a mission and look."""
    assert "liveries_verified" in client.get("/api/health").json()


def test_every_flyable_aircraft_has_a_service_window(client):
    """A jet with no window can be picked in an era it never flew in — the
    v1.46.1 class of bug, from the aircraft side instead of the card side."""
    assert client.get("/api/health").json()["service_data_gaps"] == []


def test_the_data_packs_validate():
    errors = validate_data_packs()
    assert not errors, f"data pack errors: {errors}"


# --- the Nevada boundary ----------------------------------------------------

def test_the_groom_lake_box_is_the_real_boundary():
    """R-4808N was drawn as a four-corner rectangle, which is why it never
    lined up with the boundary the NTTR map draws. The real area steps around
    the Nevada Test Site."""
    found = list(_walk_for(load_json("historical_airspace"), "R-4808N"))
    assert found, "R-4808N is no longer in historical_airspace.json"
    for zone in found:
        pts = (zone.get("corners") or zone.get("points")
               or zone.get("polygon") or [])
        assert len(pts) == 14, (
            f"R-4808N has {len(pts)} points. The published legal boundary "
            f"(FAA realignment effective 1995) has 14 and steps around the "
            f"Nevada Test Site; a 4-corner box never lined up with the "
            f"boundary the NTTR map draws.")
        assert zone.get("source"), \
            "the boundary lost its citation — the only thing that makes the " \
            "14 points checkable by a human"


def _walk_for(node, name):
    if isinstance(node, dict):
        if node.get("name") == name:
            yield node
        for v in node.values():
            yield from _walk_for(v, name)
    elif isinstance(node, list):
        for v in node:
            yield from _walk_for(v, name)
