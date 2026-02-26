# PyAutoGUI 部署與測試（Windows）

## 0) 目前環境狀態（本機檢查結果）

- 系統 Python：`3.14.2`
- 系統 pip：可用
- 專案 venv：`Jarvis_Training\.venv312`（Python `3.12.10`）
- `PyAutoGUI`：已安裝（`0.9.54`）

## 1) 建議使用方式

為了避免套件混亂，請優先使用專案虛擬環境執行：

```powershell
& "D:\zhe-wei-tech\Jarvis_Training\.venv312\Scripts\python.exe" --version
```

若要重裝 PyAutoGUI：

```powershell
& "D:\zhe-wei-tech\Jarvis_Training\.venv312\Scripts\python.exe" -m pip install -U pyautogui pillow
```

## 2) 第一支腳本（已建立）

- 檔案：`scripts/my_agent.py`
- 功能：
  - 5 秒倒數
  - 滑鼠移動 + 點擊
  - 自動打字
  - 按 Enter

執行：

```powershell
& "D:\zhe-wei-tech\Jarvis_Training\.venv312\Scripts\python.exe" "D:\zhe-wei-tech\scripts\my_agent.py"
```

## 3) 座標工具（已建立）

- 檔案：`scripts/mouse_position.py`
- 功能：即時顯示滑鼠座標，按 `Ctrl + C` 結束

執行：

```powershell
& "D:\zhe-wei-tech\Jarvis_Training\.venv312\Scripts\python.exe" "D:\zhe-wei-tech\scripts\mouse_position.py"
```

## 4) 安全注意事項

- `PyAutoGUI` 的 `FAILSAFE=True` 已啟用。
- 緊急停止方式：滑鼠移到螢幕左上角 `(0,0)`。
- 第一次執行請先在不重要的視窗測試，避免誤操作。

## 5) 你現有系統內的對應能力

你也可以直接用 Discord Bot 指令，不需手動寫腳本：

- `!pc desktop`
- `!pc open <app>`
- `!pc type <text>`
- `!pc screenshot`

若你要，我可以下一步把 `my_agent.py` 升級成「讀取任務 JSON 後自動執行」版本，讓 Agent Hub 可直接下發桌面操作。
