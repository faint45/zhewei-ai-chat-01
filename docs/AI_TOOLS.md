# AI 程式碼工具清單

本目錄包含多種 AI 程式碼工具的安裝腳本，可與 Jarvis 系統搭配使用。

## 已成功安裝 ✅

| 工具 | 安裝腳本 | 狀態 | 用途 |
|------|----------|------|------|
| **GPT Engineer** | `install_gpt_engineer.bat` | ✅ 已安裝 | 從需求生成完整專案 |
| **Aider** | `install_aider.bat` | ✅ 已安裝 | 與現有 IDE 整合 |
| **Gemini CLI** | `install_gemini_cli.bat` | ✅ 已安裝 | 大型重構、長上下文 |
| **iFlow CLI** | `install_iflow_cli.bat` | ⚠️ 需 Rust | 多模型選擇 |

## 付費工具

| 工具 | 安裝腳本 | 費用 |
|------|----------|------|
| **Claude Code** | `install_claude_code.bat` | CLI 免費，API 需 Pro ($20/月) |

---

## 安裝方式

### 1. GPT Engineer（完全免費）
```bash
scripts\install_gpt_engineer.bat
```

使用：
```bash
gpt-engineer "建立一個 Python 計算機"
```

### 2. Aider（完全免費）
```bash
scripts\install_aider.bat
```

使用：
```bash
aider                    # 對話模式
aider --file main.py     # 編輯單一檔案
```

### 3. Gemini CLI（完全免費）
```bash
scripts\install_gemini_cli.bat
```

使用：
```bash
gemini "分析這段程式碼"
```

### 4. iFlow CLI（完全免費，需 Rust 環境）
```bash
scripts\install_iflow_cli.bat
```

**前置需求：**
- 安裝 Rust: `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y`
- 重新開啟終端機

使用：
```bash
iflow analyze            # 分析專案
iflow task "優化程式碼"   # 執行任務
```

### 5. Claude Code（CLI 免費）
```bash
scripts\install_claude_code.bat
```

使用：
```bash
claude "分析程式碼"
```

---

## 工具比較

| 工具 | 免費額度 | 優勢 | 適合場景 |
|------|----------|------|----------|
| GPT Engineer | 完全免費 | 從需求生成專案 | 從零開始專案 |
| Aider | 完全免費 | 與現有 IDE 整合 | 混合開發 |
| Gemini CLI | 完全免費 | 大型重構 | 大規模重構 |
| iFlow CLI | 免費模型 | 多模型選擇 | 跨模型比較 |
| Claude Code | CLI 免費 | GitHub 整合 | 終端開發 |

---

## 建議組合

```
GPT Engineer + Aider + Gemini CLI = 完全免費組合
```

| 用途 | 工具 |
|------|------|
| 從需求生成專案 | GPT Engineer |
| 與現有 IDE 整合 | Aider |
| 大型重構 | Gemini CLI |
| Web UI + 知識庫 | Jarvis |

---

## 與 Jarvis 整合

Jarvis 系統已經整合了：
- 11 個 AI 提供者（Groq, DeepSeek, Gemini, Claude, MiniMax, Ollama 等）
- 26+ MCP 工具
- 14,600+ 營建知識庫
- Web UI 介面

這些 CLI 工具可以作為**補充**，在終端環境中使用。
