# Jarvis 前端模組系統

## 架構

```
jarvis.html          ← 主框架（HTML 模板 + CSS + 組裝器），不可修改
modules/
  mod-chat.js        ← AI 對話 + WebSocket + 對話紀錄
  mod-code.js        ← 編碼模擬 + 即時預覽（類似 AI Studio）
  mod-image.js       ← 文字生圖（ComfyUI）
  mod-learn.js       ← 學習大模型精華
  mod-system.js      ← 系統控制 / 遠端截圖 / 系統資訊
```

## 規則

1. **不可修改** `jarvis.html` 的 HTML 模板和 CSS 樣式
2. **不可修改** 各模組的既有功能（標記 `請勿修改` 的區塊）
3. **可擴充** 各模組中標記 `★ 後續接入本地模型` 的位置
4. **可新增** 新模組 `mod-xxx.js`，然後在 `jarvis.html` 中引入

## 模組介面規範

每個模組 export 一個工廠函數到 `window`：

```javascript
window.JarvisModXxx = function (BASE, { ref, nextTick, watch }) {
    // BASE = API 根路徑（如 https://brain.zhe-wei.net）
    // ref, nextTick, watch = Vue 3 Composition API

    const myData = ref('');

    const myMethod = async () => { /* ... */ };

    // 可選：init 函數，在 onMounted 時被主框架呼叫
    const init = () => { /* 初始化邏輯 */ };

    return { myData, myMethod, init };
};
```

## 新增模組步驟

1. 建立 `modules/mod-xxx.js`，遵循上方介面規範
2. 在 `jarvis.html` 加入 `<script src="/static/modules/mod-xxx.js"></script>`
3. 在主框架 `setup()` 中初始化：`const xxx = JarvisModXxx(BASE, {ref, nextTick, watch});`
4. 在 `return` 中展開：`...xxx,`
5. 如需新 Tab，在 `tabLabels` 加入 key，並在 HTML 加入對應的 `v-show` 區塊

## 本地模型接入點

| 模組 | 接入位置 | 說明 |
|------|----------|------|
| mod-chat.js | `sendChat()` 中的 `providers` 陣列 | 改為 `['ollama']` 即可用本地模型 |
| mod-code.js | `generateCode()` 中的 API 端點 | 可改為呼叫本地 Ollama |
| mod-image.js | `generateImage()` 中的 API 端點 | 已接 ComfyUI |
| mod-learn.js | `askAndLearn()` 中的 `providers` | 可加入 `'ollama'` |
| mod-system.js | 無需修改 | 直接呼叫 Host API |

## 後端 API 對應

| 前端模組 | 後端 API | 檔案 |
|----------|----------|------|
| mod-chat.js | `/ws`, `/api/jarvis/ask-and-learn`, `/api/jarvis/chat-history` | brain_server.py |
| mod-code.js | `/api/jarvis/generate-code` | brain_server.py |
| mod-image.js | `/api/jarvis/generate-image` | brain_server.py |
| mod-learn.js | `/api/jarvis/ask-and-learn`, `/api/jarvis/batch-learn`, `/api/jarvis/learning-stats` | brain_server.py |
| mod-system.js | `/api/host/*` | brain_server.py → host_api.py |
