# chat.koxuan.com production guide

這版聊天室已改成 **Flask 前端 + Supabase Postgres 後端**。

## 架構

- Flask: 處理 invite gate、session、admin 頁
- Supabase Postgres: rooms / invites / messages / rate limits
- 反向代理: Nginx 或 Caddy

這樣比 SQLite 更像正式 production，之後要接 Realtime、多房間、moderation 也比較順。

## 先做什麼

先把 schema 套到 Supabase：

- `supabase/chat_schema.sql`

如果你已經有 Supabase 專案，可以直接在 SQL editor 執行。

## 必要環境變數

至少要設定：

- `CHAT_SECRET_KEY`
- `CHAT_ADMIN_TOKEN`
- `CHAT_SUPABASE_URL`
- `CHAT_SUPABASE_SERVICE_ROLE_KEY`

可參考：

- `chat/.env.example`

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

## production 啟動

```bash
cd chat
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export CHAT_SECRET_KEY="請換成長隨機字串"
export CHAT_ADMIN_TOKEN="請換成長隨機 admin token"
export CHAT_SUPABASE_URL="https://your-project.supabase.co"
export CHAT_SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
gunicorn -c gunicorn.conf.py wsgi:app
```

## 健康檢查

```bash
curl http://127.0.0.1:8787/healthz
```

預期回傳類似：

```json
{"ok":true,"room":"lobby","backend":"supabase"}
```

## 注意

這版後端使用的是 **service role key**，所以：

- 只能放在 server side
- 不能送到前端
- 不要 commit 到 repo

## 下一步建議

接下來最值得做的會是：

- 把 `chat_schema.sql` 納入正式 migration 流程
- 改成 Supabase Realtime，減少前端輪詢
- 補 invite revoke / expiry UI
- 補 moderation / audit log
