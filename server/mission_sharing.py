"""Explicit, revocable links to selected missions; private saves stay private.

All metadata and file reads use the account owner. Public responses project
only shared content and the chosen display name, never identity/session data.
"""
import base64
import json
import secrets
from urllib.parse import quote

from .account_store import database

TABLES = {'mission': ('missions', 'mission_id'), 'selection': ('selections', 'selection_id')}


def share(user_id, kind, item_id):
    table, column = TABLES[kind]
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        if not db.execute(f'SELECT id FROM {table} WHERE id=? AND user_id=?', (item_id, user_id)).fetchone():
            return None
        existing = db.execute(f'SELECT token FROM mission_shares WHERE {column}=? AND user_id=?', (item_id, user_id)).fetchone()
        if existing:
            return existing['token']
        token = secrets.token_urlsafe(24)
        db.execute(f'INSERT INTO mission_shares(token,user_id,{column}) VALUES (?,?,?)', (token, user_id, item_id))
        return token


def unshare(user_id, kind, item_id):
    _, column = TABLES[kind]
    with database() as db:
        return db.execute(f'DELETE FROM mission_shares WHERE user_id=? AND {column}=?', (user_id, item_id)).rowcount > 0


def page_link(user_id, enable=False):
    with database() as db:
        if enable:
            db.execute('INSERT INTO shared_pages VALUES (?,?) ON CONFLICT(user_id) DO NOTHING',
                       (user_id, secrets.token_urlsafe(24)))
        row = db.execute('SELECT token FROM shared_pages WHERE user_id=?', (user_id,)).fetchone()
        return '/pilots/' + row['token'] if row else None


def stop_all(user_id):
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('DELETE FROM shared_pages WHERE user_id=?', (user_id,))
        db.execute('DELETE FROM mission_shares WHERE user_id=?', (user_id,))


def builder_link(recipe):
    encoded = base64.urlsafe_b64encode(json.dumps({'v': 1, 'r': recipe}, separators=(',', ':'), ensure_ascii=False).encode()).decode().rstrip('=')
    return '/?r=' + encoded


def present(row, kind, share_token=None, private=False):
    item = {k: row[k] for k in ('title', 'created_at', 'version')}
    recipe = json.loads(row['recipe']) if kind == 'mission' else None
    payload = json.loads(row['payload']) if kind == 'selection' else None
    if payload and payload['kind'] == 'recipe':
        recipe = payload['recipe']
    item['category'] = 'original' if kind == 'mission' else 'setup' if recipe else 'library'
    item['details'] = {k: recipe.get(k) for k in ('map', 'era', 'aircraft', 'slots', 'veteran_wingmen')} if recipe else {}
    if recipe:
        item['open_path'] = builder_link(recipe)
    if kind == 'mission':
        prefix = '/api/account/missions/' + row['id'] if private else '/api/shared/' + share_token
        item.update(bytes=row['bytes'], miz_path=prefix + '/download?format=miz', kit_path=prefix + '/download?format=kit')
    elif payload['kind'] == 'pack':
        item['collection'] = not bool(payload.get('path'))
        item['pack_version'] = payload.get('pack_version')
        item['open_path'] = '/?v=library&pack=' + quote(payload['pack_id'], safe='')
        item['download_path'] = '/api/pack/' + quote(payload['pack_id'], safe='') + '/' + (
            quote(payload['path'], safe='/') if payload.get('path') else 'all.zip')
    if private:
        item.update(id=row['id'], kind=kind, share_path='/shared/' + share_token if share_token else None)
    return item


def private_library(user_id):
    items = []
    with database() as db:
        for kind, (table, column) in TABLES.items():
            columns = 'm.id,m.title,m.created_at,m.version,' + ('m.recipe,m.bytes' if kind == 'mission' else 'm.payload')
            rows = db.execute(f'SELECT {columns},s.token FROM {table} m LEFT JOIN mission_shares s ON s.{column}=m.id '
                              'WHERE m.user_id=?', (user_id,)).fetchall()
            items.extend(present(row, kind, row['token'], private=True) for row in rows)
    return sorted(items, key=lambda i: (i['created_at'], i['id']), reverse=True)


def public_item(token):
    with database() as db:
        share_row = db.execute('SELECT s.*,u.name FROM mission_shares s JOIN users u ON u.id=s.user_id WHERE token=?', (token,)).fetchone()
        if not share_row:
            return None
        kind = 'mission' if share_row['mission_id'] else 'selection'
        table, column = TABLES[kind]
        columns = 'id,title,created_at,version,' + ('recipe,bytes' if kind == 'mission' else 'payload')
        row = db.execute(f'SELECT {columns} FROM {table} WHERE id=? AND user_id=?',
                         (share_row[column], share_row['user_id'])).fetchone()
        if not row:
            return None
        return {'name': share_row['name'], 'items': [present(row, kind, token)]}


def public_page(token):
    with database() as db:
        user = db.execute('SELECT p.user_id,u.name FROM shared_pages p JOIN users u ON u.id=p.user_id WHERE p.token=?', (token,)).fetchone()
        if not user:
            return None
        items = []
        for kind, (table, column) in TABLES.items():
            columns = 'm.id,m.title,m.created_at,m.version,' + ('m.recipe,m.bytes' if kind == 'mission' else 'm.payload')
            rows = db.execute(f'SELECT {columns},s.token FROM {table} m JOIN mission_shares s ON s.{column}=m.id '
                              'AND s.user_id=m.user_id JOIN shared_pages p ON p.user_id=s.user_id '
                              'WHERE p.token=?', (token,)).fetchall()
            for row in rows:
                item = present(row, kind, row['token'])
                item['share_path'] = '/shared/' + row['token']
                items.append(item)
    return {'name': user['name'], 'items': sorted(items, key=lambda i: i['created_at'], reverse=True)}



def public_file(token, format):
    column = {'miz': 'miz', 'kit': 'kit'}[format]
    with database() as db:
        row = db.execute(f'SELECT m.{column} FROM missions m JOIN mission_shares s ON s.mission_id=m.id '
                         'AND s.user_id=m.user_id WHERE s.token=?', (token,)).fetchone()
        return row[0] if row else None
