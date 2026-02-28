@echo off
chcp 65001 >nul
title 築未科技 USB 可攜版打包工具
echo ============================================
echo   築未科技 AI 助手 — USB 可攜版打包
echo ============================================
echo.

:: 設定目標 USB 磁碟
set /p USB_DRIVE="請輸入 USB 磁碟代號 (例如 E): "
set TARGET=%USB_DRIVE%:\ZheweiAI

echo.
echo 目標目錄: %TARGET%
echo.
pause

:: 建立目錄結構
echo [1/7] 建立目錄結構...
mkdir "%TARGET%" 2>nul
mkdir "%TARGET%\python" 2>nul
mkdir "%TARGET%\ollama" 2>nul
mkdir "%TARGET%\models" 2>nul
mkdir "%TARGET%\brain" 2>nul
mkdir "%TARGET%\data" 2>nul
mkdir "%TARGET%\data\auth" 2>nul
mkdir "%TARGET%\data\chat_history" 2>nul
mkdir "%TARGET%\data\kb_snapshots" 2>nul

:: 複製 Python 可攜版
echo [2/7] 複製 Python 環境...
if exist "D:\zhe-wei-tech\.venv312" (
    xcopy /E /I /Q "D:\zhe-wei-tech\.venv312" "%TARGET%\python\venv" >nul
    echo   ✓ Python venv 已複製
) else (
    echo   ⚠ 找不到 .venv312，請手動下載 Python Embedded
)

:: 複製 Ollama
echo [3/7] 複製 Ollama...
if exist "%LOCALAPPDATA%\Programs\Ollama" (
    xcopy /E /I /Q "%LOCALAPPDATA%\Programs\Ollama" "%TARGET%\ollama\bin" >nul
    echo   ✓ Ollama 程式已複製
) else (
    echo   ⚠ 找不到 Ollama，請手動下載 https://ollama.com/download
)

:: 複製模型
echo [4/7] 複製 Ollama 模型（這可能需要很長時間）...
if exist "%USERPROFILE%\.ollama\models" (
    echo   正在複製模型檔案...
    xcopy /E /I /Q "%USERPROFILE%\.ollama\models" "%TARGET%\models" >nul
    echo   ✓ 模型已複製
) else (
    echo   ⚠ 找不到模型目錄
)

:: 複製 Brain Server 核心
echo [5/7] 複製 Brain Server 核心檔案...
set SRC=D:\zhe-wei-tech

:: 核心 Python 檔案
for %%f in (brain_server.py ai_service.py auth_manager.py agent_logic.py agent_tools.py config_ai.py ollama_client.py) do (
    if exist "%SRC%\%%f" copy /Y "%SRC%\%%f" "%TARGET%\brain\" >nul
)

:: AI 模組
if exist "%SRC%\ai_modules" (
    xcopy /E /I /Q "%SRC%\ai_modules" "%TARGET%\brain\ai_modules" >nul
)

:: 核心模組
if exist "%SRC%\core" (
    xcopy /E /I /Q "%SRC%\core" "%TARGET%\brain\core" >nul
)

:: 靜態資源
if exist "%SRC%\brain_workspace\static" (
    xcopy /E /I /Q "%SRC%\brain_workspace\static" "%TARGET%\brain\static" >nul
)

:: PWA
if exist "%SRC%\frontend\pwa" (
    xcopy /E /I /Q "%SRC%\frontend\pwa" "%TARGET%\brain\pwa" >nul
)

:: 授權和配置
if exist "%SRC%\brain_workspace\auth" (
    xcopy /E /I /Q "%SRC%\brain_workspace\auth" "%TARGET%\data\auth" >nul
)

echo   ✓ Brain Server 核心已複製

:: 建立啟動腳本
echo [6/7] 建立啟動腳本...
(
echo @echo off
echo chcp 65001 ^>nul
echo title 築未科技 AI 助手
echo echo ============================================
echo echo   築未科技 AI 助手 — USB 可攜版
echo echo ============================================
echo echo.
echo.
echo :: 設定環境變數
echo set SCRIPT_DIR=%%~dp0
echo set OLLAMA_HOME=%%SCRIPT_DIR%%models
echo set OLLAMA_MODELS=%%SCRIPT_DIR%%models
echo set PATH=%%SCRIPT_DIR%%ollama\bin;%%SCRIPT_DIR%%python\venv\Scripts;%%PATH%%
echo.
echo :: 檢查 Ollama
echo echo [1/3] 啟動 Ollama...
echo start /B "" "%%SCRIPT_DIR%%ollama\bin\ollama.exe" serve
echo timeout /t 3 /nobreak ^>nul
echo.
echo :: 檢查模型
echo echo [2/3] 檢查 AI 模型...
echo "%%SCRIPT_DIR%%ollama\bin\ollama.exe" list
echo echo.
echo.
echo :: 啟動 Brain Server
echo echo [3/3] 啟動 AI 伺服器...
echo cd /d "%%SCRIPT_DIR%%brain"
echo set AI_MODE=local_only
echo set OLLAMA_BASE_URL=http://localhost:11434
echo set BRAIN_DATA_DIR=%%SCRIPT_DIR%%data
echo "%%SCRIPT_DIR%%python\venv\Scripts\python.exe" brain_server.py
echo.
echo pause
) > "%TARGET%\啟動.bat"

:: 建立說明文件
(
echo # 築未科技 AI 助手 — USB 可攜版
echo.
echo ## 使用方式
echo 1. 將 USB 隨身碟插入電腦
echo 2. 雙擊「啟動.bat」
echo 3. 等待 AI 伺服器啟動（約 30 秒）
echo 4. 開啟瀏覽器訪問 http://localhost:8000
echo.
echo ## 系統需求
echo - Windows 10/11 64位元
echo - 16GB 以上記憶體（推薦 32GB）
echo - USB 3.0 以上（推薦 USB 3.2）
echo.
echo ## 目錄結構
echo - python/    — Python 執行環境
echo - ollama/    — Ollama AI 引擎
echo - models/    — AI 模型檔案
echo - brain/     — 核心伺服器
echo - data/      — 用戶資料
echo - 啟動.bat   — 一鍵啟動
echo.
echo ## 注意事項
echo - 首次啟動可能較慢（模型載入）
echo - 請勿在 USB 運行時直接拔出
echo - 模型資料約 20GB，請使用 64GB 以上 USB
echo.
echo ## 授權
echo 本軟體受 License Key 保護，請聯繫 allen34556@gmail.com 取得授權。
echo.
echo © 2026 築未科技 版權所有
) > "%TARGET%\README.md"

echo   ✓ 啟動腳本已建立

:: 統計
echo [7/7] 計算大小...
echo.
echo ============================================
echo   打包完成！
echo   目標: %TARGET%
echo ============================================
echo.
dir /s "%TARGET%" | find "個檔案"
echo.
echo 請測試: 雙擊 %TARGET%\啟動.bat
echo.
pause
