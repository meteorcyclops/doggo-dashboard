# dog.koxuan.com 安全版自動部署方案

這份文件是給 Koxuan 的安全版自動部署設計稿。

目標：
- push 到 GitHub 後，自動把 `dog.koxuan.com` 部署到 VPS
- 但不要用 root 長期金鑰直接暴露給 GitHub Actions
- 儘量把 deploy 權限縮到最小

---

## 1. 設計原則

這套流程採用以下原則：

1. **不用 root 當 GitHub Actions 登入帳號**
2. **用專用 deploy user**
3. **deploy user 只碰固定站點目錄**
4. **deploy user 若需要 sudo，只允許極少數固定命令**
5. **GitHub Secret 只放 deploy 專用私鑰，不放日常管理用 SSH key**

---

## 2. 推薦架構

```text
GitHub push
   |
   v
GitHub Actions
   |
   |  SSH (deploy-only key)
   v
VPS deploy user
   |
   | rsync / upload
   v
/srv/www/dog.koxuan.com/current
   |
   | limited sudo
   v
caddy validate + reload
```

---

## 3. VPS 上應該新增的角色

### deploy user

建議建立一個專用帳號，例如：

- `dogdeploy`

用途：
- 只用來接收 GitHub Actions 的部署
- 不拿來做人類日常 SSH 管理

### 這個 user 應該能做的事

- 寫入：`/srv/www/dog.koxuan.com/current`
- 執行有限 sudo：
  - `caddy validate --config /etc/caddy/Caddyfile`
  - `systemctl reload caddy`

### 這個 user 不應該能做的事

- 不能任意 sudo
- 不能寫整個 `/srv`
- 不能直接管理其他站
- 不能碰系統敏感設定

---

## 4. GitHub 端需要的 Secrets

建議至少放：

- `VPS_DEPLOY_HOST`
  - 例如：`139.59.122.96`

- `VPS_DEPLOY_USER`
  - 例如：`dogdeploy`
  - 注意不要打錯成 `dogdepl` 之類的截斷字串

- `VPS_DEPLOY_KEY`
  - deploy 專用 SSH private key

如之後要加強，可再放：
- `VPS_DEPLOY_PORT`（如果不是 22）

---

## 5. GitHub Actions 應該做的事

workflow 只做固定流程：

1. checkout repo
2. 必要時先 build / 更新 `docs/`
3. 用 deploy key SSH 到 VPS
4. rsync `docs/` 到指定目錄
5. 修正權限（限部署目錄）
6. 驗證 Caddy 設定
7. reload Caddy
8. 驗證 `https://dog.koxuan.com`

### 不該做的事

- 不要執行任意 shell script from user input
- 不要允許操作全系統目錄
- 不要直接使用 root 帳號

---

## 6. repo 建議調整

### 目前已有
- `scripts/deploy_dog_dashboard.sh`

### 接下來建議新增
- `.github/workflows/deploy-dog-vps.yml`
- 可選：`scripts/remote_finalize_dog_deploy.sh`

其中：
- local script 仍保留給手動部署
- GitHub Actions 用自己的 workflow
- 若要再收權限，可把遠端收尾動作集中在固定 script

---

## 7. 我建議的最小安全版本

### 先做這版就夠好

- 新建 `dogdeploy`
- 新建 deploy 專用 SSH key
- `dogdeploy` 可寫 `dog.koxuan.com` 目錄
- `dogdeploy` 只能 sudo：
  - `caddy validate --config /etc/caddy/Caddyfile`
  - `systemctl reload caddy`
- GitHub Actions 只部署 `docs/`

這版已經比「直接把 root key 丟進 GitHub」安全很多。

---

## 8. 風險說明

### 主要風險

1. GitHub repo 被入侵
2. GitHub Secrets 洩漏
3. workflow 被惡意修改
4. deploy user 權限設太大

### 怎麼降低風險

- 使用 deploy-only key
- 使用最小權限 deploy user
- 限制 sudo 指令
- 把部署目錄與其他站點隔離
- 不共用 root 私鑰

---

## 9. 推薦執行順序

1. 在 VPS 建 `dogdeploy`
2. 建 deploy-only SSH key
3. 設定 `authorized_keys`
4. 調整 `/srv/www/dog.koxuan.com` 權限給 deploy user
5. 設定 sudoers 白名單
6. 建 GitHub Actions workflow
7. 在 GitHub Secrets 放 key / host / user
8. 測一次 push deploy

---

## 10. 一句話版結論

> 安全版自動部署可以做，而且值得做。
> 但正確做法不是讓 GitHub 直接拿 root 登 VPS，
> 而是建立一個 **deploy 專用身份**，只給它剛剛好的權限。
