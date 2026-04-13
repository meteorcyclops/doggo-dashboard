#!/usr/bin/env bash
set -euo pipefail

LOCAL_SITE_DIR="${LOCAL_SITE_DIR:-/Users/koxuan/.openclaw/workspace/travel/nagoya-hokuriku-osaka-2026-05-21-30}"
REMOTE_HOST="${REMOTE_HOST:-root@139.59.122.96}"
REMOTE_DIR="${REMOTE_DIR:-/srv/www/travel.koxuan.com/current}"
REMOTE_CADDYFILE="${REMOTE_CADDYFILE:-/etc/caddy/Caddyfile}"
SITE_DOMAIN="${SITE_DOMAIN:-travel.koxuan.com}"

if [[ ! -d "$LOCAL_SITE_DIR" ]]; then
  echo "Local site dir not found: $LOCAL_SITE_DIR" >&2
  exit 1
fi

echo "==> Deploying $SITE_DOMAIN"
echo "    local:  $LOCAL_SITE_DIR"
echo "    remote: $REMOTE_HOST:$REMOTE_DIR"

ssh -o BatchMode=yes "$REMOTE_HOST" "mkdir -p '$REMOTE_DIR'"

rsync -av --delete \
  --exclude '.DS_Store' \
  "$LOCAL_SITE_DIR/" "$REMOTE_HOST:$REMOTE_DIR/"

ssh -o BatchMode=yes "$REMOTE_HOST" '
set -e
chmod 755 /srv/www/travel.koxuan.com/current
find /srv/www/travel.koxuan.com/current -type d -exec chmod 755 {} \;
find /srv/www/travel.koxuan.com/current -type f -exec chmod 644 {} \;
chown -R root:root /srv/www/travel.koxuan.com
caddy validate --config /etc/caddy/Caddyfile
systemctl reload caddy
'

echo "==> Verifying https://$SITE_DOMAIN"
curl -I "https://$SITE_DOMAIN"

echo "==> Done"
