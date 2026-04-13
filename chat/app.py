from __future__ import annotations

import json
import mimetypes
import os
import secrets
import time
from datetime import datetime, timezone
from typing import Any
from urllib import error, parse, request as urllib_request

from flask import Flask, abort, jsonify, redirect, render_template, request, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

ADMIN_TOKEN = os.environ.get('CHAT_ADMIN_TOKEN', '')
SECRET_KEY = os.environ.get('CHAT_SECRET_KEY', '')
DEFAULT_ROOM_SLUG = os.environ.get('CHAT_DEFAULT_ROOM', 'lobby')
RATE_LIMIT_SECONDS = int(os.environ.get('CHAT_RATE_LIMIT_SECONDS', '8'))
MAX_MESSAGE_LENGTH = int(os.environ.get('CHAT_MAX_MESSAGE_LENGTH', '400'))
MAX_MESSAGES = int(os.environ.get('CHAT_MAX_MESSAGES', '120'))
SESSION_COOKIE_NAME = os.environ.get('CHAT_SESSION_COOKIE_NAME', 'koxuan_chat_session')
SESSION_COOKIE_SECURE = os.environ.get('CHAT_SESSION_COOKIE_SECURE', 'false').lower() in {'1', 'true', 'yes', 'on'}
SESSION_COOKIE_SAMESITE = os.environ.get('CHAT_SESSION_COOKIE_SAMESITE', 'Lax')
PERMANENT_SESSION_LIFETIME_SECONDS = int(os.environ.get('CHAT_SESSION_TTL_SECONDS', str(60 * 60 * 24 * 7)))
SUPABASE_URL = os.environ.get('CHAT_SUPABASE_URL', '').rstrip('/')
SUPABASE_SERVICE_ROLE_KEY = os.environ.get('CHAT_SUPABASE_SERVICE_ROLE_KEY', '')
SUPABASE_SCHEMA = os.environ.get('CHAT_SUPABASE_SCHEMA', 'public')
SUPABASE_STORAGE_BUCKET = os.environ.get('CHAT_SUPABASE_STORAGE_BUCKET', 'chat-uploads')
MAX_UPLOAD_BYTES = int(os.environ.get('CHAT_MAX_UPLOAD_BYTES', str(20 * 1024 * 1024)))

ANIMALS = ['🦊', '🦦', '🦋', '🐼', '🐶', '🐱', '🐺', '🐈', '🦭', '🐦', '🐰', '🦝', '🦔', '🐸']

app = Flask(__name__)
app.config.update(
    SECRET_KEY=SECRET_KEY,
    SESSION_COOKIE_NAME=SESSION_COOKIE_NAME,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=SESSION_COOKIE_SECURE,
    SESSION_COOKIE_SAMESITE=SESSION_COOKIE_SAMESITE,
    PERMANENT_SESSION_LIFETIME=PERMANENT_SESSION_LIFETIME_SECONDS,
    MAX_CONTENT_LENGTH=MAX_UPLOAD_BYTES,
)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

if not SECRET_KEY:
    raise RuntimeError('CHAT_SECRET_KEY is required in production.')
if not ADMIN_TOKEN:
    raise RuntimeError('CHAT_ADMIN_TOKEN is required in production.')
if not SUPABASE_URL:
    raise RuntimeError('CHAT_SUPABASE_URL is required for Supabase-backed chat.')
if not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError('CHAT_SUPABASE_SERVICE_ROLE_KEY is required for Supabase-backed chat.')


class SupabaseError(RuntimeError):
    pass


def supabase_request(method: str, path: str, *, query: dict[str, Any] | None = None, json_body: dict[str, Any] | list[dict[str, Any]] | None = None, data: bytes | None = None, extra_headers: dict[str, str] | None = None, prefer: str | None = None) -> Any:
    url = f"{SUPABASE_URL}/rest/v1/{path.lstrip('/')}"
    if query:
        url = f"{url}?{parse.urlencode(query, doseq=True)}"

    headers = {
        'apikey': SUPABASE_SERVICE_ROLE_KEY,
        'Authorization': f'Bearer {SUPABASE_SERVICE_ROLE_KEY}',
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Accept-Profile': SUPABASE_SCHEMA,
        'Content-Profile': SUPABASE_SCHEMA,
    }
    if prefer:
        headers['Prefer'] = prefer
    if extra_headers:
        headers.update(extra_headers)

    body = data
    if json_body is not None:
        body = json.dumps(json_body).encode('utf-8')

    req = urllib_request.Request(url, method=method.upper(), headers=headers, data=body)
    try:
        with urllib_request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode('utf-8') if resp.headers.get('Content-Type', '').startswith('application/json') else resp.read()
            if raw in (b'', ''):
                return None
            if isinstance(raw, bytes):
                return raw
            return json.loads(raw)
    except error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='ignore')
        raise SupabaseError(f'Supabase HTTP {exc.code}: {detail}') from exc
    except error.URLError as exc:
        raise SupabaseError(f'Supabase connection failed: {exc}') from exc


def fetch_one(path: str, query: dict[str, Any]) -> dict[str, Any] | None:
    rows = supabase_request('GET', path, query={**query, 'limit': 1}) or []
    return rows[0] if rows else None


def ensure_nickname() -> str:
    if 'nickname' not in session:
        session['nickname'] = secrets.choice(ANIMALS)
    return session['nickname']


def ensure_session_id() -> str:
    if 'chat_session_id' not in session:
        session['chat_session_id'] = secrets.token_hex(16)
    session.permanent = True
    return session['chat_session_id']


def current_room() -> dict[str, Any] | None:
    room_id = session.get('chat_room_id')
    if not room_id:
        return None
    return fetch_one('chat_rooms', {'id': f'eq.{room_id}'})


def require_access() -> dict[str, Any]:
    room = current_room()
    if room is None:
        abort(403)
    return room


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def invite_status(invite: dict[str, Any]) -> str | None:
    now = datetime.now(timezone.utc)
    if invite.get('revoked'):
        return '這個邀請連結已停用。'
    expires_at = parse_timestamp(invite.get('expires_at'))
    if expires_at and now > expires_at:
        return '這個邀請連結已過期。'
    max_uses = invite.get('max_uses')
    use_count = int(invite.get('use_count') or 0)
    if max_uses is not None and use_count >= int(max_uses):
        return '這個邀請連結已達使用上限。'
    return None


def create_invite(room_id: str, label: str = 'default', max_uses: int | None = None) -> str:
    token = secrets.token_urlsafe(24)
    payload = {
        'token': token,
        'room_id': room_id,
        'label': label,
        'max_uses': max_uses,
    }
    supabase_request('POST', 'chat_invites', json_body=payload, prefer='return=minimal')
    return token


def ensure_default_room() -> dict[str, Any]:
    room = fetch_one('chat_rooms', {'slug': f'eq.{DEFAULT_ROOM_SLUG}'})
    if room:
        return room
    payload = {
        'slug': DEFAULT_ROOM_SLUG,
        'title': '匿名小圈圈聊天室',
        'description': '用邀請連結進入，匿名但不裸奔。',
    }
    supabase_request('POST', 'chat_rooms', json_body=payload, prefer='return=representation')
    room = fetch_one('chat_rooms', {'slug': f'eq.{DEFAULT_ROOM_SLUG}'})
    if room is None:
        raise SupabaseError('Failed to create default room.')
    return room


def ensure_bootstrap_invite() -> None:
    room = ensure_default_room()
    existing = supabase_request('GET', 'chat_invites', query={'room_id': f"eq.{room['id']}", 'select': 'id', 'limit': 1}) or []
    if not existing:
        create_invite(room['id'], label='bootstrap')


def require_admin_token() -> None:
    token = request.headers.get('X-Admin-Token', '') or request.args.get('token', '')
    if token != ADMIN_TOKEN:
        abort(401)


def increment_invite_use_count(invite: dict[str, Any]) -> None:
    next_count = int(invite.get('use_count') or 0) + 1
    supabase_request('PATCH', 'chat_invites', query={'id': f"eq.{invite['id']}"}, json_body={'use_count': next_count}, prefer='return=minimal')


def upsert_rate_limit(session_id: str) -> None:
    supabase_request(
        'POST',
        'chat_rate_limits',
        json_body={'session_id': session_id, 'last_post_at': datetime.now(timezone.utc).isoformat()},
        prefer='resolution=merge-duplicates,return=minimal',
    )


def ensure_bucket_public() -> None:
    buckets = supabase_request('GET', 'storage/v1/bucket', extra_headers={'Accept': 'application/json'}) or []
    if any(bucket.get('name') == SUPABASE_STORAGE_BUCKET for bucket in buckets):
        return
    req = urllib_request.Request(
        f'{SUPABASE_URL}/storage/v1/bucket',
        method='POST',
        headers={
            'apikey': SUPABASE_SERVICE_ROLE_KEY,
            'Authorization': f'Bearer {SUPABASE_SERVICE_ROLE_KEY}',
            'Content-Type': 'application/json',
        },
        data=json.dumps({'id': SUPABASE_STORAGE_BUCKET, 'name': SUPABASE_STORAGE_BUCKET, 'public': True}).encode('utf-8'),
    )
    try:
        with urllib_request.urlopen(req, timeout=30):
            return
    except error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='ignore')
        if 'already exists' in detail:
            return
        raise SupabaseError(f'Supabase storage bucket create failed: {detail}') from exc


def upload_image(file_storage: Any, room_id: str) -> tuple[str, str]:
    content = file_storage.read()
    file_storage.stream.seek(0)
    if not content:
        raise ValueError('圖片內容是空的。')
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError(f'圖片不能超過 {MAX_UPLOAD_BYTES // (1024 * 1024)}MB。')

    mime_type = file_storage.mimetype or mimetypes.guess_type(file_storage.filename or '')[0] or 'application/octet-stream'
    ext = mimetypes.guess_extension(mime_type) or '.bin'
    image_path = f'{room_id}/{int(time.time())}-{secrets.token_urlsafe(8)}{ext}'
    req = urllib_request.Request(
        f'{SUPABASE_URL}/storage/v1/object/{SUPABASE_STORAGE_BUCKET}/{image_path}',
        method='POST',
        headers={
            'apikey': SUPABASE_SERVICE_ROLE_KEY,
            'Authorization': f'Bearer {SUPABASE_SERVICE_ROLE_KEY}',
            'Content-Type': mime_type,
            'x-upsert': 'false',
        },
        data=content,
    )
    try:
        with urllib_request.urlopen(req, timeout=60):
            pass
    except error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='ignore')
        raise SupabaseError(f'Supabase storage upload failed: {detail}') from exc

    public_url = f'{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_STORAGE_BUCKET}/{image_path}'
    return public_url, image_path


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
        return render_template(
            'index.html',
            nickname=session['nickname'],
            room=room,
            max_message_length=MAX_MESSAGE_LENGTH,
            max_upload_mb=max(1, MAX_UPLOAD_BYTES // (1024 * 1024)),
        )
    return redirect('/enter')


@app.route('/enter', methods=['GET', 'POST'])
def enter() -> Any:
    error = None
    invite_token = (request.args.get('invite') or '').strip()
    if request.method == 'POST':
        invite_token = (request.form.get('token') or '').strip()

    if invite_token:
        invite = fetch_one('chat_invites', {'token': f'eq.{invite_token}'})
        if invite is None:
            error = '找不到這個邀請連結。'
        else:
            blocked_reason = invite_status(invite)
            if blocked_reason:
                error = blocked_reason
            else:
                room = fetch_one('chat_rooms', {'id': f"eq.{invite['room_id']}"})
                if room is None:
                    error = '邀請對應的聊天室不存在。'
                else:
                    increment_invite_use_count(invite)
                    session.clear()
                    session['chat_authorized'] = True
                    session['chat_room_id'] = room['id']
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
    rows = supabase_request(
        'GET',
        'chat_messages',
        query={
            'room_id': f"eq.{room['id']}",
            'deleted': 'eq.false',
            'select': 'id,nickname,body,image_url,created_at',
            'order': 'created_at.desc',
            'limit': MAX_MESSAGES,
        },
    ) or []
    items = list(reversed(rows))
    return jsonify({
        'items': items,
        'rateLimitSeconds': RATE_LIMIT_SECONDS,
        'maxMessageLength': MAX_MESSAGE_LENGTH,
        'maxUploadMb': max(1, MAX_UPLOAD_BYTES // (1024 * 1024)),
    })


@app.route('/api/messages', methods=['POST'])
def create_message() -> Any:
    room = require_access()
    body = ''
    image_url = None
    image_path = None

    if request.content_type and request.content_type.startswith('multipart/form-data'):
        body = (request.form.get('body') or '').strip()
        image_file = request.files.get('image')
    else:
        payload = request.get_json(silent=True) or {}
        body = (payload.get('body') or '').strip()
        image_file = None

    if len(body) > MAX_MESSAGE_LENGTH:
        return jsonify({'error': f'訊息不能超過 {MAX_MESSAGE_LENGTH} 字。'}), 400

    if image_file and image_file.filename:
        try:
            image_url, image_path = upload_image(image_file, room['id'])
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 400

    if not body and not image_url:
        return jsonify({'error': '文字或圖片至少要有一項。'}), 400

    session_id = ensure_session_id()
    now = datetime.now(timezone.utc)
    row = fetch_one('chat_rate_limits', {'session_id': f'eq.{session_id}'})
    if row:
        last_post_at = parse_timestamp(row.get('last_post_at'))
        if last_post_at and now.timestamp() - last_post_at.timestamp() < RATE_LIMIT_SECONDS:
            return jsonify({'error': f'發言太快了，請 {RATE_LIMIT_SECONDS} 秒後再試。'}), 429

    nickname = ensure_nickname()
    supabase_request(
        'POST',
        'chat_messages',
        json_body={'room_id': room['id'], 'nickname': nickname, 'body': body, 'image_url': image_url, 'image_path': image_path},
        prefer='return=minimal',
    )
    upsert_rate_limit(session_id)
    return jsonify({'ok': True})


@app.route('/api/messages/<message_id>', methods=['DELETE'])
def delete_message(message_id: str) -> Any:
    require_admin_token()
    supabase_request('PATCH', 'chat_messages', query={'id': f'eq.{message_id}'}, json_body={'deleted': True}, prefer='return=minimal')
    return jsonify({'ok': True})


@app.route('/admin')
def admin() -> Any:
    require_admin_token()
    room = ensure_default_room()
    invites = supabase_request(
        'GET',
        'chat_invites',
        query={
            'room_id': f"eq.{room['id']}",
            'select': 'id,token,label,max_uses,use_count,expires_at,revoked,created_at',
            'order': 'created_at.desc',
        },
    ) or []
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

    room = ensure_default_room()
    invite_token = create_invite(room['id'], label=label, max_uses=max_uses)
    base = request.host_url.rstrip('/')
    return jsonify({'ok': True, 'token': invite_token, 'url': f"{base}{url_for('enter')}?invite={invite_token}"})


@app.route('/healthz')
def healthz() -> Any:
    room = ensure_default_room()
    return jsonify({'ok': True, 'room': room['slug'], 'backend': 'supabase'})


with app.app_context():
    ensure_bucket_public()
    ensure_default_room()
    ensure_bootstrap_invite()


if __name__ == '__main__':
    port = int(os.environ.get('CHAT_PORT', '8787'))
    app.run(host='127.0.0.1', port=port, debug=False)
