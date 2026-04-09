# Doggo Dashboard

一個可愛、像素風、偏星之卡比戰鬥框氣質的靜態展示儀表板。  
這個 repo 目前提供的是 **公開展示版**，使用 **假資料**，不連你的本機服務。

## Live Demo

- GitHub Pages: https://meteorcyclops.github.io/doggo-dashboard/

## 特色

- 可愛狗狗像素角色
- 白天 / 黑夜主題切換
- 可愛戰鬥框風格 HUD
- 純靜態網頁，可安全公開展示
- 展示資料來自 `docs/data.json`

## 專案結構

```text
.
├─ docs/
│  ├─ index.html      # 公開展示頁
│  ├─ style.css       # 樣式
│  ├─ ui.js           # 前端互動
│  ├─ data.json       # 假資料
│  └─ .nojekyll
└─ .github/
   └─ workflows/
      └─ deploy-pages.yml
```

## 開發方式

你可以先在本機改好，再 push 到 GitHub，自動部署到 GitHub Pages。

### 本機預覽

```bash
cd docs
python3 -m http.server 4173 --bind 127.0.0.1
```

然後開：

- http://127.0.0.1:4173

## 部署流程

目前已設定 GitHub Actions：

- 只要 push 到 `master`
- 且變更包含 `docs/**`、`README.md` 或 workflow 本身
- 就會自動部署到 GitHub Pages

## 安全說明

這個公開版：

- **不會連到本機 OpenClaw**
- **不會讀取真實 cron / LINE / gateway 狀態**
- 僅展示 UI 與假資料

如果你要做私有版 / 本機版，可以另外保留一套只在本機跑的資料來源。

## 後續可以再做

- 自動切換白天 / 黑夜
- 更完整的角色動畫
- 更多像素風任務卡樣式
- 多頁展示模式
