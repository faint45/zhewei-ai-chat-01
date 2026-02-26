# 男神拍拍 - AI 攝影助手

## 📱 功能特色

### 拍照功能
- **前後鏡頭切換** - 支援手機前後鏡頭
- **即時預覽** - Camera API 即時顯示
- **網格輔助線** - 三分法構圖輔助

### AI 修圖功能
- **10 種男生濾鏡** - 專為男性設計的濾鏡風格
- **人像美顏** - 自動美化肤色、光滑肌肤
- **風格濾鏡** - 多種風格可選（韓系、日系、欧美等）
- **智能增強** - 自動調整亮度、對比、飽和度
- **手動調整** - 亮度、對比、暖色、銳化、模糊

### 姿勢參考庫
- **10 種姿勢建議** - 經典站姿、坐姿、側顏等
- **姿勢提示** - 點擊姿勢顯示拍攝技巧
- **分類瀏覽** - 基本、坐姿、人像、街頭、運動

### 參考資料庫
- **姿勢建議** - 經典拍照姿勢
- **光線技巧** - 自然光、逆光、側光等
- **場景推薦** - 城市、自然、咖啡廳等
- **風格靈感** - 韓系、日系、欧美、復古

### 照片管理
- **歷史記錄** - 儲存最近 100 張照片
- **本地儲存** - 使用 localStorage
- **刪除功能** - 單張或全部清除

### PWA 特性
- **可安裝** - 加入主螢幕使用
- **離線支援** - 部分功能離線可用
- **手機優化** - 觸控友善介面

## 🚀 使用方式

### 方式一：透過 brain_server 訪問
```
https://brain.zhe-wei.net/photo-app
```

### 方式二：本地運行
```bash
# 啟動 brain_server.py
python brain_server.py

# 訪問
http://localhost:8002/photo-app
```

### 方式三：獨立運行（需要 HTTP Server）
```bash
# 使用 Python http.server
cd photo_app
python -m http.server 8080

# 訪問
http://localhost:8080
```

## 📁 檔案結構

```
photo_app/
├── index.html          # 主頁面
├── styles.css          # 樣式表
├── app.js              # 主程式
├── manifest.json       # PWA 配置
├── icons/              # 圖示
│   ├── icon.svg
│   ├── icon-72.png
│   ├── icon-96.png
│   ├── ...
│   └── generate_icons.py  # 圖示生成腳本
└── screenshots/        # 截圖
```

## 🔧 自訂 AI API

目前 AI 修圖使用瀏覽器內建的 CSS Filter，如需更強大的 AI 修圖，可整合外部 API：

### 整合範例（修改 app.js）

```javascript
// 替換 applyAIToImage 方法
async applyAIToImage(imageData, mode) {
    const response = await fetch('YOUR_AI_API_ENDPOINT', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            image: imageData,
            mode: mode
        })
    });
    const result = await response.json();
    return result.processedImage;
}
```

### 推薦 API
- **Replicate** - Stable Diffusion API
- **Clipdrop API** - AI 圖片處理
- **PicWish API** - 人像美化

## 📱 安裝到手機

1. 使用手機瀏覽器訪問 `/photo-app`
2. 點擊「安裝」按鈕
3. 選擇「加入主螢幕」
4. 即可像原生 App 一樣使用

## 🔒 隱私說明

- 所有照片儲存在瀏覽器 localStorage
- 不會上傳到伺服器
- 請定期備份重要照片

## 📝 更新日誌

### v1.0.0 (2026-02-20)
- 初始版本
- 拍照功能
- AI 修圖（CSS Filter）
- 姿勢參考庫
- 照片管理
- PWA 支援
