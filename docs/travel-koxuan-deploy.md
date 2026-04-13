# travel.koxuan.com 部署說明

這個站是靜態旅遊網站，內容目前來自：

- `travel/nagoya-hokuriku-osaka-2026-05-21-30/`

## 建議部署目錄

```text
/srv/www/travel.koxuan.com/current
```

這樣可和 `dog.koxuan.com` 的靜態站結構保持一致，後續也方便做 deploy user 權限隔離。

## Caddy 範本

參考：

- `travel/Caddyfile.travel.koxuan.com.example`

建議的 Caddy 站台配置為：

- domain: `travel.koxuan.com`
- root: `/srv/www/travel.koxuan.com/current`
- `file_server`
- 啟用 gzip / zstd

## 手動部署腳本

已新增：

- `scripts/deploy_travel_site.sh`

預設：

- 本機來源：`/Users/koxuan/.openclaw/workspace/travel/nagoya-hokuriku-osaka-2026-05-21-30`
- 遠端：`root@139.59.122.96:/srv/www/travel.koxuan.com/current`

執行方式：

```bash
bash scripts/deploy_travel_site.sh
```

也可自行覆寫：

```bash
LOCAL_SITE_DIR=/path/to/site \
REMOTE_HOST=user@host \
REMOTE_DIR=/srv/www/travel.koxuan.com/current \
bash scripts/deploy_travel_site.sh
```

## GitHub Actions 自動部署

已新增 workflow：

- `.github/workflows/deploy-travel-vps.yml`

此 workflow 會：

1. checkout repo
2. 透過 deploy key SSH 到 VPS
3. rsync `travel/nagoya-hokuriku-osaka-2026-05-21-30/` 到 `/srv/www/travel.koxuan.com/current/`
4. 修正目錄與檔案權限
5. 驗證 Caddy 設定
6. reload Caddy
7. 驗證 `https://travel.koxuan.com`

## GitHub Secrets

建議使用與 dog deploy 類似的 secrets：

- `VPS_DEPLOY_HOST`
- `VPS_DEPLOY_USER`
- `VPS_DEPLOY_KEY`

如果 travel 要使用不同 deploy user，也可以再分成 travel 專用 secrets。

## 建議的下一步

1. 在 VPS 建立 `/srv/www/travel.koxuan.com/current`
2. 將 `travel.koxuan.com` 的 Caddy site block 加入 `/etc/caddy/Caddyfile`
3. 確認 DNS 已指向 VPS
4. 手動部署一次或觸發 GitHub Actions
5. 檢查 HTTPS 與首頁是否正常載入
