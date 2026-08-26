#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
LOCAL_DOCS_DIR="${LOCAL_DOCS_DIR:-$REPO_ROOT/docs}"
REMOTE_HOST="${REMOTE_HOST:-root@139.59.122.96}"
REMOTE_DIR="${REMOTE_DIR:-/srv/www/dog.koxuan.com/current}"
REMOTE_CADDYFILE="${REMOTE_CADDYFILE:-/etc/caddy/Caddyfile}"
SITE_DOMAIN="${SITE_DOMAIN:-dog.xuan.tw}"

if [[ ! -d "$LOCAL_DOCS_DIR" ]]; then
  echo "Local docs dir not found: $LOCAL_DOCS_DIR" >&2
  exit 1
fi

echo "==> Building fresh dashboard data"
DOGGO_BUILD_TRIGGER=manual-vps python3 "$SCRIPT_DIR/build_dashboard_data.py"
python3 "$SCRIPT_DIR/validate_static_site.py"

echo "==> Deploying $SITE_DOMAIN"
echo "    local:  $LOCAL_DOCS_DIR"
echo "    remote: $REMOTE_HOST:$REMOTE_DIR"

ssh -o BatchMode=yes "$REMOTE_HOST" "mkdir -p '$REMOTE_DIR'"

rsync -av --delete \
  --exclude '.DS_Store' \
  "$LOCAL_DOCS_DIR/" "$REMOTE_HOST:$REMOTE_DIR/"

ssh -o BatchMode=yes "$REMOTE_HOST" '
set -e
chmod 755 /srv/www/dog.koxuan.com/current
find /srv/www/dog.koxuan.com/current -type d -exec chmod 755 {} \;
find /srv/www/dog.koxuan.com/current -type f -exec chmod 644 {} \;
chown -R root:root /srv/www/dog.koxuan.com
caddy validate --config /etc/caddy/Caddyfile
systemctl reload caddy
'

echo "==> Verifying https://$SITE_DOMAIN"
curl -I "https://$SITE_DOMAIN"

echo "==> Done"
