# Frontend - Cloudflare Pages 部署目錄

此目錄由 GitHub Actions 自動生成，包含所有靜態前端檔案。

## 自動部署流程

```
git push → GitHub Actions → 複製靜態檔案到 frontend/ → Cloudflare Pages
```

## 包含的檔案

- `index.html` — 首頁（從 templates/index.html 複製）
- `static/` — CSS、JS、圖片等靜態資源
- `privacy.html` — 隱私權政策
- `terms.html` — 服務條款

## 注意事項

⚠️ **不要手動編輯此目錄的檔案**

所有修改應在原始檔案進行：
- 首頁 → 編輯 `templates/index.html`
- 靜態資源 → 編輯 `static/`
- 隱私/條款 → 編輯 `brain_workspace/static/privacy.html` 和 `terms.html`

修改後 `git push`，GitHub Actions 會自動同步到此目錄並部署。

## Cloudflare Pages 設定

- **專案名稱：** zhewei-tech
- **域名：** zhe-wei.net
- **Build 設定：** 無需 build，直接部署 frontend/ 目錄
- **環境變數：** 無需設定
