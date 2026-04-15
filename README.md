# Doggo Dashboard

一個可愛、像素風、偏星之卡比戰鬥框氣質的靜態展示儀表板。  
公開站以 **GitHub Pages** 部署；**台股與新聞在 CI 由 Python 拉取後寫入 `docs/data.json`**，瀏覽器只讀同源的 JSON（避開 CORS）。

## Live Demo

- GitHub Pages: https://meteorcyclops.github.io/doggo-dashboard/

## 資料來源與免責

- **台股報價**：公開頁初始資料會先讀建置腳本用 [yfinance](https://github.com/ranaroussi/yfinance) 產生的 `docs/data.json`，盤中再由同源優先的 `/api/tw-quotes` 做較即時更新。若 live API 不可用，前端會自動退回建置時快照。也可用 `window.DOGGO_LIVE_TW_QUOTES_URL` 覆寫即時來源。
- **新聞**：預設合併 [自由時報 財經](https://news.ltn.com.tw/rss/business.xml) 與 [國際](https://news.ltn.com.tw/rss/world.xml) RSS 標題與連結（繁體中文）。
- **川普發言快訊**：建置時由 `scripts/trump_truth_tracker.py` 的 `fetch_posts` 讀取第三方存檔站 [trumpstruth.org](https://www.trumpstruth.org/) 的公開 HTML，解析後寫入 `data.json` 的 `trumpTruth`（摘要 + 外連至該站存檔頁）。**這不是官方 Truth Social、也不是本 repo 對該站或內容的背書**；若該站 HTML 結構變更，需手動更新 `scripts/trump_truth_tracker.py` 內的 regex 解析邏輯。
- **任務卡片**：仍由 `docs/data.seed.json` 的示範 `jobs` 合併進 `docs/data.json`，與真實 cron／LINE 無關。

**法遵／免責**：本專案顯示之股價與新聞皆為**延遲或第三方公開資訊**，僅供 UI 展示與學習用途，**不構成投資建議**，亦不保證即時性或完整性。川普發言區塊之文字為**截短摘要**並連至第三方存檔站，**非官方平台、不代表本專案立場**，請自行判讀原文與來源可信度。

## 特色

- 可愛狗狗像素角色（依 `dog.state` 切換動畫：idle／bone／excited／worried／sleepy）
- 白天 / 黑夜主題切換
- 台股快報、新聞雷達、任務小書與系統讀值
- 純靜態前端 + 建置時抓資料，可安全公開展示

## 專案結構

```text
.
├─ docs/
│  ├─ index.html       # 公開展示頁
│  ├─ style.css
│  ├─ ui.js
│  ├─ data.json        # 建置產出（含 quotes / feed / trumpTruth / dog / provenance）
│  ├─ data.seed.json   # 示範 jobs 等種子，供腳本 merge
│  └─ .nojekyll
├─ scripts/
│  ├─ build_dashboard_data.py   # 合併種子 + yfinance + RSS + trumpTruth → data.json
│  └─ trump_truth_tracker.py    # 川普帖文 HTML 抓取（亦供 CLI digest/alerts）
├─ requirements.txt
└─ .github/
   └─ workflows/
      └─ deploy-pages.yml
```

## 本機只跑腳本預覽資料

在 repo 根目錄建立虛擬環境並執行建置（會覆寫 `docs/data.json`）：

```bash
cd /path/to/doggo-dashboard
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/build_dashboard_data.py
```

可選環境變數（逗號分隔）：

- `DOGGO_STOCK_SYMBOLS`：例如 `2330,0050,2884`（多為上市 `.TW`；上櫃個股可能需改腳本為 `.TWO`）
- `DOGGO_RSS_URLS`：自訂 RSS 列表

完成後再啟動靜態伺服器預覽頁面：

```bash
cd docs
python3 -m http.server 4173 --bind 127.0.0.1
```

瀏覽：http://127.0.0.1:4173

## 開發方式

在本機修改 `docs/` 或 `scripts/` 後 push 到 GitHub；workflow 會在部署前執行 Python 產生最新的 `docs/data.json` 再上傳。

## 部署流程

### GitHub Pages（原本方式）

- Push 至 `master`，且變更包含 `docs/**`、`scripts/**`、`requirements.txt`、`README.md` 或 workflow 本身時觸發部署。
- 另設 **UTC** 排程 `0 1,7,13,19 * * *`（每日四次）重新建置並部署，讓公開頁有機會更新報價與新聞（仍受來源與 Actions 排程影響）。
- 也可在 Actions 分頁手動 **Run workflow**。

### VPS（目前 `dog.koxuan.com` 使用方式）

目前 `dog.koxuan.com` 已改由 VPS 上的 Caddy 直接提供靜態檔，站點目錄為：

```text
/srv/www/dog.koxuan.com/current
```

本機可用以下腳本部署：

```bash
./scripts/deploy_dog_dashboard.sh
```

這個腳本會做：
- 將 `docs/` rsync 到 VPS
- 修正遠端檔案權限
- 驗證 Caddy 設定
- reload Caddy
- 驗證 `https://dog.koxuan.com`

可覆寫的環境變數：
- `LOCAL_DOCS_DIR`
- `REMOTE_HOST`
- `REMOTE_DIR`
- `REMOTE_CADDYFILE`
- `SITE_DOMAIN`

## 安全說明

公開版：

- **不會連到本機 OpenClaw** 或你的私有服務
- **不會讀取真實 cron／LINE／gateway 狀態**（頂多顯示種子裡的示範欄位）
- 新聞仍以 **GitHub Actions 建置時** 產生的靜態 JSON 為主，瀏覽器不向第三方 RSS 直接請求
- 台股即時模式由受控後端 `/api/tw-quotes` 代理提供，瀏覽器不直接向第三方行情來源請求

若需要私有／本機即時連線版，請將 `docs/` 與 `chat/` 一起部署，並確認前端可連到 `/api/tw-quotes`。後端可用 `TW_QUOTES_CACHE_SECONDS` 調整台股即時 API 快取秒數，勿把金鑰放進靜態頁面。

## 後續可以再做

- 自動切換白天 / 黑夜（依時段）
- 更完整的角色動畫
- 更多像素風任務卡樣式
- 多頁展示模式
