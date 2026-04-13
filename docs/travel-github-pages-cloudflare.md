# travel.koxuan.com：GitHub Pages + Cloudflare 設定

這份說明是給 `travel.koxuan.com` 這個靜態旅遊網站使用。

目前網站內容位置：

- `travel/nagoya-hokuriku-osaka-2026-05-21-30/`

已經補好的設定：

- `.github/workflows/deploy-travel-pages.yml`
- `travel/nagoya-hokuriku-osaka-2026-05-21-30/CNAME`

---

## 1. GitHub Pages 這條路的概念

流程是：

```text
GitHub repo
  -> GitHub Actions
  -> GitHub Pages
  -> Cloudflare DNS / custom domain
  -> travel.koxuan.com
```

因為這個 travel site 是純靜態頁面，所以用 GitHub Pages 很適合，比走 VPS + Caddy 更輕。

---

## 2. GitHub 端要做什麼

### A. 確認 repo Pages 已啟用

進 GitHub repo：

- `Settings` → `Pages`

建議選：

- **Source**：`GitHub Actions`

如果目前 repo 已經有其他 Pages workflow，記得確認不會和這個 `deploy-travel-pages.yml` 打架。

### B. 確認 workflow 已跑

新增的 workflow：

- `.github/workflows/deploy-travel-pages.yml`

它會把這個目錄部署為 Pages artifact：

- `travel/nagoya-hokuriku-osaka-2026-05-21-30/`

### C. Custom domain

網站根目錄已加入：

- `CNAME` → `travel.koxuan.com`

這樣 GitHub Pages 會知道 custom domain 是這個。

---

## 3. Cloudflare 要怎麼設

如果你要把 `travel.koxuan.com` 指到 GitHub Pages，通常用：

### 方案：CNAME

在 Cloudflare DNS 新增：

- Type: `CNAME`
- Name: `travel`
- Target: `<your-github-pages-host>`

常見會是像這樣：

- `meteorcyclops.github.io`

如果這個 repo 對應的 Pages 網址最後不是這個，要以 GitHub Pages 顯示的 target 為準。

### Proxy 狀態

先建議：

- **DNS only**（灰雲）先測通

等 custom domain 正常後，再決定要不要開 proxy。

---

## 4. GitHub Pages 可能還要補的地方

GitHub Pages custom domain 成功後，通常要確認：

- `travel.koxuan.com` 已在 repo Pages 設定裡顯示
- HTTPS 狀態正常
- certificate 已簽發完成

如果 GitHub 顯示 DNS 檢查中，通常等一陣子就會好。

---

## 5. 你實際可以照這個順序做

1. push 已完成
2. 到 GitHub repo 的 `Settings > Pages`
3. 確認 source 用 `GitHub Actions`
4. 等 `Deploy travel.koxuan.com to GitHub Pages` workflow 跑完
5. 到 Cloudflare 新增：
   - `travel` → CNAME → GitHub Pages 指定網域
6. 回 GitHub Pages 看 custom domain 是否變成綠色正常
7. 測 `https://travel.koxuan.com`

---

## 6. 注意事項

目前這個 repo 另外已有：

- `.github/workflows/deploy-pages.yml`

那是給 `docs/` 用的 Pages 流程。

如果同一個 repo 只能保留一個 GitHub Pages 發佈流程，之後可能要決定：

- travel site 是否獨立 repo
- 或把 docs / travel 合併成同一個 Pages 站下的不同路徑
- 或改用 Cloudflare Pages / 其他靜態託管

也就是說：

**現在這版是先讓 travel site 具備走 GitHub Pages 的能力，但如果 repo 內已有其他 Pages 站，可能需要二選一或重構。**

---

## 7. 最短結論

如果你要最快上線：

- 先讓 GitHub Actions 把 travel site 發到 Pages
- 再用 Cloudflare 設 `travel.koxuan.com`

對這種純靜態旅遊網站來說，這是比 VPS 更合理的路線。
