# chat.koxuan.com production guide

一個邀請制匿名聊天室，使用 Flask + SQLite，適合先跑在單機或 VPS 上，再由 Nginx / Caddy 反向代理。

## 目前版本有什麼

- 邀請制入口，不直接裸奔在公網
- 匿名暱稱自動產生
- 單房間 MVP
- 基本發言限流
- 訊息長度限制
- Admin 頁可產生 invite link
- `/healthz` 健康檢查
- production session cookie 安全設定
- Gunicorn 啟動方式

## 不適合的場景

目前仍是輕量版本，不建議直接拿來跑大量即時聊天場景。若之後要升級，優先方向會是：

- Postgres 取代 SQLite
- WebSocket / Realtime
- CAPTCHA / Turnstile
- invite revocation / moderation UI 完整化
- 觀測與告警

## 本機開發

```bash
cd chat
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
export $(grep -v '^#' .env | xargs)
python app.py
```

預設跑在 `127.0.0.1:8787`

## production 啟動

```bash
cd chat
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export CHAT_SECRET_KEY="請換成長隨機字串"
export CHAT_ADMIN_TOKEN="請換成長隨機 admin token"
gunicorn -c gunicorn.conf.py wsgi:app
```

## 必要環境變數

至少要設定：

- `CHAT_SECRET_KEY`
- `CHAT_ADMIN_TOKEN`

否則程式會直接拒絕啟動。

其他可調整項目請看：

- `chat/.env.example`

## 反向代理建議

- `chat.koxuan.com` 反代到 `127.0.0.1:8787`
- 外層加 TLS
- 外層再加 rate limit
- 若走 Cloudflare，也建議開基本 bot / abuse 保護

## systemd 例子

```ini
[Unit]
Description=chat.koxuan.com
After=network.target

[Service]
WorkingDirectory=/opt/chat
Environment=CHAT_SECRET_KEY=replace-me
Environment=CHAT_ADMIN_TOKEN=replace-me-admin
ExecStart=/opt/chat/.venv/bin/gunicorn -c gunicorn.conf.py wsgi:app
Restart=always
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
```

## 首次使用

啟動後系統會自動建立：

- 預設房間 `lobby`
- 一筆 bootstrap invite

你可以到 SQLite 看 invite token：

```bash
sqlite3 data/chat.db 'select token,label,use_count,max_uses from invites;'
```

或打開 admin 頁：

```text
http://127.0.0.1:8787/admin?token=你的_CHAT_ADMIN_TOKEN
```

## 健康檢查

```bash
curl http://127.0.0.1:8787/healthz
```

預期回傳：

```json
{"ok":true,"room":"lobby"}
```
