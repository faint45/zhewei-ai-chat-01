# 築未科技主腦自動規則（由經驗日誌生成）

- 更新時間：2026-02-10T23:42:50
- 來源：Experience_Logs.jsonl / Error_Logs.jsonl / 大智庫 SOP_Logs.jsonl

## 高價值對策（優先遵循）
- 若 Gemini 模型不存在，先改用可用模型（例如 gemini-2.0-flash 或已配置預設模型），避免重試同一錯誤模型。
- 所有檔案/命令工作目錄需落在 D 槽或 Z 槽；遇到路徑錯誤時優先切到 D:/brain_workspace。
- 遇到 Ollama 連線異常時，先檢查 OLLAMA_BASE_URL 與服務狀態，再決定是否呼叫 deploy_service 重啟。

## 高頻問題摘要
- 工作目錄僅允許 D 槽或 Z 槽
- API 錯誤: 404 models/gemini-1.5-flash is not found for API version v1beta, or is not supported for generateContent. Call ListModels to see the list of available models and their supported methods.
- Ollama 服務異常: All connection attempts failed
- mock final answer

## 高頻任務摘要
- 請執行 deploy_service 重啟 Ollama 服務
- 測試
- test multi agent flow

## 執行原則
- 回答前先比對上述高頻問題，避免重犯已知錯誤。
- 同類任務優先套用已驗證成功的對策與路徑。
- 若新錯誤未覆蓋，完成後必須寫回 Experience，供下一輪自動更新規則。
