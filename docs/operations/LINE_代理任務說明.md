# LINE 代理任務（Agent Hub）

## 可用按鈕

在 `http://127.0.0.1:8002/agent-hub` 可用：

- `開啟 LINE（主機端）`
- `OCR 讀取 LINE 畫面（不保證穩定）`

## 技術實作

- 主機腳本：`scripts/line_agent.py`
  - `--action open`：啟動 LINE 執行檔
  - `--action read_ocr`：截圖 LINE 視窗訊息區並 OCR
- 任務橋接：
  - 佇列：`reports/agent_host_jobs.json`
  - 結果：`reports/agent_host_results/<task_id>.json`

## 限制與風險

- LINE 桌面版沒有官方讀訊 API。
- OCR 結果可能誤判、漏字，且容易受 UI 更新影響。
- 若要高穩定讀取，建議改用有官方 API 的通訊平台（例如企業 webhook / bot API）。

## 依賴

- 已有：`pyautogui`
- OCR 需額外：
  - Python 套件：`pytesseract`
  - 系統程式：Tesseract OCR（需可執行）
