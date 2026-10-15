"""Private accounts, opaque sessions and original mission archives on one volume.

The identity UUID is independent of Discord and can be migrated to a family
identity service later. This module does not implement cross-application SSO.
SQLite transactions make archive/quota checks and deletion atomic. Fly requests
must reach ACCOUNTS_OWNER_MACHINE; replica disks are never writable fallbacks.
"""
from contextlib import contextmanager, closing
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import sqlite3
import time
import uuid

SESSION_TTL = 30 * 86400
STATE_TTL = 600
MAX_MISSIONS = 100
MAX_USER_BYTES = 100 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024
MAX_KIT_BYTES = 24 * 1024 * 1024
MIN_FREE_BYTES = 256 * 1024 * 1024


class QuotaError(ValueError):
    pass


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


@contextmanager
def database():
    directory = Path(os.environ.get('ACCOUNTS_DATA_DIR', 'instance/accounts'))
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    with closing(sqlite3.connect(directory / 'accounts.sqlite3', timeout=10)) as db, db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA secure_delete=ON')
        db.execute('PRAGMA foreign_keys=ON')
        db.executescript('''
          CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY, discord_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL, created_at INTEGER NOT NULL);
          CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            csrf TEXT NOT NULL, expires INTEGER NOT NULL);
          CREATE TABLE IF NOT EXISTS oauth_states (
            token_hash TEXT PRIMARY KEY, return_to TEXT NOT NULL, expires INTEGER NOT NULL);
          CREATE TABLE IF NOT EXISTS missions (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title TEXT NOT NULL, created_at INTEGER NOT NULL, version TEXT NOT NULL,
            recipe TEXT NOT NULL, manifest TEXT NOT NULL, sha256 TEXT NOT NULL,
            miz BLOB NOT NULL, kit BLOB NOT NULL, bytes INTEGER NOT NULL,
            UNIQUE(user_id, sha256, version));
          CREATE INDEX IF NOT EXISTS mission_user ON missions(user_id, created_at);
        ''')
        now = int(time.time())
        db.execute('DELETE FROM sessions WHERE expires <= ?', (now,))
        db.execute('DELETE FROM oauth_states WHERE expires <= ?', (now,))
        db.commit()
        yield db


def start_login(return_to):
    token = secrets.token_urlsafe(32)
    with database() as db:
        # Bound anonymous login-state storage, including expired-state cleanup.
        if db.execute('SELECT COUNT(*) FROM oauth_states').fetchone()[0] >= 10000:
            raise QuotaError('Sign-in is busy. Please try again shortly.')
        db.execute('INSERT INTO oauth_states VALUES (?, ?, ?)',
                   (digest(token), return_to, int(time.time()) + STATE_TTL))
    return token


def consume_login(token):
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT return_to FROM oauth_states WHERE token_hash=?', (digest(token),)).fetchone()
        db.execute('DELETE FROM oauth_states WHERE token_hash=?', (digest(token),))
    return row['return_to'] if row else None


def sign_in(discord_id, name):
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    with database() as db:
        db.execute('INSERT INTO users VALUES (?, ?, ?, ?) ON CONFLICT(discord_id) DO NOTHING',
                   (str(uuid.uuid4()), discord_id, name, int(time.time())))
        user = dict(db.execute('SELECT * FROM users WHERE discord_id=?', (discord_id,)).fetchone())
        # Bound active sessions per account; preserve the newest 19 plus this one.
        db.execute('DELETE FROM sessions WHERE user_id=? AND token_hash NOT IN '
                   '(SELECT token_hash FROM sessions WHERE user_id=? ORDER BY expires DESC LIMIT 19)',
                   (user['id'], user['id']))
        db.execute('INSERT INTO sessions VALUES (?, ?, ?, ?)',
                   (digest(token), user['id'], csrf, int(time.time()) + SESSION_TTL))
    return token


def session(token):
    if not token or len(token) > 128:
        return None
    with database() as db:
        row = db.execute('SELECT users.*, sessions.csrf FROM sessions JOIN users '
                         'ON users.id=sessions.user_id WHERE token_hash=?', (digest(token),)).fetchone()
    return dict(row) if row else None


def sign_out(token):
    with database() as db:
        db.execute('DELETE FROM sessions WHERE token_hash=?', (digest(token),))


def public_mission(row):
    item = dict(row)
    item['recipe'] = json.loads(item['recipe'])
    item['manifest'] = json.loads(item['manifest'])
    return item


MISSION_COLUMNS = 'id, title, created_at, version, recipe, manifest, sha256, bytes'


def list_missions(user_id):
    with database() as db:
        return [public_mission(row) for row in db.execute(
            f'SELECT {MISSION_COLUMNS} FROM missions WHERE user_id=? ORDER BY created_at DESC, id', (user_id,))]


def save_mission(user_id, title, result):
    manifest = result['manifest']
    miz, kit = result['miz'].read_bytes(), result['bundle'].read_bytes()
    size = len(miz) + len(kit)
    if size > MAX_KIT_BYTES:
        raise QuotaError('This Mission Kit is too large to save. Generate without saving to download it.')
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        existing = db.execute(f'SELECT {MISSION_COLUMNS} FROM missions WHERE user_id=? AND sha256=? AND version=?',
                              (user_id, manifest['mission']['sha256'], manifest['app_version'])).fetchone()
        if existing:
            return public_mission(existing)
        count, used = db.execute('SELECT COUNT(*), COALESCE(SUM(bytes), 0) FROM missions WHERE user_id=?',
                                 (user_id,)).fetchone()
        if count >= MAX_MISSIONS or used + size > MAX_USER_BYTES:
            raise QuotaError('Your saved-mission space is full (100 missions or 100 MB). Delete a mission or generate without saving.')
        total = db.execute('SELECT COALESCE(SUM(bytes), 0) FROM missions').fetchone()[0]
        directory = Path(os.environ.get('ACCOUNTS_DATA_DIR', 'instance/accounts'))
        if total + size > MAX_TOTAL_BYTES or shutil.disk_usage(directory).free < MIN_FREE_BYTES + size:
            raise QuotaError('Saved-mission storage is full. Generate without saving and keep your download; please contact the operator.')
        mid = str(uuid.uuid4())
        db.execute('INSERT INTO missions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                   (mid, user_id, title, int(time.time()), manifest['app_version'],
                    json.dumps(manifest['recipe']), json.dumps(manifest), manifest['mission']['sha256'], miz, kit, size))
        return public_mission(db.execute(f'SELECT {MISSION_COLUMNS} FROM missions WHERE id=?', (mid,)).fetchone())


def mission_file(user_id, mid, kind):
    column = {'miz': 'miz', 'kit': 'kit'}[kind]
    with database() as db:
        row = db.execute(f'SELECT {column} FROM missions WHERE id=? AND user_id=?', (mid, user_id)).fetchone()
    return row[0] if row else None


def rename_mission(user_id, mid, title):
    with database() as db:
        return db.execute('UPDATE missions SET title=? WHERE id=? AND user_id=?', (title, mid, user_id)).rowcount > 0


def delete_mission(user_id, mid):
    with database() as db:
        return db.execute('DELETE FROM missions WHERE id=? AND user_id=?', (mid, user_id)).rowcount > 0


def rename_user(user_id, name):
    with database() as db:
        db.execute('UPDATE users SET name=? WHERE id=?', (name, user_id))


def delete_user(user_id):
    with database() as db:
        db.execute('DELETE FROM users WHERE id=?', (user_id,))
