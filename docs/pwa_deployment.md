# Portal PWA 部署指南

## 概述

Portal 已升級為 Progressive Web App (PWA)，支援：
- 📱 **離線訪問** - Service Worker 快取
- 💬 **即時對話** - WebSocket 雙向通訊
- 🔐 **授權管理** - 遠端操作授權
- 📲 **安裝到桌面/主畫面** - 原生應用體驗
- 🔔 **推播通知** - 即時提醒

## 已完成的功能

### 1. PWA Manifest (`portal/manifest.json`)

完整的 PWA 配置：
- 應用名稱、圖標、主題色
- 獨立顯示模式 (standalone)
- 快捷方式 (Shortcuts) - 快速訪問 Jarvis、Bridge、Vision
- 分享目標 (Share Target) - 接收分享的文件
- 權限請求 - 通知、地理位置、相機、麥克風

### 2. Service Worker (`portal/sw.js`)

功能：
- **靜態資源快取** - 首頁、CSS、JS
- **API 快取** - 網路優先策略
- **離線頁面** - 無網路時顯示友善提示
- **推播通知** - Push API 整合
- **背景同步** - Background Sync API
- **自動更新** - 檢測新版本並提示更新

### 3. 前端功能 (`portal/index.html`)

新增元素：
- **PWA 安裝提示** - 自動彈出安裝橫幅
- **對話浮動按鈕** - 右下角聊天圖標
- **對話面板** - WebSocket 即時通訊
- **授權請求 UI** - 批准/拒絕操作
- **Service Worker 註冊** - 自動註冊和更新檢查

### 4. 後端支援 (`portal_server.py`)

新增功能：
- **WebSocket 端點** (`/ws/chat`) - 雙向通訊
- **連接管理器** - 管理多個 WebSocket 連接
- **授權系統** - 請求和回應授權
- **命令處理** - 處理用戶指令
- **Manifest 路由** - 提供 PWA 配置
- **Service Worker 路由** - 提供 SW 腳本

## 使用方式

### 本地測試

```bash
# 啟動 Portal PWA
python portal_server.py

# 訪問
http://localhost:8888
```

### 安裝 PWA

#### 桌面 (Chrome/Edge)
1. 訪問 https://zhe-wei.net
2. 點擊地址欄右側的「安裝」圖標
3. 或等待自動彈出的安裝提示
4. 點擊「安裝」

#### 手機 (iOS Safari)
1. 訪問 https://zhe-wei.net
2. 點擊分享按鈕
3. 選擇「加入主畫面」
4. 點擊「新增」

#### 手機 (Android Chrome)
1. 訪問 https://zhe-wei.net
2. 點擊右上角選單
3. 選擇「安裝應用程式」
4. 點擊「安裝」

### 使用對話功能

1. **開啟對話**
   - 點擊右下角的聊天圖標
   - 對話面板會從右側滑出

2. **發送訊息**
   - 在輸入框輸入訊息
   - 按 Enter 或點擊發送按鈕

3. **可用命令**
   - `狀態` - 查詢所有服務狀態
   - `mcp` - 查看 MCP 工具列表
   - `重啟` - 請求重啟服務（需授權）

4. **授權操作**
   - AI 執行敏感操作時會彈出授權請求
   - 顯示操作詳情
   - 點擊「批准」或「拒絕」

## 對話與授權流程

```
用戶: "重啟 gateway"
  ↓
AI: 發送授權請求
  ↓
前端: 顯示授權 UI
  ↓
用戶: 點擊「批准」
  ↓
後端: 執行重啟操作
  ↓
AI: 回報執行結果
```

## API 端點

### WebSocket

```javascript
// 連接
const ws = new WebSocket('wss://zhe-wei.net/ws/chat');

// 發送訊息
ws.send(JSON.stringify({
    type: 'message',
    content: '查詢狀態'
}));

// 接收訊息
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'message') {
        console.log('AI:', data.content);
    } else if (data.type === 'auth_request') {
        // 顯示授權請求
        showAuthUI(data);
    }
};

// 授權回應
ws.send(JSON.stringify({
    type: 'auth_response',
    request_id: 'xxx',
    approved: true
}));
```

### HTTP

```bash
# Manifest
GET /manifest.json

# Service Worker
GET /sw.js

# 服務狀態
GET /api/services/status

# 系統統計
GET /api/stats
```

## 離線功能

### 快取策略

1. **靜態資源** - 快取優先
   - HTML、CSS、JS
   - 字體、圖標

2. **API 請求** - 網路優先
   - 成功後快取
   - 離線時使用快取

3. **離線頁面** - 無網路時顯示

### 測試離線模式

1. 開啟 DevTools (F12)
2. 切換到 Network 標籤
3. 勾選 "Offline"
4. 重新整理頁面
5. 應該看到離線頁面或快取內容

## 推播通知

### 請求權限

```javascript
// 自動在 Service Worker 註冊時請求
Notification.requestPermission().then(permission => {
    if (permission === 'granted') {
        console.log('✅ 通知權限已授予');
    }
});
```

### 發送推播 (後端)

```python
# 透過 Service Worker 發送
# 需要整合 Web Push 協議
```

## 部署到生產環境

### 1. 更新 Docker Compose

已完成 - `docker-compose.yml` 已包含 portal 服務

### 2. 重啟服務

```bash
# 重啟 Portal
docker compose restart portal

# 重啟 Gateway (載入新配置)
docker compose restart gateway
```

### 3. 配置 Cloudflare Tunnel

在 Cloudflare Zero Trust 添加：
- `zhe-wei.net` → gateway:80
- `www.zhe-wei.net` → gateway:80

### 4. 測試 HTTPS

```bash
# 訪問
https://zhe-wei.net

# 檢查
- ✅ HTTPS 連接
- ✅ Service Worker 註冊
- ✅ WebSocket 連接 (wss://)
- ✅ 安裝提示顯示
```

## 圖標準備

需要準備以下尺寸的圖標 (放在 `portal/static/icons/`):

- icon-72x72.png
- icon-96x96.png
- icon-128x128.png
- icon-144x144.png
- icon-152x152.png
- icon-192x192.png
- icon-384x384.png
- icon-512x512.png

**快速生成**：
```bash
# 使用 ImageMagick 或線上工具
# 從單一 SVG/PNG 生成所有尺寸
```

## 截圖準備

需要準備截圖 (放在 `portal/static/screenshots/`):

- desktop.png (1280x720) - 桌面版截圖
- mobile.png (750x1334) - 手機版截圖

## 監控與除錯

### Chrome DevTools

1. **Application 標籤**
   - Service Workers - 查看 SW 狀態
   - Manifest - 檢查 PWA 配置
   - Cache Storage - 查看快取內容

2. **Network 標籤**
   - 查看 WebSocket 連接
   - 檢查 API 請求

3. **Console 標籤**
   - Service Worker 日誌
   - WebSocket 訊息

### 常見問題

**Q: Service Worker 未註冊**
- 確認 HTTPS 連接 (localhost 除外)
- 檢查 `/sw.js` 是否可訪問
- 查看 Console 錯誤訊息

**Q: WebSocket 連接失敗**
- 確認使用 `wss://` (HTTPS) 或 `ws://` (HTTP)
- 檢查後端 WebSocket 端點
- 查看 Network 標籤 WS 連接

**Q: 安裝提示未顯示**
- 確認滿足 PWA 安裝條件
- 檢查 manifest.json 配置
- 確認 Service Worker 已註冊

**Q: 離線模式不工作**
- 檢查 Service Worker 快取策略
- 確認資源已快取
- 查看 Cache Storage

## 效能優化

### 1. 快取策略優化

```javascript
// 預快取關鍵資源
const CRITICAL_URLS = [
  '/',
  '/manifest.json',
  '/static/css/main.css',
  '/static/js/main.js'
];
```

### 2. 壓縮資源

```bash
# 壓縮 JS/CSS
npm install -g terser cssnano

# 壓縮圖片
npm install -g imagemin-cli
```

### 3. CDN 加速

- Tailwind CSS - 已使用 CDN
- Font Awesome - 已使用 CDN

## 安全性

### 1. HTTPS 必須

PWA 功能需要 HTTPS (localhost 除外)

### 2. CSP 設定

```python
# 添加 Content Security Policy
app.add_middleware(
    CSPMiddleware,
    policy="default-src 'self'; connect-src 'self' wss://zhe-wei.net"
)
```

### 3. WebSocket 認證

```python
# 添加 JWT 認證
@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket, token: str):
    # 驗證 token
    user = verify_token(token)
    if not user:
        await websocket.close(code=1008)
        return
    # ...
```

## 未來擴展

- [ ] 整合 Push Notification Server
- [ ] 添加語音輸入 (Web Speech API)
- [ ] 相機/麥克風權限整合
- [ ] 地理位置服務
- [ ] 背景同步優化
- [ ] 更豐富的離線功能

## 總結

Portal PWA 現在支援：
✅ 離線訪問
✅ 即時對話
✅ 授權管理
✅ 安裝到設備
✅ 推播通知準備

你現在可以從任何設備訪問 https://zhe-wei.net，安裝 PWA，並透過對話介面遠端管理所有服務！
