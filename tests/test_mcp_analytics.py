"""Count actual tool work once; preserve domain security and reporting ownership."""
import datetime as dt
import json

import anyio
from fastapi import HTTPException
from fastapi.testclient import TestClient
from mcp import Client
import pytest

from missiongen import Recipe, __version__, analytics
from missiongen.share import encode_recipe
from server import admin, mcp_server, mission_kit
from server.app import app

RECIPE = {'map': 'caucasus', 'era': 'modern', 'aircraft': 'F_16C_50', 'seed': 17}


@pytest.fixture(autouse=True)
def ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(analytics, 'DATA_DIR', tmp_path / 'analytics')


def tool(name, params):
    async def run():
        async with Client(mcp_server.mcp) as client:
            return await client.call_tool(name, {'params': params})
    return anyio.run(run)


@pytest.fixture
def prepared_build(monkeypatch):
    def build(recipe, directory):
        mission = directory / 'mission.miz'
        mission.write_bytes(b'prepared-native-archive')
        return {'manifest': {'share_code': encode_recipe(recipe), 'mission': {'sha256': 'a' * 64}},
                'miz': mission, 'bundle': mission}
    monkeypatch.setattr(mission_kit, 'build_kit', build)


def test_success_counts_once_and_downloads_discovery_validation_do_not_add_builds(prepared_build):
    assert not tool('sortiestarter_list_catalog', {'kind': 'maps'}).is_error
    assert not tool('sortiestarter_validate_recipe', {'recipe': RECIPE}).is_error
    assert analytics.mcp_stats()['built'] == 0
    response = tool('sortiestarter_generate_mission', {'recipe': RECIPE})
    assert not response.is_error
    assert analytics.mcp_stats()['built'] == 1
    with TestClient(app, base_url='http://localhost') as client:
        query = {'r': encode_recipe(Recipe.from_dict(RECIPE)), 'version': __version__}
        assert client.get('/api/mission-kit', params=query).status_code == 200
        assert client.get('/api/mission-kit', params={**query, 'format': 'miz'}).status_code == 200
        assert client.get('/api/mission-kit', params={**query, 'sha256': 'b' * 64}).status_code == 409
    s = analytics.mcp_stats()
    assert (s['built'], s['downloads'], s['failed'], s['busy']) == (1, 2, 0, 0)
    assert s['last_built'] and sum(n for _, n in s['per_day']) == 1
    assert analytics.stats()['generates'] == 0
    assert analytics.stats()['share_dls'] == 0
    assert analytics.people()['opted_out_events'] == 0


@pytest.mark.parametrize('failure,expected', [(RuntimeError('private details'), 'failed'),
                                            (HTTPException(503, 'busy'), 'busy')])
def test_failed_and_busy_native_work_never_counts_as_completed(monkeypatch, failure, expected):
    def fail(*args):
        raise failure
    monkeypatch.setattr(mission_kit, 'build_kit', fail)
    assert tool('sortiestarter_generate_mission', {'recipe': RECIPE}).is_error
    stats = analytics.mcp_stats()
    assert stats['built'] == 0 and stats[expected] == 1
    raw = ''.join(p.read_text() for p in analytics.DATA_DIR.glob('events-*.jsonl'))
    assert 'private details' not in raw and 'recipe' not in json.loads(raw)


def test_invalid_recipe_and_claimed_mcp_source_are_not_completed_tool_builds():
    assert tool('sortiestarter_generate_mission', {'recipe': {'slots': 0}}).is_error
    analytics.record('generate', 'mcp', Recipe.from_dict(RECIPE))
    assert analytics.mcp_stats()['built'] == 0


def test_mcp_event_never_carries_a_browser_identity():
    analytics.record('mcp_build', 'mcp', Recipe.from_dict(RECIPE), visitor='not-a-browser')
    events = list(analytics._iter_events(30))
    assert len(events) == 1 and events[0]['visitor'] is None
    assert not (analytics.DATA_DIR / '.visitor_salt').exists()


def test_mcp_metrics_respect_window_and_do_not_count_bot_traffic_as_browsers(monkeypatch):
    now = dt.datetime.now(dt.timezone.utc)
    events = []
    for days, kind, source, visitor in [(40, 'mcp_build', 'mcp', None),
        (0, 'mcp_build', 'mcp', None), (0, 'mcp_error', 'mcp', None),
        (0, 'mcp_busy', 'mcp', None), (0, 'mcp_download', 'mcp', None),
        (0, 'generate', 'builder', 'browser'), (0, 'dl', 'share', None)]:
        events.append({'ts': (now-dt.timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%SZ'),
                       'kind': kind, 'source': source, 'visitor': visitor})
    analytics.DATA_DIR.mkdir()
    (analytics.DATA_DIR / 'events-test.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
    assert analytics.mcp_stats(30)['built'] == 1
    assert analytics.mcp_stats(90)['built'] == 2
    assert analytics.stats(30)['generates'] == 1
    assert analytics.stats(30)['sources'] == [('builder', 1)]
    assert analytics.stats(30)['share_dls'] == 1
    people = analytics.people(30)
    assert people['visitors'] == 1 and people['opted_out_events'] == 0


def test_admin_count_is_private_and_reports_no_historical_backfill(monkeypatch):
    monkeypatch.setenv('ADMIN_PASSWORD', 'test-mcp-admin-password')
    analytics.record('mcp_build', 'mcp', Recipe.from_dict(RECIPE))
    with TestClient(app, base_url='http://localhost') as client:
        assert 'MCP missions built' not in client.get('/admin/analytics').text
        client.cookies.set(admin._COOKIE, admin._make_token())
        response = client.get('/admin/analytics?days=7')
        assert response.status_code == 200
        assert '<b>1</b><small>MCP missions built' in response.text
        assert 'earlier MCP builds are unknown' in response.text
        assert 'last 7 days' in response.text and 'Streamable HTTP' in response.text


def test_admin_analytics_and_mcp_share_volume_owner():
    from server.catalog_owner import replay_target
    for path in ['/admin/analytics', '/mcp/', '/api/mission-kit']:
        assert replay_target(path, 'catalog-owner', 'replica') == 'catalog-owner'
        assert replay_target(path, 'catalog-owner', 'catalog-owner') is None


def test_analytics_storage_failure_never_breaks_a_successful_tool_build(monkeypatch, prepared_build):
    analytics.DATA_DIR.write_text('not a directory')
    assert not tool('sortiestarter_generate_mission', {'recipe': RECIPE}).is_error


def test_explicit_canonical_and_fly_domains_initialize_and_list_tools(monkeypatch):
    settings = mcp_server.transport_security('https://sortiestarter.com',
                                              'https://dcs-mission-starter.fly.dev')
    monkeypatch.setattr(mcp_server, 'security', settings)
    with TestClient(app, base_url='https://sortiestarter.com') as client:
        for host in ['sortiestarter.com', 'dcs-mission-starter.fly.dev', 'sortiestarter.com:443']:
            headers = {'Host': host, 'Origin': 'https://' + host.removesuffix(':443'),
                       'Accept': 'application/json, text/event-stream'}
            init = client.post('/mcp/', headers=headers, json={'jsonrpc': '2.0', 'id': 1,
                'method': 'initialize', 'params': {'protocolVersion': '2025-03-26',
                    'capabilities': {}, 'clientInfo': {'name': 'regression-client', 'version': '1'}}})
            assert init.status_code == 200, init.text
            result = client.post('/mcp/', headers=headers, json={'jsonrpc': '2.0', 'id': 2,
                'method': 'tools/list', 'params': {}})
            assert result.status_code == 200, result.text
            assert len(result.json()['result']['tools']) == 6
        assert client.post('/mcp/', headers={**headers, 'Host': 'evil.example'}, json={}).status_code == 421
        assert client.post('/mcp/', headers={**headers, 'Origin': 'https://evil.example'}, json={}).status_code == 403


@pytest.mark.parametrize('origin', ['https://*.example', 'https://example/path',
                                   'https://user:password@example', 'file://example',
                                   'https://example?token=private'])
def test_additional_origins_refuse_unsafe_configuration(origin):
    with pytest.raises(ValueError, match='explicit HTTP'):
        mcp_server.transport_security('https://sortiestarter.com', origin)
