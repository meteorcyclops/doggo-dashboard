# LINE webhook bridge

這條 bridge 的用途是把公開的 `bot.koxuan.com/line/webhook` 請求，轉回本機 OpenClaw gateway 的：

- `http://127.0.0.1:18789/line/webhook`

## 架構

- VPS Caddy: `bot.koxuan.com` → tailnet `100.74.22.60:18889`
- 本機 bridge: `0.0.0.0:18889` → `127.0.0.1:18789/line/webhook`
- 本機 OpenClaw gateway: `127.0.0.1:18789`

## 正式檔案

- 腳本：`scripts/line_webhook_bridge.py`
- launchd：`launchd/com.koxuan.line-webhook-bridge.plist`

## 安裝 / 更新

```bash
chmod +x scripts/line_webhook_bridge.py
mkdir -p ~/Library/LaunchAgents state
cp launchd/com.koxuan.line-webhook-bridge.plist ~/Library/LaunchAgents/
launchctl unload ~/Library/LaunchAgents/com.koxuan.line-webhook-bridge.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/com.koxuan.line-webhook-bridge.plist
launchctl kickstart -k gui/$(id -u)/com.koxuan.line-webhook-bridge
```

## 驗證

```bash
curl -i http://127.0.0.1:18889/line/webhook
curl -i https://bot.koxuan.com/line/webhook
```

都應該回 `200 OK`。
