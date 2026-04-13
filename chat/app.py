from __future__ import annotations

import json
import os
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Any

from flask import Flask, abort, g, jsonify, redirect, render_template, request, session

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / 'data'
DB_PATH = DATA_DIR / 'chat.db'
INVITE_TOKEN = os.environ.get('CHAT_INVITE_TOKEN', '')
ADMIN_TOKEN = os.environ.get('CHAT_ADMIN_TOKEN', '')
SECRET_KEY = os.environ.get('CHAT_SECRET_KEY', secrets.token_hex(32))
RATE_LIMIT_SECONDS = 8
MAX_MESSAGE_LENGTH = 400

ANIMALS = ['Fox', 'Otter', 'Moth', 'Panda', 'Corgi', 'Cat', 'Wolf', 'Lynx', 'Seal', 'Raven']
COLORS = ['Amber', 'Mint', 'Indigo', 'Coral', 'Sky', 'Lemon', 'Rose', 'Pearl', 'Moss', 'Lilac']

app = Flask(__name__)
app.secret_key = SECRET_KEY


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
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nickname TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            deleted INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS rate_limits (
            session_id TEXT PRIMARY KEY,
            last_post_at INTEGER NOT NULL
        );
        '''
    )
    db.commit()


def ensure_nickname() -> str:
    if 'nickname' not in session:
        session['nickname'] = f"{secrets.choice(COLORS)} {secrets.choice(ANIMALS)}"
    return session['nickname']


def ensure_session_id() -> str:
    if 'chat_session_id' not in session:
        session['chat_session_id'] = secrets.token_hex(16)
    return session['chat_session_id']


def require_access() -> None:
    if not INVITE_TOKEN:
        abort(500, 'CHAT_INVITE_TOKEN not configured')
    if session.get('chat_authorized'):
        return
    abort(403)


@app.route('/')
def index() -> Any:
    if session.get('chat_authorized'):
        ensure_nickname()
        return render_template('index.html', nickname=session['nickname'])
    return redirect('/enter')


@app.route('/enter', methods=['GET', 'POST'])
def enter() -> Any:
    error = None
    if request.method == 'POST':
        token = (request.form.get('token') or '').strip()
        if token and token == INVITE_TOKEN:
            session['chat_authorized'] = True
            ensure_nickname()
            ensure_session_id()
            return redirect('/')
        error = '入口碼不正確。'
    return render_template('enter.html', error=error)


@app.route('/api/me')
def me() -> Any:
    require_access()
    return jsonify({'nickname': ensure_nickname()})


@app.route('/api/messages')
def list_messages() -> Any:
    require_access()
    db = get_db()
    rows = db.execute(
        'SELECT id, nickname, body, created_at FROM messages WHERE deleted = 0 ORDER BY id DESC LIMIT 80'
    ).fetchall()
    items = [dict(row) for row in reversed(rows)]
    return jsonify({'items': items})


@app.route('/api/messages', methods=['POST'])
def create_message() -> Any:
    require_access()
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
        return jsonify({'error': '發言太快了，請稍等一下。'}), 429

    nickname = ensure_nickname()
    db.execute('INSERT INTO messages (nickname, body, created_at) VALUES (?, ?, ?)', (nickname, body, now))
    db.execute(
        'INSERT INTO rate_limits (session_id, last_post_at) VALUES (?, ?) ON CONFLICT(session_id) DO UPDATE SET last_post_at=excluded.last_post_at',
        (session_id, now),
    )
    db.commit()
    return jsonify({'ok': True})


@app.route('/api/messages/<int:message_id>', methods=['DELETE'])
def delete_message(message_id: int) -> Any:
    token = request.headers.get('X-Admin-Token', '')
    if not ADMIN_TOKEN or token != ADMIN_TOKEN:
        return jsonify({'error': 'unauthorized'}), 401
    db = get_db()
    db.execute('UPDATE messages SET deleted = 1 WHERE id = ?', (message_id,))
    db.commit()
    return jsonify({'ok': True})


@app.route('/healthz')
def healthz() -> Any:
    return jsonify({'ok': True})


with app.app_context():
    init_db()


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8787, debug=False)
