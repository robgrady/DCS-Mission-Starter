"""Optional Discord sign-in and private mission archives; guests keep all existing APIs."""
import hmac
import json
import logging
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
from typing import Literal
from urllib.parse import urlencode, urlsplit
import urllib.error
import urllib.request

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from pydantic import BaseModel, Field, field_validator
from starlette.background import BackgroundTask

from . import account_store as store
from . import artifact_service, mission_kit
from .mission_routes import GenerateRequest
from missiongen import Recipe, packs

router = APIRouter()
log = logging.getLogger('missionstarter.accounts')
COOKIE = '__Host-ss_account'
STATE_COOKIE = '__Host-ss_oauth'
NO_STORE = {'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer'}


class AuthAccessFilter(logging.Filter):
    """Uvicorn must not write authorization codes/state into access logs."""
    def filter(self, record):
        if isinstance(record.args, tuple) and len(record.args) >= 3:
            values = list(record.args)
            if isinstance(values[2], str) and values[2].startswith('/auth/discord'):
                values[2] = values[2].split('?', 1)[0]
                record.args = tuple(values)
        return True


logging.getLogger('uvicorn.access').addFilter(AuthAccessFilter())


def base_url():
    value = os.environ.get('DISCORD_BASE_URL', '').rstrip('/')
    parsed = urlsplit(value)
    # Explicit canonical origin; never construct OAuth redirects from Host headers.
    if parsed.scheme != 'https' or not parsed.netloc or parsed.path or parsed.query or parsed.fragment or parsed.username:
        return None
    return value


def enabled():
    return bool(base_url() and os.environ.get('DISCORD_CLIENT_ID', '').isdigit()
                and os.environ.get('DISCORD_CLIENT_SECRET'))


def require_user(request: Request):
    if not enabled():
        raise HTTPException(503, 'Discord sign-in is not configured yet.')
    user = store.session(request.cookies.get(COOKIE))
    if user is None:
        raise HTTPException(401, 'Sign in with Discord to access your missions.')
    if request.method not in ('GET', 'HEAD'):
        if request.headers.get('origin') != base_url() or not hmac.compare_digest(
                request.headers.get('x-csrf-token', '').encode(), user['csrf'].encode()):
            raise HTTPException(403, 'Your session changed. Reload the page and try again.')
    return user


def safe_return(value):
    # Only app-root query strings are needed; reject redirects, backslashes,
    # control characters and credential/callback query leakage.
    return value if (len(value) <= 100000 and (value == '/' or value.startswith('/?'))
                     and '\\' not in value and not any(ord(c) < 32 for c in value)) else '/'


def discord_json(url, data=None, token=None):
    headers = {'User-Agent': 'SortieStarter/DiscordLogin', 'Accept': 'application/json'}
    if data is not None:
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
    if token:
        headers['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request(url, data=urlencode(data).encode() if data is not None else None, headers=headers)
    # urllib does not log response bodies/tokens. HTTP errors are deliberately
    # translated into a generic retry message, with no secrets or auth codes.
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read(65536))


@router.get('/auth/discord')
def discord_login(request: Request, return_to: str = '/'):
    if not enabled():
        raise HTTPException(503, 'Discord sign-in is not configured yet.')
    if request.url.hostname != urlsplit(base_url()).hostname:
        return RedirectResponse(base_url() + '/auth/discord?' + urlencode({'return_to': safe_return(return_to)}), headers=NO_STORE)
    state = store.start_login(safe_return(return_to))
    response = RedirectResponse('https://discord.com/oauth2/authorize?' + urlencode({
        'client_id': os.environ['DISCORD_CLIENT_ID'], 'response_type': 'code',
        'scope': 'identify', 'state': state, 'redirect_uri': base_url() + '/auth/discord/callback'}), headers=NO_STORE)
    response.set_cookie(STATE_COOKIE, state, max_age=store.STATE_TTL, secure=True,
                        httponly=True, samesite='lax', path='/')
    return response


@router.get('/auth/discord/callback')
def discord_callback(request: Request, state: str = '', code: str = '', error: str = ''):
    if not enabled():
        raise HTTPException(503, 'Discord sign-in is not configured yet.')
    cookie = request.cookies.get(STATE_COOKIE, '')
    target = None
    if state and len(state) <= 128 and cookie and hmac.compare_digest(cookie.encode(), state.encode()):
        target = store.consume_login(state)
    response = RedirectResponse(base_url() + '/?auth=failed', status_code=303, headers=NO_STORE)
    response.delete_cookie(STATE_COOKIE, path='/', secure=True, httponly=True, samesite='lax')
    if target is None:
        return response
    if error:
        response.headers['location'] = base_url() + target + ('&' if '?' in target else '?') + 'auth=cancelled'
        return response
    if not code or len(code) > 2048:
        return response
    try:
        tokens = discord_json('https://discord.com/api/oauth2/token', {
            'client_id': os.environ['DISCORD_CLIENT_ID'], 'client_secret': os.environ['DISCORD_CLIENT_SECRET'],
            'grant_type': 'authorization_code', 'code': code, 'redirect_uri': base_url() + '/auth/discord/callback'})
        access = tokens.get('access_token') if isinstance(tokens, dict) else None
        if not isinstance(access, str) or not access:
            return response
        identity = discord_json('https://discord.com/api/users/@me', token=access)
        if not isinstance(identity, dict):
            return response
        discord_id = identity.get('id', '')
        name = identity.get('global_name') or identity.get('username')
        if not isinstance(discord_id, str) or not discord_id.isdigit() or not 1 <= len(discord_id) <= 32 or not isinstance(name, str) or not name.strip():
            return response
        token = store.sign_in(discord_id, name.strip()[:80])
        # Rotate any prior local session on successful authentication.
        old_token = request.cookies.get(COOKIE)
        if old_token:
            store.sign_out(old_token)
        response.set_cookie(COOKIE, token, max_age=store.SESSION_TTL, secure=True, httponly=True, samesite='lax', path='/')
        response.headers['location'] = base_url() + target + ('&' if '?' in target else '?') + 'auth=signed_in'
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, TypeError, OSError):
        log.warning('Discord sign-in did not complete; retry required')
    return response


@router.get('/api/account')
def account(request: Request):
    user = store.session(request.cookies.get(COOKIE)) if enabled() else None
    return {'enabled': enabled(), 'user': ({'id': user['id'], 'name': user['name'],
            'created_at': user['created_at']} if user else None),
            'csrf': user['csrf'] if user else None, 'limits': {'missions': store.MAX_MISSIONS, 'bytes': store.MAX_USER_BYTES,
                                                            'selections': store.MAX_SELECTIONS}}


@router.post('/api/account/logout')
def logout(request: Request, user=Depends(require_user)):
    store.sign_out(request.cookies[COOKIE])
    response = JSONResponse({'ok': True})
    response.delete_cookie(COOKIE, path='/', secure=True, httponly=True, samesite='lax')
    return response


class NameRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)

    @field_validator('name')
    @classmethod
    def trim(cls, value):
        value = value.strip()
        if not value or any(ord(c) < 32 for c in value):
            raise ValueError('Enter a name without control characters.')
        return value


@router.patch('/api/account')
def profile(req: NameRequest, user=Depends(require_user)):
    store.rename_user(user['id'], req.name)
    return {'ok': True}


@router.delete('/api/account')
def delete_profile(request: Request, user=Depends(require_user)):
    store.delete_user(user['id'])
    response = JSONResponse({'ok': True})
    response.delete_cookie(COOKIE, path='/', secure=True, httponly=True, samesite='lax')
    return response


@router.get('/api/account/missions')
def missions(user=Depends(require_user)):
    return {'missions': store.list_missions(user['id'])}


@router.get('/api/account/export')
def export_profile(user=Depends(require_user)):
    return JSONResponse({'profile': {k: user[k] for k in ('id', 'discord_id', 'name', 'created_at')},
                         'missions': store.list_missions(user['id']),
                         'selections': store.list_selections(user['id'])}, headers={
                             'Content-Disposition': 'attachment; filename="sortie-starter-profile.json"'})


class SelectionRequest(BaseModel):
    model_config = {'extra': 'forbid'}
    kind: Literal['recipe', 'pack']
    name: str = Field(default='', max_length=80)
    recipe: dict | None = None
    pack_id: str | None = Field(default=None, pattern=r'^[a-z0-9][a-z0-9_-]{0,99}$')
    path: str | None = Field(default=None, max_length=512)


@router.get('/api/account/selections')
def selections(user=Depends(require_user)):
    return {'selections': store.list_selections(user['id'])}


@router.post('/api/account/selections')
def save_selection(req: SelectionRequest, user=Depends(require_user)):
    if any(ord(c) < 32 for c in req.name):
        raise HTTPException(400, 'Enter a name without control characters.')
    if req.kind == 'recipe':
        if req.recipe is None or req.pack_id is not None or req.path is not None:
            raise HTTPException(400, 'Choose mission settings to save.')
        try:
            recipe = Recipe.from_dict(req.recipe)
        except artifact_service.USER_ERRORS as exc:
            raise HTTPException(400, str(exc)) from exc
        payload = {'kind': 'recipe', 'recipe': recipe.to_dict()}
        title = f'{recipe.map} · {recipe.aircraft} · {recipe.template or recipe.mission_kind}'
    else:
        if not req.pack_id or req.recipe is not None:
            raise HTTPException(400, 'Choose a published Library collection.')
        pack = next((p for p in packs.list_packs() if p['id'] == req.pack_id), None)
        if not pack:
            raise HTTPException(404, 'This collection is no longer published. Refresh the Library.')
        event = next((e for e in pack.get('events', []) if e.get('miz') == req.path), None) if req.path else None
        if req.path and (not event or not packs.get_file(req.pack_id, req.path)):
            raise HTTPException(404, 'This published mission is unavailable. Refresh the Library.')
        payload = {'kind': 'pack', 'pack_id': req.pack_id, 'path': req.path, 'pack_version': pack.get('version')}
        title = (event.get('label') if event else pack.get('label')) or req.pack_id
    try:
        sid = store.save_selection(user['id'], (req.name.strip() or title)[:80], payload)
    except store.QuotaError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {'id': sid}


@router.patch('/api/account/selections/{sid}')
def rename_selection(sid: str, req: NameRequest, user=Depends(require_user)):
    if not store.rename_selection(user['id'], sid, req.name):
        raise HTTPException(404, 'Saved selection not found.')
    return {'ok': True}


@router.delete('/api/account/selections/{sid}')
def delete_selection(sid: str, user=Depends(require_user)):
    if not store.delete_selection(user['id'], sid):
        raise HTTPException(404, 'Saved selection not found.')
    return {'ok': True}


@router.post('/api/account/generate')
def generate_saved(req: GenerateRequest, user=Depends(require_user)):
    directory = Path(tempfile.mkdtemp(prefix='sortie-saved-'))
    try:
        recipe = Recipe.from_dict(req.recipe)
        result = mission_kit.build_kit(recipe, directory)
        title = f'{recipe.map} · {recipe.aircraft} · {recipe.template or recipe.mission_kind}'[:80]
        item = store.save_mission(user['id'], title, result)
        from missiongen import analytics
        analytics.record('generate', req.source, recipe, visitor=req.visitor)
        filename = f'{recipe.map}_{recipe.era}_{recipe.aircraft}_{recipe.template or "starter"}_{recipe.seed}.miz'
        return FileResponse(result['miz'], filename=filename, media_type='application/zip', headers={
            'X-Saved-Mission': item['id'], 'X-Kit': json.dumps(result['manifest']['kit']),
            'X-Warnings': artifact_service._header_safe('; '.join(result['manifest']['warnings']))[:900]},
            background=BackgroundTask(shutil.rmtree, directory, ignore_errors=True))
    except HTTPException:
        shutil.rmtree(directory, ignore_errors=True)
        raise
    except artifact_service.USER_ERRORS as exc:
        shutil.rmtree(directory, ignore_errors=True)
        raise HTTPException(400, str(exc)) from exc
    except store.QuotaError as exc:
        shutil.rmtree(directory, ignore_errors=True)
        raise HTTPException(409, str(exc)) from exc
    except Exception:
        shutil.rmtree(directory, ignore_errors=True)
        log.exception('Saved mission generation failed')
        raise HTTPException(503, 'The mission could not be saved. Try again, or turn off saving to download without an archive.')


@router.get('/api/account/missions/{mid}/download')
def download(mid: str, format: Literal['miz', 'kit'] = 'miz', user=Depends(require_user)):
    data = store.mission_file(user['id'], mid, format)
    if data is None:
        raise HTTPException(404, 'Mission not found.')
    filename = 'mission.miz' if format == 'miz' else 'mission_kit.zip'
    return Response(data, media_type='application/zip', headers={'Content-Disposition': f'attachment; filename="{filename}"'})


@router.patch('/api/account/missions/{mid}')
def rename(mid: str, req: NameRequest, user=Depends(require_user)):
    if not store.rename_mission(user['id'], mid, req.name):
        raise HTTPException(404, 'Mission not found.')
    return {'ok': True}


@router.delete('/api/account/missions/{mid}')
def delete(mid: str, user=Depends(require_user)):
    if not store.delete_mission(user['id'], mid):
        raise HTTPException(404, 'Mission not found.')
    return {'ok': True}


def install(app):
    @app.middleware('http')
    async def private_account_requests(request, call_next):
        path = request.url.path
        private = path.startswith('/api/account') or path.startswith('/auth/discord')
        if private:
            owner = os.environ.get('ACCOUNTS_OWNER_MACHINE')
            current = os.environ.get('FLY_MACHINE_ID')
            if owner and current and owner != current:
                return Response(headers={**NO_STORE, 'fly-replay': 'instance=' + owner})
            # Bound authenticated recipe requests and return-to queries before
            # the framework reads/parses their bodies. No mission uploads here.
            if len(request.scope.get('query_string', b'')) > 100000:
                return JSONResponse({'detail': 'Request is too large.'}, status_code=413, headers=NO_STORE)
            if request.method in ('POST', 'PATCH', 'DELETE'):
                data = bytearray()
                async for chunk in request.stream():
                    data.extend(chunk)
                    if len(data) > 100000:
                        return JSONResponse({'detail': 'Request is too large.'}, status_code=413, headers=NO_STORE)
                request._body = bytes(data)
            try:
                response = await call_next(request)
            except (OSError, sqlite3.Error):
                log.exception('Account storage unavailable')
                response = JSONResponse({'detail': 'Account storage is unavailable. Please try again shortly.'}, status_code=503)
            response.headers.update(NO_STORE)
            return response
        # Keep login cookies and the canonical callback on one hostname.
        if path == '/' and base_url() and request.url.hostname in ('sortiestarter.com', 'www.sortiestarter.com') and request.url.hostname != urlsplit(base_url()).hostname:
            return RedirectResponse(base_url() + ('?' + request.url.query if request.url.query else ''), status_code=308)
        return await call_next(request)
