# 築未科技 AI 對話窗口 - 外部部署

單一 deploy 資料夾支援 Git 倉庫、Netlify、Vercel、Cloudflare Pages 等多種部署。

## 🌐 部署選項

### 選項一：GitHub Pages（推薦）
1. 將此 `deploy/` 資料夾內容上傳到 GitHub 倉庫
2. 在倉庫設定中啟用 GitHub Pages
3. 訪問：`https://[您的用戶名].github.io/[倉庫名]`

### 選項二：Netlify
1. 拖拽此文件夾到 [netlify.com](https://netlify.com)
2. 自動部署完成
3. 獲得專屬網址

### 選項三：Vercel
1. 連結 GitHub 倉庫到 Vercel
2. 自動部署
3. 全球 CDN 加速

## 📱 功能特色

- ✅ 響應式設計 - 手機電腦完美適配
- ✅ 全球訪問 - 任何網路、任何設備
- ✅ 即時對話 - 支援智能 AI 回應
- ✅ 無需維護 - 雲端自動運行
- ✅ 安全加密 - HTTPS 保護

## 🔧 自定義配置

如需整合真實 AI 服務，請修改 `index.html` 中的：
```javascript
// 替換為您的 AI API 端點
const API_BASE = 'https://your-ai-api.com';
```

## 📞 支援

如有問題，請聯繫技術支援團隊。