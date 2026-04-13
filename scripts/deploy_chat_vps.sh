#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/opt/chat-koxuan}"
APP_DIR="$APP_ROOT/chat"
SERVICE_NAME="${SERVICE_NAME:-chat-koxuan.service}"
APP_USER="${APP_USER:-chatapp}"
APP_GROUP="${APP_GROUP:-chatapp}"

mkdir -p "$APP_ROOT"
cd "$APP_DIR"

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

chown -R "$APP_USER":"$APP_GROUP" "$APP_ROOT"
chmod 750 "$APP_ROOT"

systemctl daemon-reload
systemctl restart "$SERVICE_NAME"
systemctl status "$SERVICE_NAME" --no-pager
