from __future__ import annotations

import os
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Any

from flask import Flask, abort, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / 'data'
DB_PATH = DATA_DIR / 'chat.db'
ADMIN_TOKEN = os.environ.get('CHAT_ADMIN_TOKEN', '')
SECRET_KEY = os.environ.get('CHAT_SECRET_KEY', '')
DEFAULT_ROOM_SLUG = os.environ.get('CHAT_DEFAULT_ROOM', 'lobby')
RATE_LIMIT_SECONDS = int(os.environ.get('CHAT_RATE_LIMIT_SECONDS', '8'))
MAX_MESSAGE_LENGTH = int(os.environ.get('CHAT_MAX_MESSAGE_LENGTH', '400'))
MAX_MESSAGES = int(os.environ.get('CHAT_MAX_MESSAGES', '120'))
SESSION_COOKIE_NAME = os.environ.get('CHAT_SESSION_COOKIE_NAME', 'koxuan_chat_session')
SESSION_COOKIE_SECURE = os.environ.get('CHAT_SESSION_COOKIE_SECURE', 'true').lower() in {'1', 'true', 'yes', 'on'}
SESSION_COOKIE_SAMESITE = os.environ.get('CHAT_SESSION_COOKIE_SAMESITE', 'Lax')
PERMANENT_SESSION_LIFETIME_SECONDS = int(os.environ.get('CHAT_SESSION_TTL_SECONDS', str(60 * 60 * 24 * 7)))

ANIMALS = ['Fox', 'Otter', 'Moth', 'Panda', 'Corgi', 'Cat', 'Wolf', 'Lynx', 'Seal', 'Raven']
COLORS = ['Amber', 'Mint', 'Indigo', 'Coral', 'Sky', 'Lemon', 'Rose', 'Pearl', 'Moss', 'Lilac']

app = Flask(__name__)
app.config.update(
    SECRET_KEY=SECRET_KEY,
    SESSION_COOKIE_NAME=SESSION_COOKIE_NAME,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=SESSION_COOKIE_SECURE,
    SESSION_COOKIE_SAMESITE=SESSION_COOKIE_SAMESITE,
    PERMANENT_SESSION_LIFETIME=PERMANENT_SESSION_LIFETIME_SECONDS,
)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)


if not SECRET_KEY:
    raise RuntimeError('CHAT_SECRET_KEY is required in production.')

if not ADMIN_TOKEN:
    raise RuntimeError('CHAT_ADMIN_TOKEN is required in production.')


def get_db() -> sqlite3.Connection:
    if 'db' not in g:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db


@app.teardown_appcontext
def close_db(_: Any) -> None:
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = get_db()
    db.executescript(
        '''
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS invites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT NOT NULL UNIQUE,
            room_id INTEGER NOT NULL,
            label TEXT,
            max_uses INTEGER,
            use_count INTEGER NOT NULL DEFAULT 0,
            expires_at INTEGER,
            revoked INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL,
            FOREIGN KEY(room_id) REFERENCES rooms(id)
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER NOT NULL,
            nickname TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            deleted INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(room_id) REFERENCES rooms(id)
        );
        CREATE TABLE IF NOT EXISTS rate_limits (
            session_id TEXT PRIMARY KEY,
            last_post_at INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_messages_room_created_at ON messages(room_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_invites_room_id ON invites(room_id);
        '''
    )
    db.commit()
    ensure_default_room(db)
    db.commit()


def ensure_default_room(db: sqlite3.Connection) -> sqlite3.Row:
    row = db.execute('SELECT * FROM rooms WHERE slug = ?', (DEFAULT_ROOM_SLUG,)).fetchone()
    if row:
        return row
    now = int(time.time())
    db.execute(
        'INSERT INTO rooms (slug, title, description, created_at) VALUES (?, ?, ?, ?)',
        (DEFAULT_ROOM_SLUG, '匿名小圈圈聊天室', '用邀請連結進入，匿名但不裸奔。', now),
    )
    return db.execute('SELECT * FROM rooms WHERE slug = ?', (DEFAULT_ROOM_SLUG,)).fetchone()


def ensure_nickname() -> str:
    if 'nickname' not in session:
        session['nickname'] = f"{secrets.choice(COLORS)} {secrets.choice(ANIMALS)}"
    return session['nickname']


def ensure_session_id() -> str:
    if 'chat_session_id' not in session:
        session['chat_session_id'] = secrets.token_hex(16)
    session.permanent = True
    return session['chat_session_id']


def current_room() -> sqlite3.Row | None:
    room_id = session.get('chat_room_id')
    if not room_id:
        return None
    return get_db().execute('SELECT * FROM rooms WHERE id = ?', (room_id,)).fetchone()


def require_access() -> sqlite3.Row:
    room = current_room()
    if room is None:
        abort(403)
    return room


def invite_status(invite: sqlite3.Row) -> str | None:
    now = int(time.time())
    if int(invite['revoked'] or 0):
        return '這個邀請連結已停用。'
    expires_at = invite['expires_at']
    if expires_at and now > int(expires_at):
        return '這個邀請連結已過期。'
    max_uses = invite['max_uses']
    if max_uses is not None and int(invite['use_count']) >= int(max_uses):
        return '這個邀請連結已達使用上限。'
    return None


def create_invite(room_id: int, label: str = 'default', max_uses: int | None = None, expires_at: int | None = None) -> str:
    db = get_db()
    token = secrets.token_urlsafe(24)
    now = int(time.time())
    db.execute(
        'INSERT INTO invites (token, room_id, label, max_uses, expires_at, created_at) VALUES (?, ?, ?, ?, ?, ?)',
        (token, room_id, label, max_uses, expires_at, now),
    )
    db.commit()
    return token


def ensure_bootstrap_invite() -> None:
    db = get_db()
    room = ensure_default_room(db)
    existing = db.execute('SELECT COUNT(*) AS count FROM invites WHERE room_id = ?', (room['id'],)).fetchone()
    if int(existing['count']) == 0:
        create_invite(room['id'], label='bootstrap', max_uses=None, expires_at=None)


def require_admin_token() -> None:
    token = request.headers.get('X-Admin-Token', '') or request.args.get('token', '')
    if token != ADMIN_TOKEN:
        abort(401)


@app.after_request
def apply_security_headers(response: Any) -> Any:
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['Cache-Control'] = 'no-store'
    return response


@app.route('/')
def index() -> Any:
    room = current_room()
    if room:
        ensure_nickname()
        ensure_session_id()
        return render_template('index.html', nickname=session['nickname'], room=room, max_message_length=MAX_MESSAGE_LENGTH)
    return redirect('/enter')


@app.route('/enter', methods=['GET', 'POST'])
def enter() -> Any:
    error = None
    invite_token = (request.args.get('invite') or '').strip()
    if request.method == 'POST':
        invite_token = (request.form.get('token') or '').strip()

    if invite_token:
        db = get_db()
        invite = db.execute(
            'SELECT invites.*, rooms.slug, rooms.title, rooms.description FROM invites JOIN rooms ON rooms.id = invites.room_id WHERE token = ?',
            (invite_token,),
        ).fetchone()
        if invite is None:
            error = '找不到這個邀請連結。'
        else:
            blocked_reason = invite_status(invite)
            if blocked_reason:
                error = blocked_reason
            else:
                db.execute('UPDATE invites SET use_count = use_count + 1 WHERE id = ?', (invite['id'],))
                db.commit()
                session.clear()
                session['chat_authorized'] = True
                session['chat_room_id'] = int(invite['room_id'])
                session['chat_invite_token'] = invite_token
                ensure_nickname()
                ensure_session_id()
                return redirect('/')

    return render_template('enter.html', error=error, invite_token=invite_token)


@app.route('/logout', methods=['POST'])
def logout() -> Any:
    session.clear()
    return redirect('/enter')


@app.route('/api/me')
def me() -> Any:
    room = require_access()
    return jsonify({'nickname': ensure_nickname(), 'room': {'slug': room['slug'], 'title': room['title']}})


@app.route('/api/messages')
def list_messages() -> Any:
    room = require_access()
    db = get_db()
    rows = db.execute(
        'SELECT id, nickname, body, created_at FROM messages WHERE room_id = ? AND deleted = 0 ORDER BY id DESC LIMIT ?',
        (room['id'], MAX_MESSAGES),
    ).fetchall()
    items = [dict(row) for row in reversed(rows)]
    return jsonify({'items': items, 'rateLimitSeconds': RATE_LIMIT_SECONDS, 'maxMessageLength': MAX_MESSAGE_LENGTH})


@app.route('/api/messages', methods=['POST'])
def create_message() -> Any:
    room = require_access()
    db = get_db()
    payload = request.get_json(silent=True) or {}
    body = (payload.get('body') or '').strip()
    if not body:
        return jsonify({'error': '訊息不能是空的。'}), 400
    if len(body) > MAX_MESSAGE_LENGTH:
        return jsonify({'error': f'訊息不能超過 {MAX_MESSAGE_LENGTH} 字。'}), 400

    session_id = ensure_session_id()
    now = int(time.time())
    row = db.execute('SELECT last_post_at FROM rate_limits WHERE session_id = ?', (session_id,)).fetchone()
    if row and now - int(row['last_post_at']) < RATE_LIMIT_SECONDS:
        return jsonify({'error': f'發言太快了，請 {RATE_LIMIT_SECONDS} 秒後再試。'}), 429

    nickname = ensure_nickname()
    db.execute(
        'INSERT INTO messages (room_id, nickname, body, created_at) VALUES (?, ?, ?, ?)',
        (room['id'], nickname, body, now),
    )
    db.execute(
        'INSERT INTO rate_limits (session_id, last_post_at) VALUES (?, ?) ON CONFLICT(session_id) DO UPDATE SET last_post_at=excluded.last_post_at',
        (session_id, now),
    )
    db.commit()
    return jsonify({'ok': True})


@app.route('/api/messages/<int:message_id>', methods=['DELETE'])
def delete_message(message_id: int) -> Any:
    require_admin_token()
    db = get_db()
    db.execute('UPDATE messages SET deleted = 1 WHERE id = ?', (message_id,))
    db.commit()
    return jsonify({'ok': True})


@app.route('/admin')
def admin() -> Any:
    require_admin_token()
    db = get_db()
    room = ensure_default_room(db)
    invites = db.execute(
        'SELECT token, label, max_uses, use_count, expires_at, revoked, created_at FROM invites WHERE room_id = ? ORDER BY id DESC',
        (room['id'],),
    ).fetchall()
    base = request.host_url.rstrip('/')
    invite_items = []
    for invite in invites:
        item = dict(invite)
        item['url'] = f"{base}{url_for('enter')}?invite={invite['token']}"
        invite_items.append(item)
    return render_template('admin.html', room=room, invites=invite_items)


@app.route('/admin/invites', methods=['POST'])
def admin_create_invite() -> Any:
    token = request.headers.get('X-Admin-Token', '') or request.form.get('admin_token', '')
    if token != ADMIN_TOKEN:
        return jsonify({'error': 'unauthorized'}), 401

    payload = request.get_json(silent=True) if request.is_json else None
    label = (payload or {}).get('label') if payload else request.form.get('label')
    label = (label or 'manual').strip()

    max_uses_raw = str((payload or {}).get('max_uses') if payload else (request.form.get('max_uses') or '')).strip()
    max_uses = int(max_uses_raw) if max_uses_raw else None
    if max_uses is not None and max_uses <= 0:
        return jsonify({'error': 'max_uses 必須大於 0'}), 400

    db = get_db()
    room = ensure_default_room(db)
    invite_token = create_invite(room['id'], label=label, max_uses=max_uses)
    base = request.host_url.rstrip('/')
    return jsonify({'ok': True, 'token': invite_token, 'url': f"{base}{url_for('enter')}?invite={invite_token}"})


@app.route('/healthz')
def healthz() -> Any:
    db = get_db()
    db.execute('SELECT 1').fetchone()
    return jsonify({'ok': True, 'room': DEFAULT_ROOM_SLUG})


with app.app_context():
    init_db()
    ensure_bootstrap_invite()


if __name__ == '__main__':
    port = int(os.environ.get('CHAT_PORT', '8787'))
    app.run(host='127.0.0.1', port=port, debug=False)
