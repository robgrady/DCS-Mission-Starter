"""Actual MCP clients, native archive readback, bounded builds and download cleanup."""
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request
import zipfile

import anyio
from fastapi.testclient import TestClient
from mcp import Client
import pytest

from missiongen import Recipe, __version__
from missiongen.share import encode_recipe
from scripts.audit_library import inspect_archive
from server import mcp_server, mission_kit
from server.app import app
from server.generation import GenerationCapacity

RECIPE = {'era':'modern', 'slots':4, 'veteran_wingmen':3, 'bb_dressing':False,
          'bb_ambient':False, 'bb_sams':False, 'bb_branding':False, 'bb_kneeboard':True}


def call(name, arguments=None):
    async def work():
        async with Client(mcp_server.mcp) as client:
            return await client.call_tool(name, arguments or {})
    return anyio.run(work)


def test_sdk_discovers_structured_schemas_annotations_and_resources():
    async def work():
        async with Client(mcp_server.mcp) as client:
            tools = (await client.list_tools()).tools
            assert len(tools) == 5
            for tool in tools:
                assert tool.name.startswith('sortiestarter_')
                assert tool.output_schema and tool.annotations.destructive_hint is False
            generate = next(t for t in tools if t.name.endswith('generate_mission'))
            assert generate.annotations.read_only_hint is False
            assert 'params' in generate.input_schema['properties']
            resources = (await client.list_resources()).resources
            assert {str(r.uri) for r in resources} == {'sortiestarter://recipe-schema','sortiestarter://user-guide','sortiestarter://integration-guide'}
            schema = await client.read_resource('sortiestarter://recipe-schema')
            assert json.loads(schema.contents[0].text)['x-engine-version'] == __version__
            guide = await client.read_resource('sortiestarter://user-guide')
            assert 'Flying with veteran AI wingmen' in guide.contents[0].text
            integration = await client.read_resource('sortiestarter://integration-guide')
            assert integration.contents[0].text == (mcp_server.ROOT/'docs/MCP.md').read_text()
    anyio.run(work)


def test_catalog_pagination_and_era_map_filters():
    first = call('sortiestarter_list_catalog', {'params':{'kind':'aircraft','limit':2}}).structured_content
    second = call('sortiestarter_list_catalog', {'params':{'kind':'aircraft','limit':2,'offset':first['next_offset']}}).structured_content
    assert first['has_more'] and len(first['items']) == len(second['items']) == 2
    assert {i['key'] for i in first['items']}.isdisjoint(i['key'] for i in second['items'])
    maps = call('sortiestarter_list_catalog', {'params':{'kind':'maps','era':'wwii','limit':50}}).structured_content
    assert 'nttr' not in {i['key'] for i in maps['items']}
    aircraft = call('sortiestarter_list_catalog', {'params':{'kind':'aircraft','era':'wwii','query':'F_16C'}}).structured_content
    assert not aircraft['items']
    boats = call('sortiestarter_list_catalog', {'params':{'kind':'carriers','limit':50}}).structured_content
    assert all(not item['key'].startswith('_') for item in boats['items'])
    germany = call('sortiestarter_get_catalog_item', {'params':{'kind':'maps','key':'germany'}}).structured_content
    assert 'coldwar' in germany['item']['presets']
    caucasus = call('sortiestarter_get_catalog_item', {'params':{'kind':'maps','key':'caucasus'}}).structured_content
    assert caucasus['item']['has_carrier']


@pytest.mark.parametrize('name,args', [
    ('sortiestarter_list_catalog', {'params':{'kind':'maps','era':'bogus'}}),
    ('sortiestarter_list_catalog', {'params':{'kind':'maps','limit':51}}),
    ('sortiestarter_get_catalog_item', {'params':{'kind':'maps','key':'../private'}}),
    ('sortiestarter_validate_recipe', {'params':{'recipe':{'slots':4,'veteran_wingmen':4}}}),
    ('sortiestarter_validate_recipe', {'params':{'recipe':{'slots':'4'}}}),
    ('sortiestarter_validate_recipe', {'params':{'recipe':{'template':'pack_wk_checkout'}}}),
])
def test_bad_inputs_are_actionable_tool_errors(name, args):
    result = call(name,args)
    assert result.is_error and result.content


def test_validation_resolves_templates_without_claiming_a_build():
    result = call('sortiestarter_validate_recipe', {'params':{'recipe':{'template':'qf_bfm','era':'modern'}}})
    assert not result.is_error
    assert result.structured_content['stage'] == 'recipe_fields'
    assert result.structured_content['recipe']['start'] == 'air'
    assert result.structured_content['recipe']['template'] == 'qf_bfm'


@pytest.fixture(scope='module')
def kit(tmp_path_factory):
    directory = tmp_path_factory.mktemp('native-mcp-kit')
    return mission_kit.build_kit(Recipe.from_dict(RECIPE), directory)


def test_kit_manifest_comm_sidecar_and_native_seats_match(kit):
    manifest = kit['manifest']
    assert manifest['mission']['sha256'] == hashlib.sha256(kit['miz'].read_bytes()).hexdigest()
    native = inspect_archive(kit['miz'])
    groups = [g for g in native['groups'] if any(u['skill'] in ('Player','Client') for u in g['units'])]
    assert len(groups) == 1
    assert [u['skill'] for u in groups[0]['units']] == ['Player','High','High','High']
    with zipfile.ZipFile(kit['bundle']) as archive:
        assert archive.testzip() is None
        assert {'mission.miz','manifest.json','comms.json','navigation.json','brief.pdf','brief.md'} <= set(archive.namelist())
        assert json.loads(archive.read('manifest.json')) == manifest
        assert archive.read('mission.miz') == kit['miz'].read_bytes()
        assert '3 veteran AI wingmen' in archive.read('brief.md').decode()
        comms = json.loads(archive.read('comms.json'))
        assert any(row['agency'] == 'Flight' and row['frequency_mhz'] == '305.725' for row in comms)
        with zipfile.ZipFile(io.BytesIO(archive.read('mission.miz'))) as miz:
            for page in [n for n in miz.namelist() if n.startswith('KNEEBOARD/IMAGES/')]:
                assert archive.read('kneeboard/' + Path(page).name) == miz.read(page)
        assert manifest['kit']['kneeboard_pages'] >= 3
        assert all('dtc' not in f['name'] for f in manifest['files'])
        assert {f['name'] for f in manifest['files']} | {'manifest.json'} == set(archive.namelist())


def test_dtc_files_only_when_actually_produced(tmp_path):
    result = mission_kit.build_kit(Recipe.from_dict({**RECIPE,'aircraft':'F_14B_U','bb_dtc':True,'bb_kneeboard':False}), tmp_path)
    with zipfile.ZipFile(result['bundle']) as archive:
        assert 'dtc_setup_card.md' in archive.namelist()
        with zipfile.ZipFile(io.BytesIO(archive.read('mission.miz'))) as miz:
            assert any(n.startswith('DTC/') for n in miz.namelist())
    assert result['manifest']['kit']['dtc']


def test_build_failure_and_success_remove_preview_temporary_files(monkeypatch):
    seen = []
    def fail(recipe, directory):
        seen.append(directory)
        (directory/'partial.miz').write_text('partial')
        raise RuntimeError('private-error-path')
    monkeypatch.setattr(mission_kit, 'build_kit', fail)
    result = call('sortiestarter_generate_mission', {'params':{'recipe':RECIPE}})
    assert result.is_error and 'private-error-path' not in str(result.content)
    assert seen and not seen[0].exists()
    def success(recipe, directory):
        seen.append(directory)
        return {'manifest':{'share_code':'test', 'mission':{'sha256':'0'*64}}}
    monkeypatch.setattr(mission_kit, 'build_kit', success)
    assert mission_kit.generation_preview(Recipe.from_dict(RECIPE)) == {'share_code':'test', 'mission':{'sha256':'0'*64}}
    assert not seen[-1].exists()


def test_mcp_and_downloads_share_website_generation_capacity(monkeypatch):
    capacity = GenerationCapacity(1)
    monkeypatch.setattr(mission_kit.artifact_service,'generation_capacity',capacity)
    with capacity.slot():
        result = call('sortiestarter_generate_mission', {'params':{'recipe':RECIPE}})
        assert result.is_error and 'busy' in str(result.content) and '3 seconds' in str(result.content)
        with TestClient(app,base_url='http://localhost') as client:
            response=client.get('/api/mission-kit',params={'r':encode_recipe(Recipe.from_dict(RECIPE)), 'version':__version__})
            assert response.status_code==503 and response.headers['Retry-After']=='3'


def test_http_download_cleanup_version_guard_and_invalid_code(monkeypatch, kit):
    paths=[]
    def build(recipe,directory):
        paths.append(directory)
        for key in ('bundle','miz'):
            (directory/kit[key].name).write_bytes(kit[key].read_bytes())
        return {**kit,'bundle':directory/kit['bundle'].name,'miz':directory/kit['miz'].name}
    monkeypatch.setattr(mission_kit,'build_kit',build)
    with TestClient(app,base_url='http://localhost') as client:
        params={'r':encode_recipe(Recipe.from_dict(RECIPE)), 'version':__version__}
        response=client.get('/api/mission-kit',params=params)
        assert response.status_code==200 and response.content==kit['bundle'].read_bytes()
        assert paths and not paths[-1].exists()
        assert client.get('/api/mission-kit',params={**params,'version':'0.0.0'}).status_code==409
        assert client.get('/api/mission-kit',params={**params,'r':'broken'}).status_code==400
        assert client.get('/api/mission-kit',params={**params,'format':'../../secret'}).status_code==422
        assert client.get('/api/mission-kit',params={**params,'sha256':'0'*64}).status_code==409
        assert len(paths)==2 and not paths[-1].exists()


def test_http_transport_blocks_bad_hosts_origins_and_large_bodies():
    with TestClient(app,base_url='http://localhost') as client:
        headers={'Accept':'application/json, text/event-stream'}
        rpc={'jsonrpc':'2.0','id':1,'method':'tools/list','params':{}}
        assert client.post('/mcp/',json=rpc,headers={**headers,'Host':'evil.example'}).status_code==421
        assert client.post('/mcp/',json=rpc,headers={**headers,'Origin':'https://evil.example'}).status_code==403
        assert client.post('/mcp/',content='x'*1_000_001,headers={**headers,'Content-Type':'application/json'}).status_code==413
        assert client.post('/mcp/',content=iter([b'x'*500_001,b'x'*500_001]),headers={**headers,'Content-Type':'application/json'}).status_code==413


def test_catalog_owner_routes_mcp_to_published_catalog():
    from server.catalog_owner import replay_target
    assert replay_target('/mcp/','owner','replica')=='owner'
    assert replay_target('/mcp','owner','replica')=='owner'
    assert replay_target('/api/mission-kit','owner','replica')=='owner'


@pytest.fixture(scope='module')
def mcp_site(tmp_path_factory):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    url=f'http://127.0.0.1:{port}'
    directory=tmp_path_factory.mktemp('mcp-http')
    env=dict(os.environ,PUBLIC_BASE_URL=url,PACKS_DATA_DIR=str(directory/'packs'),ANALYTICS_DATA_DIR=str(directory/'analytics'))
    env.pop('PACKS_OWNER_MACHINE',None);env.pop('FLY_MACHINE_ID',None)
    process=subprocess.Popen([sys.executable,'-m','uvicorn','server.app:app','--port',str(port)],
        cwd=Path(__file__).resolve().parent.parent,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:urllib.request.urlopen(url+'/api/health',timeout=1);break
            except Exception:
                if process.poll() is not None:pytest.fail('MCP server failed to start')
                time.sleep(.1)
        else:pytest.fail('MCP server did not become ready')
        yield url
    finally:
        process.terminate();process.wait(timeout=10)


@pytest.mark.parametrize('mode',['auto','legacy'])
def test_real_http_sdk_client_session_modes_resources_and_errors(mcp_site,mode):
    async def work():
        async with Client(mcp_site+'/mcp/',mode=mode) as client:
            assert len((await client.list_tools()).tools)==5
            result=await client.call_tool('sortiestarter_validate_recipe',{'params':{'recipe':RECIPE}})
            assert not result.is_error and result.structured_content['recipe']['veteran_wingmen']==3
            assert json.loads((await client.read_resource('sortiestarter://recipe-schema')).contents[0].text)['x-engine-version']==__version__
            invalid=await client.call_tool('sortiestarter_validate_recipe',{'params':{'recipe':{'map':'missing'}}})
            assert invalid.is_error
    anyio.run(work)


def test_real_http_generation_download_is_the_manifest_native_mission(mcp_site,tmp_path):
    async def work():
        async with Client(mcp_site+'/mcp/') as client:
            result=await client.call_tool('sortiestarter_generate_mission',{'params':{'recipe':RECIPE}})
            assert not result.is_error,str(result.content)
            return result.structured_content
    result=anyio.run(work)
    manifest=result['manifest']
    with urllib.request.urlopen(result['downloads']['mission'],timeout=120) as response:
        mission=response.read()
    assert hashlib.sha256(mission).hexdigest()==manifest['mission']['sha256']
    path=tmp_path/'download.miz';path.write_bytes(mission)
    native=inspect_archive(path)
    groups=[g for g in native['groups'] if any(u['skill'] in ('Player','Client') for u in g['units'])]
    assert [u['skill'] for u in groups[0]['units']]==['Player','High','High','High']
    with urllib.request.urlopen(result['downloads']['kit'],timeout=120) as response:
        with zipfile.ZipFile(io.BytesIO(response.read())) as archive:
            assert archive.read('mission.miz')==mission
            assert json.loads(archive.read('manifest.json'))['mission']==manifest['mission']


def test_cancelled_tool_keeps_capacity_and_cleans_up_after_worker_finishes(monkeypatch):
    import threading
    entered, finish = threading.Event(), threading.Event()
    capacity = GenerationCapacity(1)
    directories = []
    completed = []
    def slow_build(recipe,directory):
        directories.append(directory)
        with capacity.slot():
            entered.set()
            assert finish.wait(10)
        return {'manifest':{'share_code':'cancelled', 'mission':{'sha256':'0'*64}}}
    monkeypatch.setattr(mission_kit,'build_kit',slow_build)
    async def work():
        async with anyio.create_task_group() as tasks:
            async def request():
                with anyio.CancelScope() as scope:
                    scopes.append(scope)
                    await mcp_server.sortiestarter_generate_mission(mcp_server.RecipeInput(recipe=RECIPE))
                completed.append(True)
            scopes=[]
            tasks.start_soon(request)
            while not entered.is_set():
                await anyio.sleep(.01)
            try:
                scopes[0].cancel()
                await anyio.sleep(.02)
                assert not completed, "cancelled request abandoned its native worker"
                with pytest.raises(Exception) as busy:
                    with capacity.slot():
                        pytest.fail('cancelled build released capacity before native worker stopped')
                assert busy.value.status_code==503
                assert directories[0].exists()
            finally:
                finish.set()
        assert not directories[0].exists()
        with capacity.slot():pass
    anyio.run(work)


def test_custom_comm_sidecar_matches_native_flight_frequency(tmp_path):
    result=mission_kit.build_kit(Recipe.from_dict({**RECIPE,'bb_kneeboard':False,'comms':{'flight_common':306.0}}),tmp_path)
    from dcs import lua
    from scripts.audit_library import values
    with zipfile.ZipFile(result['bundle']) as kit:
        rows=json.loads(kit.read('comms.json'))
        flight=next(row for row in rows if row['agency']=='Flight')
        assert flight['frequency_mhz']=='306.000' and 'custom' in flight['notes']
        with zipfile.ZipFile(io.BytesIO(kit.read('mission.miz'))) as miz:
            mission=lua.loads(miz.read('mission').decode())['mission']
        players=[]
        for country in values(mission['coalition']['blue']['country']):
            for group in values(country.get('plane',{}).get('group')):
                if any(u['skill'] in ('Player','Client') for u in values(group['units'])):
                    players.append(group)
        assert len(players)==1 and players[0]['frequency']==float(flight['frequency_mhz'])


def test_failed_http_build_removes_partial_files_and_returns_clean_error(monkeypatch):
    directories=[]
    def fail(recipe,directory):
        directories.append(directory)
        (directory/'partial.miz').write_text('partial')
        raise RuntimeError('private-internal-path')
    monkeypatch.setattr(mission_kit,'build_kit',fail)
    with TestClient(app,base_url='http://localhost') as client:
        response=client.get('/api/mission-kit',params={'r':encode_recipe(Recipe.from_dict(RECIPE)),'version':__version__})
        assert response.status_code==500 and 'private-internal-path' not in response.text
        assert directories and not directories[-1].exists()


def test_public_agent_docs_and_index_match_the_mcp_resource():
    with TestClient(app,base_url='http://localhost') as client:
        guide=client.get('/api/mcp-guide')
        assert guide.status_code==200 and guide.headers['Content-Type'].startswith('text/markdown')
        assert guide.text==(mcp_server.ROOT/'docs/MCP.md').read_text()
        index=client.get('/llms.txt')
        assert index.status_code==200 and __version__ in index.text
        assert '/api/mcp-guide' in index.text and 'sortiestarter://integration-guide' in index.text
        assert guide.headers['Cache-Control']==index.headers['Cache-Control']=='no-store'


def test_original_app_transport_starts_after_application_module_reload():
    import importlib
    import server.app as module
    original = module.app
    importlib.reload(module)
    for application in (original, module.app):
        with TestClient(application, base_url='http://localhost') as client:
            response = client.post('/mcp/', json={'jsonrpc':'2.0','id':1,'method':'tools/list','params':{}},
                                   headers={'Accept':'application/json, text/event-stream', 'Host':'evil.example'})
            assert response.status_code == 421
