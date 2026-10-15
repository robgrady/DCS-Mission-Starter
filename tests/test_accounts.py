"""Optional login, private ownership and exact mission archives across sessions."""
import hashlib
import json
from pathlib import Path
import sqlite3
from urllib.parse import parse_qs, urlsplit
import zipfile

import pytest
from fastapi.testclient import TestClient

from missiongen import Recipe, __version__
from server.app import app
from server import account_routes as routes, account_store as store

ORIGIN = 'https://sortiestarter.com'


@pytest.fixture(autouse=True)
def settings(monkeypatch, tmp_path):
    monkeypatch.setenv('DISCORD_BASE_URL', ORIGIN)
    monkeypatch.setenv('DISCORD_CLIENT_ID', '1547542914651922452')
    monkeypatch.setenv('DISCORD_CLIENT_SECRET', 'test-secret-not-a-real-credential')
    monkeypatch.setenv('ACCOUNTS_DATA_DIR', str(tmp_path / 'accounts'))
    monkeypatch.delenv('FLY_MACHINE_ID', raising=False)
    monkeypatch.delenv('ACCOUNTS_OWNER_MACHINE', raising=False)


@pytest.fixture
def client():
    with TestClient(app, base_url=ORIGIN, follow_redirects=False) as client:
        yield client


def login(client, monkeypatch, discord_id='12345'):
    calls = []
    def provider(url, data=None, token=None):
        calls.append((url, data, token))
        if data is not None:
            return {'access_token': 'private-provider-token', 'refresh_token': 'private-refresh-token'}
        return {'id': discord_id, 'global_name': 'Pilot <one>', 'username': 'pilot'}
    monkeypatch.setattr(routes, 'discord_json', provider)
    start = client.get('/auth/discord', params={'return_to': '/?v=builder&step=review'})
    query = parse_qs(urlsplit(start.headers['location']).query)
    assert query['client_id'] == ['1547542914651922452']
    assert query['scope'] == ['identify']
    assert query['redirect_uri'] == [ORIGIN + '/auth/discord/callback']
    assert 'HttpOnly' in start.headers['set-cookie'] and 'Secure' in start.headers['set-cookie']
    response = client.get('/auth/discord/callback', params={'state': query['state'][0], 'code': 'test-code'})
    assert response.headers['location'] == ORIGIN + '/?v=builder&step=review&auth=signed_in'
    assert 'HttpOnly' in response.headers['set-cookie'] and 'SameSite=lax' in response.headers['set-cookie']
    user = client.get('/api/account').json()
    return user, calls, query['state'][0]


def headers(account):
    return {'Origin': ORIGIN, 'X-CSRF-Token': account['csrf']}


def fake_kit(recipe, directory):
    miz = directory / 'mission.miz'
    with zipfile.ZipFile(miz, 'w') as z:
        z.writestr('mission', 'exact original mission')
    bundle = directory / 'mission_kit.zip'
    with zipfile.ZipFile(bundle, 'w') as z:
        z.write(miz, 'mission.miz')
        z.writestr('brief.md', 'matching original briefing')
    manifest = {'app_version': __version__, 'recipe': recipe.to_dict(), 'kit': {}, 'warnings': [],
                'mission': {'sha256': hashlib.sha256(miz.read_bytes()).hexdigest()}}
    return {'manifest': manifest, 'miz': miz, 'bundle': bundle}


def saved(client, monkeypatch, account):
    monkeypatch.setattr(routes.mission_kit, 'build_kit', fake_kit)
    response = client.post('/api/account/generate', json={'recipe': {}}, headers=headers(account))
    assert response.status_code == 200, response.text
    return response, response.headers['x-saved-mission']


def test_login_preserves_stable_identity_and_stores_no_provider_tokens(client, monkeypatch):
    user, calls, _ = login(client, monkeypatch)
    assert user['user']['name'] == 'Pilot <one>'
    assert calls[0][1]['grant_type'] == 'authorization_code'
    assert calls[0][1]['redirect_uri'] == ORIGIN + '/auth/discord/callback'
    assert calls[1][2] == 'private-provider-token'
    assert client.patch('/api/account', json={'name': 'Custom name'}, headers=headers(user)).status_code == 200
    again, _, _ = login(client, monkeypatch)
    assert again['user']['id'] == user['user']['id']
    assert again['user']['name'] == 'Custom name'
    assert again['csrf'] != user['csrf']
    db_bytes = (Path(routes.os.environ['ACCOUNTS_DATA_DIR']) / 'accounts.sqlite3').read_bytes()
    for secret in (b'private-provider-token', b'private-refresh-token', b'test-secret-not-a-real-credential', b'test-code'):
        assert secret not in db_bytes


@pytest.mark.parametrize('change', ['wrong', 'missing', 'expired', 'replayed'])
def test_callback_rejects_unbound_expired_and_replayed_state(client, monkeypatch, change):
    _, _, state = login(client, monkeypatch)
    if change != 'replayed':
        start = client.get('/auth/discord')
        state = parse_qs(urlsplit(start.headers['location']).query)['state'][0]
    client.cookies.set(routes.STATE_COOKIE, state, domain='sortiestarter.com', path='/')
    if change == 'wrong': state = 'another-state'
    if change == 'missing': state = ''
    if change == 'expired':
        with store.database() as db: db.execute('UPDATE oauth_states SET expires=0')
    def forbidden(*args, **kwargs): raise AssertionError('Provider must not be called')
    monkeypatch.setattr(routes, 'discord_json', forbidden)
    assert client.get('/auth/discord/callback', params={'code':'test', 'state':state}).headers['location'].endswith('auth=failed')


def test_cancelled_login_returns_to_builder_without_creating_account(client):
    start = client.get('/auth/discord', params={'return_to':'/?v=builder&step=flight'})
    state = parse_qs(urlsplit(start.headers['location']).query)['state'][0]
    response = client.get('/auth/discord/callback', params={'state':state, 'error':'access_denied'})
    assert response.headers['location'] == ORIGIN + '/?v=builder&step=flight&auth=cancelled'
    assert client.get('/api/account').json()['user'] is None


@pytest.mark.parametrize('target', ['https://evil.test', '//evil.test', '/\\evil.test', '/auth/discord/callback?code=private'])
def test_login_does_not_accept_external_return_destinations(client, target):
    assert routes.safe_return(target) == '/'


@pytest.mark.parametrize('origin,token', [(None,None), ('https://evil.test','correct'), (ORIGIN,'wrong')])
def test_csrf_blocks_all_private_mutations(client, monkeypatch, origin, token):
    user, _, _ = login(client, monkeypatch)
    request_headers = {}
    if origin: request_headers['Origin'] = origin
    if token: request_headers['X-CSRF-Token'] = user['csrf'] if token == 'correct' else token
    for method, path, body in [('POST','/api/account/logout',{}), ('PATCH','/api/account',{'name':'changed'}),
                               ('DELETE','/api/account',{}), ('POST','/api/account/generate',{'recipe':{}}),
                               ('DELETE','/api/account/missions/other',{}), ('PATCH','/api/account/missions/other',{'name':'x'})]:
        assert client.request(method, path, headers=request_headers, json=body).status_code == 403
    assert client.get('/api/account').json()['user']['name'] == 'Pilot <one>'


def test_expired_and_logged_out_sessions_stop_working(client, monkeypatch):
    user, _, _ = login(client, monkeypatch)
    old = client.cookies.get(routes.COOKIE)
    assert client.post('/api/account/logout', headers=headers(user)).status_code == 200
    client.cookies.set(routes.COOKIE, old)
    assert client.get('/api/account/missions').status_code == 401
    login(client, monkeypatch)
    with store.database() as db: db.execute('UPDATE sessions SET expires=0')
    assert client.get('/api/account').json()['user'] is None


def test_private_downloads_keep_original_bytes_and_work_after_restart(client, monkeypatch):
    user, _, _ = login(client, monkeypatch)
    generated, mid = saved(client, monkeypatch, user)
    def forbidden(*args, **kwargs): raise AssertionError('Downloading must not regenerate')
    monkeypatch.setattr(routes.mission_kit, 'build_kit', forbidden)
    monkeypatch.setattr(routes.artifact_service, 'generate', forbidden)
    assert client.get(f'/api/account/missions/{mid}/download').content == generated.content
    kit = client.get(f'/api/account/missions/{mid}/download?format=kit')
    assert kit.status_code == 200
    import io
    with zipfile.ZipFile(io.BytesIO(kit.content)) as z:
        assert z.read('mission.miz') == generated.content
        assert z.read('brief.md') == b'matching original briefing'
    with TestClient(app, base_url=ORIGIN) as restarted:
        restarted.cookies.set(routes.COOKIE, client.cookies.get(routes.COOKIE))
        assert restarted.get(f'/api/account/missions/{mid}/download').content == generated.content
    item = client.get('/api/account/missions').json()['missions'][0]
    assert item['recipe'] == Recipe.from_dict({}).to_dict()
    assert item['version'] == __version__
    assert item['sha256'] == hashlib.sha256(generated.content).hexdigest()


def test_another_user_cannot_list_read_modify_or_delete_missions(client, monkeypatch):
    one, _, _ = login(client, monkeypatch)
    _, mid = saved(client, monkeypatch, one)
    two, _, _ = login(client, monkeypatch, discord_id='67890')
    assert client.get('/api/account/missions').json()['missions'] == []
    assert client.get(f'/api/account/missions/{mid}/download').status_code == 404
    assert client.patch(f'/api/account/missions/{mid}', json={'name':'stolen'}, headers=headers(two)).status_code == 404
    assert client.delete(f'/api/account/missions/{mid}', headers=headers(two)).status_code == 404
    login(client, monkeypatch)
    assert client.get(f'/api/account/missions/{mid}/download').status_code == 200


def test_export_delete_and_rename_do_not_affect_other_accounts(client, monkeypatch):
    user, _, _ = login(client, monkeypatch)
    _, mid = saved(client, monkeypatch, user)
    assert client.patch(f'/api/account/missions/{mid}', json={'name':'Renamed'}, headers=headers(user)).status_code == 200
    exported = client.get('/api/account/export').json()
    assert exported['missions'][0]['title'] == 'Renamed'
    assert 'csrf' not in exported['profile']
    assert client.delete('/api/account', headers=headers(user)).status_code == 200
    assert store.list_missions(user['user']['id']) == []
    assert client.get('/api/account/missions').status_code == 401


@pytest.mark.parametrize('limit', ['MAX_MISSIONS','MAX_USER_BYTES','MAX_TOTAL_BYTES','MAX_KIT_BYTES'])
def test_quota_failure_never_creates_partial_archive(client, monkeypatch, limit):
    user, _, _ = login(client, monkeypatch)
    monkeypatch.setattr(routes.mission_kit, 'build_kit', fake_kit)
    monkeypatch.setattr(store, limit, 0)
    response = client.post('/api/account/generate', json={'recipe':{}}, headers=headers(user))
    assert response.status_code == 409
    assert store.list_missions(user['user']['id']) == []


def test_storage_failure_is_recoverable_and_does_not_sign_out_user(client, monkeypatch):
    user, _, _ = login(client, monkeypatch)
    monkeypatch.setattr(routes.mission_kit, 'build_kit', fake_kit)
    original = store.save_mission
    def fail(*args): raise sqlite3.OperationalError('database or disk is full')
    monkeypatch.setattr(store, 'save_mission', fail)
    response = client.post('/api/account/generate', json={'recipe':{}}, headers=headers(user))
    assert response.status_code == 503
    assert store.list_missions(user['user']['id']) == []
    monkeypatch.setattr(store, 'save_mission', original)
    saved(client, monkeypatch, user)


def test_account_owner_routing_never_creates_replica_accounts(client, monkeypatch, tmp_path):
    monkeypatch.setenv('ACCOUNTS_OWNER_MACHINE', 'account-owner')
    monkeypatch.setenv('FLY_MACHINE_ID', 'replica')
    for path in ['/auth/discord','/auth/discord/callback','/api/account','/api/account/missions','/api/account/export']:
        response = client.get(path)
        assert response.headers['fly-replay'] == 'instance=account-owner'
        assert response.headers['cache-control'] == 'no-store'
    assert not (tmp_path / 'accounts').exists()


def test_private_requests_are_uncacheable_and_body_size_is_bounded(client, monkeypatch):
    user, _, _ = login(client, monkeypatch)
    assert client.get('/api/account').headers['cache-control'] == 'no-store'
    assert client.get('/api/account').headers['referrer-policy'] == 'no-referrer'
    response = client.post('/api/account/generate', content=b'x'*100001, headers=headers(user))
    assert response.status_code == 413
    assert response.headers['cache-control'] == 'no-store'


def test_missing_configuration_leaves_guest_generation_available(client, monkeypatch):
    monkeypatch.delenv('DISCORD_CLIENT_SECRET')
    assert client.get('/api/account').json()['enabled'] is False
    assert client.get('/auth/discord').status_code == 503
    # Guest API still performs its original recipe validation, independent of auth.
    assert client.post('/api/generate', json={'recipe':{'map':'not-a-map'}}).status_code == 400


def test_uvicorn_access_log_redacts_oauth_codes_and_state():
    import logging
    record = logging.LogRecord('uvicorn.access', logging.INFO, '', 0, '%s - "%s %s HTTP/%s" %s',
        ('127.0.0.1','GET','/auth/discord/callback?code=private-code&state=private-state','1.1',303), None)
    assert routes.AuthAccessFilter().filter(record)
    assert 'private-code' not in record.getMessage()
    assert 'private-state' not in record.getMessage()
    assert '/auth/discord/callback' in record.getMessage()


def test_internal_http_scheme_does_not_loop_behind_https_proxy(monkeypatch):
    with TestClient(app, base_url='http://sortiestarter.com', follow_redirects=False) as client:
        assert client.get('/auth/discord').headers['location'].startswith('https://discord.com/oauth2/authorize?')


def test_provider_failure_does_not_create_session_or_leak_details(client, monkeypatch, caplog):
    import urllib.error
    start = client.get('/auth/discord')
    state = parse_qs(urlsplit(start.headers['location']).query)['state'][0]
    def fail(*args, **kwargs):
        raise urllib.error.URLError('private-provider-diagnostic')
    monkeypatch.setattr(routes, 'discord_json', fail)
    response = client.get('/auth/discord/callback', params={'state':state, 'code':'private-code'})
    assert response.headers['location'] == ORIGIN+'/?auth=failed'
    assert client.get('/api/account').json()['user'] is None
    assert 'private-provider-diagnostic' not in caplog.text + response.text


def test_real_generator_archives_one_matching_mission_and_kit(client, monkeypatch):
    import io
    user, _, _ = login(client, monkeypatch)
    response = client.post('/api/account/generate', headers=headers(user), json={'recipe':{
        'map':'caucasus', 'era':'coldwar', 'aircraft':'F_4E_45MC', 'template':'qf_bfm',
        'seed':19, 'bb_dressing':False, 'bb_kneeboard':False}})
    assert response.status_code == 200, response.text
    mid = response.headers['x-saved-mission']
    kit = client.get(f'/api/account/missions/{mid}/download?format=kit')
    with zipfile.ZipFile(io.BytesIO(kit.content)) as archive:
        assert archive.read('mission.miz') == response.content
        manifest = json.loads(archive.read('manifest.json'))
        assert manifest['mission']['sha256'] == hashlib.sha256(response.content).hexdigest()
        assert 'brief.pdf' in archive.namelist() and 'brief.md' in archive.namelist()


def test_saved_selection_roundtrip_dedup_ownership_quota_and_export(client, monkeypatch):
    account, _, _ = login(client, monkeypatch)
    recipe = {'map':'caucasus','era':'coldwar','aircraft':'F_4E_45MC','slots':4,'veteran_wingmen':3,'seed':71}
    body = {'kind':'recipe','name':'My four-ship','recipe':recipe}
    assert client.post('/api/account/selections',json=body).status_code == 403
    response = client.post('/api/account/selections',json=body,headers=headers(account))
    assert response.status_code == 200, response.text
    sid = response.json()['id']
    monkeypatch.setattr(store,'MAX_SELECTIONS',1)
    assert client.post('/api/account/selections',json=body,headers=headers(account)).json()['id'] == sid
    assert client.post('/api/account/selections',json={**body,'recipe':{**recipe,'seed':72}},headers=headers(account)).status_code == 409
    item = client.get('/api/account/selections').json()['selections'][0]
    assert item['payload']['recipe']['veteran_wingmen'] == 3
    assert item['payload']['recipe']['seed'] == 71
    assert item['title'] == 'My four-ship'
    assert client.get('/api/account/export').json()['selections'] == [item]
    assert client.get('/api/account/missions').json()['missions'] == []
    other, _, _ = login(client, monkeypatch, '67890')
    assert client.get('/api/account/selections').json()['selections'] == []
    for method in ('patch','delete'):
        kw = {'json':{'name':'Intruder'}} if method == 'patch' else {}
        assert getattr(client,method)('/api/account/selections/'+sid,headers=headers(other),**kw).status_code == 404
    account, _, _ = login(client, monkeypatch)
    assert client.patch('/api/account/selections/'+sid,json={'name':'Renamed'},headers=headers(account)).status_code == 200
    assert client.get('/api/account/selections').json()['selections'][0]['title'] == 'Renamed'
    assert client.delete('/api/account/selections/'+sid,headers=headers(account)).status_code == 200
    assert client.get('/api/account/selections').json()['selections'] == []
    client.post('/api/account/selections',json=body,headers=headers(account))
    client.delete('/api/account',headers=headers(account))
    account, _, _ = login(client, monkeypatch)
    assert client.get('/api/account/selections').json()['selections'] == []


def test_pack_references_validate_published_missions_without_archiving_files(client, monkeypatch, tmp_path):
    account, _, _ = login(client, monkeypatch)
    pack = {'id':'test_pack','label':'Published collection','version':'1.2.3',
            'events':[{'miz':'missions/one.miz','label':'First sortie'}]}
    monkeypatch.setattr(routes.packs,'list_packs',lambda:[pack])
    mission = tmp_path/'one.miz';mission.write_bytes(b'published mission')
    monkeypatch.setattr(routes.packs,'get_file',lambda pid,path:mission if path=='missions/one.miz' else None)
    for path in (None,'missions/one.miz'):
        response = client.post('/api/account/selections',json={'kind':'pack','pack_id':'test_pack','path':path},headers=headers(account))
        assert response.status_code == 200, response.text
    selections = client.get('/api/account/selections').json()['selections']
    assert len(selections) == 2
    assert {s['title'] for s in selections} == {'Published collection','First sortie'}
    assert all(s['payload']['pack_version']=='1.2.3' for s in selections)
    assert client.get('/api/account/missions').json()['missions'] == []
    for body in ({'kind':'pack','pack_id':'missing'}, {'kind':'pack','pack_id':'test_pack','path':'../secret'},
                 {'kind':'pack','pack_id':'test_pack','path':'https://evil.example/one.miz'},
                 {'kind':'recipe','recipe':{'seed':'invalid'}}, {'kind':'recipe','recipe':{},'pack_id':'test_pack'}):
        assert client.post('/api/account/selections',json=body,headers=headers(account)).status_code in (400,404,422)
    monkeypatch.setattr(routes.packs,'list_packs',lambda:[])
    assert len(client.get('/api/account/selections').json()['selections']) == 2
    assert client.post('/api/account/selections',json={'kind':'pack','pack_id':'test_pack'},headers=headers(account)).status_code == 404
