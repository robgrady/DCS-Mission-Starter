"""Observe actual HTTP discovery without secrets, weakened security or builds."""
import json

from fastapi.testclient import TestClient
import pytest

from missiongen import __version__, analytics
from server import admin, mcp_server, mcp_diagnostics as diagnostics
from server.app import app


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(analytics, 'DATA_DIR', tmp_path/'analytics')
    monkeypatch.setattr(mcp_server, 'security', mcp_server.transport_security('https://sortiestarter.com'))


def test_initialize_and_list_preserve_sdk_reply_and_trace_discovery():
    headers = {'Accept':'application/json, text/event-stream',
               'Authorization':'Bearer super-secret', 'Cookie':'private-cookie',
               'Origin':'https://sortiestarter.com', 'MCP-Protocol-Version':'2025-03-26'}
    with TestClient(app, base_url='https://sortiestarter.com') as client:
        init = client.post('/mcp/', headers=headers, json={'jsonrpc':'2.0','id':1,
            'method':'initialize','params':{'protocolVersion':'2025-03-26',
             'capabilities':{},'clientInfo':{'name':'private-client','version':'secret-version'}}})
        assert init.status_code == 200 and init.json()['result']['serverInfo']['version'] == __version__
        listed = client.post('/mcp/', headers=headers, json={'jsonrpc':'2.0','id':2,'method':'tools/list'})
        assert listed.status_code == 200 and len(listed.json()['result']['tools']) == 6
        assert 'mcp-session-id' not in listed.headers
        assert listed.headers['x-sortie-version'] == __version__
    rows = diagnostics.recent()
    assert [r['rpc'] for r in rows] == ['initialize','tools/list']
    row = rows[-1]
    assert row['id'] == listed.headers['x-sortie-request-id']
    assert row['tools'] == 6 and row['bytes'] == len(listed.content) and row['status'] == 200
    assert row['accept_json'] and row['accept_sse'] and row['origin_present'] and row['protocol_present']
    raw = (analytics.DATA_DIR/'mcp-connections.json').read_text()
    assert not any(s in raw for s in ('super-secret','private-cookie','private-client','secret-version','Authorization','127.0.0.1'))
    assert analytics.mcp_stats()['built'] == 0


def test_security_errors_unacceptable_headers_redirect_and_invalid_json_are_visible():
    with TestClient(app, base_url='https://sortiestarter.com', follow_redirects=False) as client:
        headers = {'Accept':'application/json, text/event-stream'}
        assert client.post('/mcp', headers=headers, json={}).status_code == 307
        assert client.post('/mcp/', headers={**headers,'Host':'evil.example'},json={}).status_code == 421
        assert client.post('/mcp/',headers={**headers,'Origin':'https://evil.example'},json={}).status_code == 403
        assert client.post('/mcp/', headers={'Accept':'text/plain'},json={}).status_code == 406
        assert client.post('/mcp/', headers=headers,content=b'{broken',
                           ).status_code >= 400
    rows = diagnostics.recent()
    assert [r['status'] for r in rows] == [307,421,403,406,400]
    assert rows[0]['rpc'] == 'unread'  # redirect does not consume the body
    assert rows[-1]['rpc'] == 'invalid_json'


def test_large_request_limit_and_storage_failure_do_not_change_sdk_behavior():
    with TestClient(app, base_url='https://sortiestarter.com') as client:
        response = client.post('/mcp/',headers={'Accept':'application/json, text/event-stream'},
                               content=b' '*1_000_001)
        assert response.status_code == 413
        assert diagnostics.recent()[-1]['status'] == 413
        (analytics.DATA_DIR/'mcp-connections.json').unlink()
        analytics.DATA_DIR.rmdir()
        analytics.DATA_DIR.write_text('unwritable')
        response = client.post('/mcp/',headers={'Accept':'application/json, text/event-stream'},
                               json={'jsonrpc':'2.0','id':1,'method':'tools/list'})
        assert response.status_code == 200


def test_ring_is_bounded_expired_records_hidden_and_corrupt_file_safe():
    from datetime import datetime, timezone
    diagnostics.record({'ts':'2000-01-01T00:00:00+00:00','id':'expired'})
    assert diagnostics.recent() == []
    for n in range(diagnostics.LIMIT+3):
        diagnostics.record({'ts':datetime.now(timezone.utc).isoformat(),'id':str(n)})
    assert len(diagnostics.recent()) == diagnostics.LIMIT
    assert diagnostics.recent()[0]['id'] == '3'
    (analytics.DATA_DIR/'mcp-connections.json').write_text('bad json')
    assert diagnostics.recent() == []


def test_diagnostics_are_admin_only_and_replica_replay_is_not_recorded(monkeypatch):
    monkeypatch.setenv('ADMIN_PASSWORD','test-diagnostics-password')
    with TestClient(app, base_url='http://localhost') as client:
        assert 'MCP connection diagnostics' not in client.get('/admin/analytics').text
        client.cookies.set(admin._COOKIE,admin._make_token())
        assert 'MCP connection diagnostics' in client.get('/admin/analytics').text
        monkeypatch.setenv('PACKS_OWNER_MACHINE','owner')
        monkeypatch.setenv('FLY_MACHINE_ID','replica')
        response = client.post('/mcp/',json={'jsonrpc':'2.0','id':1,'method':'tools/list'})
        assert response.headers['fly-replay'] == 'instance=owner'
        assert diagnostics.recent() == []
