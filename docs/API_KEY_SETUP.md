# API Key 設定指南

## 快速開始

### 方法一：使用設定腳本（推薦）

```batch
# 執行設定腳本
scripts\setup_api_keys.bat
```

腳本會依序要求輸入：
1. DeepSeek API Key
2. MiniMax API Key
3. Gemini API Key
4. Anthropic API Key

### 方法二：手動設定環境變數

```batch
# DeepSeek
setx DEEPSEEK_API_KEY "your_deepseek_key" /M

# MiniMax
setx MINIMAX_API_KEY "your_minimax_key" /M

# Gemini
setx GEMINI_API_KEY "your_gemini_key" /M

# Anthropic (Claude)
setx ANTHROPIC_API_KEY "your_anthropic_key" /M
```

---

## API Key 取得位置

| API | 網址 | 定價 |
|-----|------|------|
| **DeepSeek** | https://platform.deepseek.com | $0.55/1M in, $2.19/1M out |
| **MiniMax** | https://platform.minimax.io | $0.15/1M in, $1.20/1M out |
| **Gemini** | https://aistudio.google.com | $0.075/1M in, $0.30/1M out |
| **Claude** | https://console.anthropic.com | $3.00/1M in, $15.00/1M out |

---

## 驗證設定

```bash
python -c "
import os
print('DEEPSEEK_API_KEY:', '✅' if os.environ.get('DEEPSEEK_API_KEY') else '❌')
print('MINIMAX_API_KEY:', '✅' if os.environ.get('MINIMAX_API_KEY') else '❌')
print('GEMINI_API_KEY:', '✅' if os.environ.get('GEMINI_API_KEY') else '❌')
print('ANTHROPIC_API_KEY:', '✅' if os.environ.get('ANTHROPIC_API_KEY') else '❌')
"
```

---

## 重啟服務

設定完成後，請重啟 Brain Server：

```batch
python brain_server.py
```

---

## 成本監控

用量監控頁面：`https://jarvis.zhe-wei.net/usage-dashboard`

或使用 API：
```bash
curl http://localhost:8002/api/usage/today
```
