"""Personal mission shelf and read-only, unlisted shared views."""
import html
from pathlib import Path
import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

from missiongen import __version__
from . import mission_sharing as sharing
from .account_routes import require_user, enabled
from .site_routes import FRONTEND

router = APIRouter()
PAGE = Path(__file__).parent.parent / 'frontend' / 'my-missions.html'
TOKEN = re.compile(r'^[A-Za-z0-9_-]{32}$')


def shared_data(token, page=False):
    if not enabled():
        raise HTTPException(503, 'Mission sharing is temporarily unavailable. Please try again later.')
    if not TOKEN.fullmatch(token):
        raise HTTPException(404, 'This shared link is unavailable or has been stopped.')
    data = sharing.public_page(token) if page else sharing.public_item(token)
    if not data:
        raise HTTPException(404, 'This shared link is unavailable or has been stopped.')
    return data


def render_page(title='My missions', status=200):
    source = FRONTEND.read_text()
    tokens = source.split('/* FLIGHTLINE:TOKENS:BEGIN', 1)[1].split('/* FLIGHTLINE:TOKENS:END */', 1)[0]
    tokens = tokens.split('*/', 1)[1]
    text = PAGE.read_text().replace('{{FLIGHTLINE_TOKENS}}', tokens).replace('{{APP_VERSION}}', __version__).replace('{{PAGE_TITLE}}', html.escape(title, quote=True))
    return HTMLResponse(text, status_code=status)


@router.get('/my-missions')
def my_missions():
    return render_page()


@router.get('/pilots/{token}')
def pilot_page(token: str):
    try:
        data = shared_data(token, page=True)
    except HTTPException as exc:
        return render_page('Shared page unavailable', exc.status_code)
    return render_page(data['name'] + '’s missions')


@router.get('/shared/{token}')
def shared_mission(token: str):
    try:
        data = shared_data(token)
    except HTTPException as exc:
        return render_page('Shared mission unavailable', exc.status_code)
    return render_page(data['items'][0]['title'])


@router.get('/api/account/library')
def library(user=Depends(require_user)):
    return {'items': sharing.private_library(user['id']), 'page_path': sharing.page_link(user['id'])}


class ShareRequest(BaseModel):
    model_config = {'extra': 'forbid'}
    kind: Literal['mission', 'selection']
    id: str = Field(min_length=1, max_length=80)


@router.post('/api/account/shares')
def create_share(req: ShareRequest, user=Depends(require_user)):
    token = sharing.share(user['id'], req.kind, req.id)
    if not token:
        raise HTTPException(404, 'Mission not found in your profile.')
    return {'path': '/shared/' + token}


@router.delete('/api/account/shares/{kind}/{item_id}')
def stop_share(kind: Literal['mission', 'selection'], item_id: str, user=Depends(require_user)):
    if not sharing.unshare(user['id'], kind, item_id):
        raise HTTPException(404, 'Shared mission not found in your profile.')
    return {'ok': True}


@router.post('/api/account/shared-page')
def create_page(user=Depends(require_user)):
    return {'path': sharing.page_link(user['id'], enable=True)}


@router.delete('/api/account/shared-page')
def stop_page(user=Depends(require_user)):
    sharing.stop_all(user['id'])
    return {'ok': True}


@router.get('/api/pilots/{token}')
def read_page(token: str):
    return shared_data(token, page=True)


@router.get('/api/shared/{token}')
def read_shared(token: str):
    return shared_data(token)


@router.get('/api/shared/{token}/download')
def download_shared(token: str, format: Literal['miz', 'kit'] = 'miz'):
    shared_data(token)
    data = sharing.public_file(token, format)
    if data is None:
        raise HTTPException(404, 'This shared mission has no archived file. Open its saved setup or published download instead.')
    filename = 'mission.miz' if format == 'miz' else 'mission_kit.zip'
    return Response(data, media_type='application/zip', headers={'Content-Disposition': f'attachment; filename="{filename}"'})
