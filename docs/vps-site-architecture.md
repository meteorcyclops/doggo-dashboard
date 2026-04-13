# VPS 站點架構說明

這份文件是用來幫 Koxuan 理解目前 VPS 的實際站點架構，以及未來把 `dog.koxuan.com` 從 GitHub Pages 搬到 VPS 後，應該怎麼設計才會乾淨、可擴充、好維護。

---

## 1. 目前的實際狀況

```text
Internet
   |
   |  dog.koxuan.com  -> GitHub Pages
   |  bot.koxuan.com  -> VPS (139.59.122.96)
   |
   +------------------------------+
                                  |
                           +------v------+
                           |   Caddy     |
                           |  on VPS     |
                           +------+------+
                                  |
                                  | reverse proxy
                                  v
                         100.74.22.60:18889
                         (Tailscale/private service)
```

### 目前可以這樣理解

- `dog.koxuan.com`
  - 現在是放在 **GitHub Pages**
  - 所以 dashboard 其實還沒有搬到 VPS

- `bot.koxuan.com`
  - 現在是先打到 **VPS**
  - VPS 上由 **Caddy** 收流量
  - Caddy 再把流量反向代理到 **Tailscale 私網服務** `100.74.22.60:18889`

### 目前 VPS 的角色

這台 VPS 現在不是單純的網站主機，它比較像：

- 一個 **公開入口**
- 一個 **反向代理節點**
- 未來可以升級成 **多站點入口主機**

---

## 2. 我建議的未來架構

如果之後不只一個網站，那最好的方向不是「把一個網站搬上去」而已，而是把這台 VPS 設計成：

> **單一公開入口 + 多 subdomain + 每站獨立管理 + Caddy 統一處理 TLS 與流量**

```text
Internet
   |
   |-- dog.koxuan.com ----> VPS :80/:443
   |-- bot.koxuan.com ----> VPS :80/:443
   |-- lab.koxuan.com ----> VPS :80/:443
   |-- api.koxuan.com ----> VPS :80/:443
   |
   v
+------------------------------------------------+
| VPS 139.59.122.96                              |
|                                                |
|  Caddy (唯一公開入口)                          |
|                                                |
|  路由規則：                                     |
|  - dog.koxuan.com -> 靜態網站                  |
|  - bot.koxuan.com -> reverse proxy             |
|  - lab.koxuan.com -> 靜態網站 / 測試站         |
|  - api.koxuan.com -> 後端服務                  |
+----------------------+-------------------------+
                       |
        +--------------+--------------+
        |                             |
        v                             v
  /srv/www/...                  127.0.0.1 / Tailscale / Docker
  靜態網站目錄                    動態服務 / 私網服務 / API
```

---

## 3. 最推薦的落地方式

### 站點類型分兩種

#### A. 靜態站
適合：
- dashboard 展示頁
- landing page
- 個人頁面
- 文件頁

做法：
- 檔案放在 VPS 本機目錄
- Caddy 直接 `file_server`

例如：
- `dog.koxuan.com`
- `lab.koxuan.com`

#### B. 動態站 / 服務
適合：
- bot 後端
- API
- Python / Node app
- 內網服務對外發布

做法：
- 服務跑在本機 port、Docker、或 Tailscale 內網機器
- Caddy 用 `reverse_proxy`

例如：
- `bot.koxuan.com`
- `api.koxuan.com`

---

## 4. 建議的檔案結構

```text
/srv/www/
  dog.koxuan.com/
    current/
      index.html
      style.css
      ui.js
      data.json

  lab.koxuan.com/
    current/
      index.html
      ...
```

這樣每個站都分開，不會全部混在一起。

### 為什麼不用全部塞進 `/var/www/html`

因為之後一多站就會變亂：
- 檔案難找
- 權限難管
- 更新容易誤蓋
- rollback 比較痛苦

`/srv/www/<domain>/current` 這種結構會乾淨很多。

---

## 5. 建議的 Caddy 配置概念

```caddyfile
dog.koxuan.com {
    root * /srv/www/dog.koxuan.com/current
    file_server
}

bot.koxuan.com {
    reverse_proxy 100.74.22.60:18889
}
```

### 這代表什麼

- `dog.koxuan.com`
  - 由 VPS 直接提供靜態檔案
  - 不需要 GitHub Pages

- `bot.koxuan.com`
  - 維持現在的反向代理架構
  - 不影響原本的 bot 流量入口

---

## 6. 遷移後的實際樣子

```text
                              GitHub repo
                         (doggo-dashboard source)
                                      |
                                      | deploy static files
                                      v
                   /srv/www/dog.koxuan.com/current
                                      |
Internet                              |
   |                                  |
   | dog.koxuan.com                   |
   | bot.koxuan.com                   |
   v                                  v
+-----------------------------------------------------------+
| VPS: 139.59.122.96                                        |
|                                                           |
|  Caddy                                                    |
|  ├─ dog.koxuan.com -> static files                        |
|  |                    /srv/www/dog.koxuan.com/current     |
|  |                                                        |
|  └─ bot.koxuan.com -> reverse_proxy 100.74.22.60:18889    |
|                                                           |
|  UFW: allow 22 / 80 / 443                                |
|  Fail2ban: sshd                                           |
|  Tailscale: enabled                                       |
+-----------------------------------------------------------+
```

---

## 7. 這種架構的優點

### 1. 清楚
- 對外永遠只看 VPS
- 每個網域各司其職

### 2. 可擴充
- 未來多網站只要加 DNS + Caddy 設定
- 不需要重做整台機器

### 3. 安全相對好控
- 對外只開 `22 / 80 / 443`
- 其他服務不需要直接暴露
- 盡量交給 Caddy 收流量

### 4. 好維護
- 憑證交給 Caddy
- 網站檔案有固定位置
- 服務可以靜態、反代混搭

---

## 8. 目前已知的 VPS 狀態

### 好的部分
- Ubuntu 24.04 LTS
- UFW 已啟用，預設 incoming deny
- 只放行 22 / 80 / 443
- Fail2ban 已啟用
- 自動安全更新已啟用
- Caddy 已可正常運作
- Tailscale 已啟用

### 之後可再改善
- SSH 雖然禁用密碼登入，但目前仍允許 root 直接登入
- 如果未來網站變多，建議改成：
  - 非 root 部署
  - 每站獨立目錄與部署流程
  - 規劃備份與 rollback

---

## 9. 我對 Koxuan 目前最推薦的做法

### 第一階段
1. 保留 `bot.koxuan.com` 現況
2. 把 `dog.koxuan.com` 從 GitHub Pages 遷到 VPS
3. 在 VPS 建立獨立靜態站目錄
4. 用 Caddy 提供 `dog.koxuan.com`

### 第二階段
5. 把部署流程整理乾淨
6. 規劃未來其他站點命名與目錄結構
7. 視情況把 root-only 部署改成較安全的方式

---

## 10. 一句話版結論

> 這台 VPS 最適合被設計成「你的網站入口主機」。
> 
> - 靜態站直接由 Caddy 提供
> - 動態服務走 reverse proxy
> - 每個網站用獨立 subdomain
> - 所有外部流量都統一進 VPS

這樣最穩，也最適合你之後慢慢把更多東西搬上來。
