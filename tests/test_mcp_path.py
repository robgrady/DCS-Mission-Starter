"""A slash-normalizing host must reach discovery without changing POST to GET."""
import json

import anyio
from fastapi.testclient import TestClient
import pytest

from missiongen import __version__, analytics
from server import mcp_server, mcp_diagnostics
from server.app import app
from server.mcp_path import MCPPathAlias


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(analytics, 'DATA_DIR', tmp_path/'analytics')
    monkeypatch.setattr(mcp_server, 'security', mcp_server.transport_security(
        'https://sortiestarter.com','https://dcs-mission-starter.fly.dev'))


@pytest.mark.parametrize('domain', ['sortiestarter.com','dcs-mission-starter.fly.dev'])
@pytest.mark.parametrize('path', ['/mcp','/mcp/'])
def test_initialize_list_and_body_work_without_following_redirects(domain,path):
    headers = {'Accept':'application/json, text/event-stream','MCP-Protocol-Version':'2025-03-26'}
    with TestClient(app,base_url='https://'+domain,follow_redirects=False) as client:
        init = client.post(path,headers=headers,json={'jsonrpc':'2.0','id':1,'method':'initialize',
            'params':{'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'path-test','version':'1'}}})
        assert init.status_code == 200 and 'location' not in init.headers
        assert init.json()['result']['serverInfo']['version'] == __version__
        listed = client.post(path,headers=headers,json={'jsonrpc':'2.0','id':2,'method':'tools/list'})
        assert listed.status_code == 200 and len(listed.json()['result']['tools']) == 6
        assert 'location' not in listed.headers and not listed.history
        recipe={'map':'syria','start':'air','start_position':{'lat':33.6,'lon':31.6}}
        validated=client.post(path,headers=headers,json={'jsonrpc':'2.0','id':3,'method':'tools/call',
            'params':{'name':'sortiestarter_validate_recipe','arguments':{'params':{'recipe':recipe}}}})
        body=validated.json()['result']
        assert validated.status_code == 200 and not body.get('isError')
        assert body['structuredContent']['recipe']['start_position'] == recipe['start_position']
    rows=mcp_diagnostics.recent()
    assert [r['rpc'] for r in rows] == ['initialize','tools/list','tools/call']
    assert all(r['path']==path and r['status']==200 for r in rows)
    assert rows[1]['tools'] == 6


def test_alias_keeps_host_origin_body_limits_and_fly_owner_checks(monkeypatch):
    with TestClient(app,base_url='https://sortiestarter.com',follow_redirects=False) as client:
        headers={'Accept':'application/json, text/event-stream','Content-Type':'application/json'}
        assert client.post('/mcp',headers={**headers,'Host':'evil.example'},json={}).status_code == 421
        assert client.post('/mcp',headers={**headers,'Origin':'https://evil.example'},json={}).status_code == 403
        assert client.post('/mcp',headers=headers,content=b'x'*1_000_001).status_code == 413
        assert client.post('/mcp',headers=headers,content=iter([b'x'*500_001,b'x'*500_001])).status_code == 413
        monkeypatch.setenv('PACKS_OWNER_MACHINE','owner')
        monkeypatch.setenv('FLY_MACHINE_ID','replica')
        response=client.post('/mcp',headers=headers,json={})
        assert response.headers['fly-replay'] == 'instance=owner'
        assert 'x-sortie-request-id' not in response.headers


def test_alias_changes_only_the_exact_path_and_never_consumes_the_body():
    async def run():
        seen=[]
        async def receive():
            raise AssertionError('alias must not read the body')
        async def send(message):
            raise AssertionError('alias must not send its own response')
        async def inner(scope, incoming, outgoing):
            seen.append(scope)
            assert incoming is receive and outgoing is send
        alias=MCPPathAlias(inner)
        original={'type':'http','path':'/mcp','raw_path':b'/mcp','method':'POST',
                  'query_string':b'test=1','headers':[(b'accept',b'application/json')]}
        await alias(original,receive,send)
        assert original['path']=='/mcp' and original['raw_path']==b'/mcp'
        assert seen[0]=={**original,'path':'/mcp/','raw_path':b'/mcp/'}
        for path in ('/mcp/','/mcp-other','/api/health'):
            scope={**original,'path':path}
            await alias(scope,receive,send)
            assert seen[-1] is scope
    anyio.run(run)
