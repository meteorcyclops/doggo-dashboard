# CHANGELOG

## v1.0 - 2026-04-13

這個版本是目前確認可用、已打 tag 的穩定基準版。

### Added
- 建立 `dog.koxuan.com` 並成功從 GitHub Pages 遷移到 VPS。
- 新增 VPS 靜態站部署流程，站點由 Caddy 直接提供。
- 新增本機部署腳本：`scripts/deploy_dog_dashboard.sh`。
- 新增 GitHub Actions 自動部署到 VPS 的 workflow。
- 新增安全版 deploy user `dogdeploy` 的部署架構。
- 新增 VPS 架構說明文件：
  - `docs/vps-site-architecture.md`
  - `docs/vps-site-architecture.html`
- 新增安全版自動部署設計文件：
  - `docs/secure-vps-auto-deploy.md`

### Changed
- dashboard 視覺已回退到 cyberpunk / neon restyle 之前的較穩定版本。
- `dog.koxuan.com` 改為由 VPS 自動部署流程管理。
- 部署流程從手動更新，提升為可本機腳本部署與 GitHub Actions 自動部署。

### Fixed
- 修正 VPS 靜態檔部署後檔案權限過嚴，導致 Caddy 無法讀取的問題。
- 修正 GitHub Actions deploy 流程中的 SSH user typo 與 rsync 權限問題。
- 確認 `dog.koxuan.com` 自動部署流程已可成功執行。

### Notes
- 目前 GitHub Actions 仍有 Node 20 deprecation warning，但不影響功能。
- `v1.0` tag 已建立並推上 GitHub，可作為穩定回復點。
