# 築未科技 — MetaGPT 使用指南

## 已完成安裝

- 安裝位置：`D:\zhe-wei-tech\MetaGPT_env\.venv`
- 主程式：`D:\zhe-wei-tech\MetaGPT_env\.venv\Scripts\metagpt.exe`
- 配置檔：`C:\Users\user\.metagpt\config2.yaml`
- 模型切換腳本：`scripts\switch_metagpt_model.ps1`

## 一鍵啟動

- Gemini：`Start_MetaGPT_Gemini.bat`
- Ollama：`Start_MetaGPT_Ollama.bat`

## 模型切換（手動）

```powershell
# 切 Gemini
powershell -ExecutionPolicy Bypass -File scripts\switch_metagpt_model.ps1 -Provider gemini -Model gemini-2.0-flash

# 切 Ollama
powershell -ExecutionPolicy Bypass -File scripts\switch_metagpt_model.ps1 -Provider ollama -Model zhewei-brain:latest
```

## 驗證結果

已通過 MetaGPT smoke test（Ollama）：
- 任務：`Build a tiny hello world cli tool`
- 輸出：`workspace\metagpt_smoke4\docs\`、`workspace\metagpt_smoke4\resources\`

## 架構定位（你的最終陣容）

- OpenHands：單任務 AI 工程師（寫碼/測試/修 Bug）
- MetaGPT：多角色協作（PM -> 架構師 -> 工程師 -> QA）
- Jarvis Bot：知識問答、工作流路由、日常操作入口

## 注意事項

1. 若 Gemini 出現 `models/gemini-pro not found`，請先切回 Ollama 使用。
2. Windows 主控台編碼問題已透過 UTF-8 環境變數處理。
3. 如需下一步接入 Discord Bot，我可以幫你加 `!metagpt` 指令。
