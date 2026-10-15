"""Sharing is opt-in, scoped to chosen items and revocable across every route."""
import json
import logging

import pytest
from test_accounts import client, settings, login, headers, saved, ORIGIN
from server import account_routes, account_store


def selection(client, account, seed=71):
    response=client.post('/api/account/selections',json={'kind':'recipe','name':'Private <Phantom>',
                         'recipe':{'seed':seed}},headers=headers(account))
    assert response.status_code==200,response.text
    return response.json()['id']


def test_sharing_exposes_only_chosen_missions_and_safe_metadata(client,monkeypatch):
    monkeypatch.setenv('GA_MEASUREMENT_ID','G-B406V24KN5')
    account,_,_=login(client,monkeypatch)
    sid=selection(client,account)
    second=selection(client,account,72)
    assert client.get('/api/account/library').json()['page_path'] is None
    assert not any(i['share_path'] for i in client.get('/api/account/library').json()['items'])
    assert client.post('/api/account/shares',json={'kind':'selection','id':sid}).status_code==403
    share=client.post('/api/account/shares',json={'kind':'selection','id':sid},headers=headers(account)).json()['path']
    assert client.post('/api/account/shares',json={'kind':'selection','id':sid},headers=headers(account)).json()['path']==share
    page=client.post('/api/account/shared-page',headers=headers(account)).json()['path']
    guest=client.__class__(client.app,base_url=ORIGIN)
    with guest:
        result=guest.get('/api'+page)
        assert result.status_code==200
        data=result.json();assert len(data['items'])==1
        assert data['items'][0]['title']=='Private <Phantom>'
        assert data['items'][0]['category']=='setup'
        assert data['items'][0]['open_path'].startswith('/?r=')
        text=json.dumps(data)
        for secret in (account['csrf'],account['user']['id'],'12345','discord_id','manifest','user_id'):
            assert secret not in text
        assert guest.get('/api/account/library').status_code==401
        assert guest.post('/api/account/shares',json={'kind':'selection','id':second}).status_code==401
        html=guest.get(share)
        assert html.status_code==200 and 'Private &lt;Phantom&gt;' in html.text and '<Phantom>' not in html.text
        for path in ('/my-missions',share,page,'/api'+share,'/api'+page):
            response=guest.get(path)
            assert 'googletagmanager.com' not in response.text
            assert 'gtag(' not in response.text
            assert response.headers['cache-control']=='no-store'
            assert response.headers['referrer-policy']=='no-referrer'
            assert response.headers['x-robots-tag']=='noindex, nofollow'
    assert client.delete('/api/account/shares/selection/'+sid,headers=headers(account)).status_code==200
    assert client.get('/api'+share).status_code==404
    assert client.get(share).status_code==404
    assert client.get('/api'+page).json()['items']==[]


def test_shared_original_files_keep_exact_bytes_and_revocation_cascades(client,monkeypatch):
    account,_,_=login(client,monkeypatch)
    generated,mid=saved(client,monkeypatch,account)
    share=client.post('/api/account/shares',json={'kind':'mission','id':mid},headers=headers(account)).json()['path']
    kit=client.get('/api/account/missions/'+mid+'/download?format=kit').content
    client.cookies.clear()
    assert client.get('/api'+share+'/download?format=miz').content==generated.content
    assert client.get('/api'+share+'/download?format=kit').content==kit
    assert 'recipe' not in client.get('/api'+share).json()['items'][0]  # Builder link is the explicit settings projection.
    account,_,_=login(client,monkeypatch)
    page=client.post('/api/account/shared-page',headers=headers(account)).json()['path']
    assert client.delete('/api/account/missions/'+mid,headers=headers(account)).status_code==200
    assert client.get('/api'+share+'/download').status_code==404
    assert client.get('/api'+page).json()['items']==[]


def test_owner_isolation_stop_all_and_new_links_do_not_reactivate_old_links(client,monkeypatch):
    account,_,_=login(client,monkeypatch);sid=selection(client,account)
    share=client.post('/api/account/shares',json={'kind':'selection','id':sid},headers=headers(account)).json()['path']
    page=client.post('/api/account/shared-page',headers=headers(account)).json()['path']
    other,_,_=login(client,monkeypatch,'67890')
    assert client.post('/api/account/shares',json={'kind':'selection','id':sid},headers=headers(other)).status_code==404
    assert client.delete('/api/account/shares/selection/'+sid,headers=headers(other)).status_code==404
    assert client.get('/api/account/library').json()['items']==[]
    account,_,_=login(client,monkeypatch)
    assert client.delete('/api/account/shared-page',headers=headers(account)).status_code==200
    assert client.get('/api'+page).status_code==404 and client.get('/api'+share).status_code==404
    newpage=client.post('/api/account/shared-page',headers=headers(account)).json()['path']
    newshare=client.post('/api/account/shares',json={'kind':'selection','id':sid},headers=headers(account)).json()['path']
    assert newpage!=page and newshare!=share
    client.delete('/api/account',headers=headers(account))
    assert client.get('/api'+newpage).status_code==404 and client.get('/api'+newshare).status_code==404


def test_my_missions_routes_auth_return_and_owner_routing(client,monkeypatch):
    response=client.get('/my-missions')
    assert response.status_code==200 and 'YOUR FLIGHTLINE' in response.text
    assert "'Source Sans 3'" in response.text and '--bg: #F2F2F7' in response.text
    assert account_routes.safe_return('/my-missions')=='/my-missions'
    assert account_routes.safe_return('/my-missions/../../evil')=='/'
    monkeypatch.setenv('ACCOUNTS_OWNER_MACHINE','owner');monkeypatch.setenv('FLY_MACHINE_ID','replica')
    for path in ('/my-missions','/pilots/'+'a'*32,'/shared/'+'a'*32,'/api/shared/'+'a'*32,'/api/pilots/'+'a'*32,'/api/account/library'):
        replay=client.get(path)
        assert replay.headers['fly-replay']=='instance=owner'
    record=logging.LogRecord('access',20,'',0,'%s %s %s',('client','GET','/shared/'+'a'*32),None)
    account_routes.AuthAccessFilter().filter(record)
    assert record.args[2]=='/[shared-link]'
