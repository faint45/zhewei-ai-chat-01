@echo off
chcp 65001 >nul 2>&1
title 築未科技 Jarvis AI 客戶端安裝程式
color 0A

echo ============================================================
echo   築未科技 Jarvis AI 客戶端 — 一鍵安裝程式
echo   版本: 1.0.0
echo ============================================================
echo.

:: ── 檢查管理員權限 ──
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [提示] 建議以管理員身份執行以獲得最佳體驗
    echo.
)

:: ── 設定安裝路徑 ──
set "INSTALL_DIR=%USERPROFILE%\JarvisAI"
set "OLLAMA_DIR=%INSTALL_DIR%\ollama"
set "DATA_DIR=%INSTALL_DIR%\data"
set "KB_DIR=%INSTALL_DIR%\knowledge_base"
set "LOG_FILE=%INSTALL_DIR%\install.log"

echo [1/8] 建立安裝目錄...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
if not exist "%DATA_DIR%" mkdir "%DATA_DIR%"
if not exist "%KB_DIR%" mkdir "%KB_DIR%"
echo   → %INSTALL_DIR%
echo.

:: ── 記錄安裝日誌 ──
echo [%date% %time%] 開始安裝 > "%LOG_FILE%"

:: ── 檢查 Python ──
echo [2/8] 檢查 Python 環境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   [!] 未偵測到 Python，正在下載安裝...
    echo   [!] 請從 https://www.python.org/downloads/ 下載 Python 3.12+
    echo   [!] 安裝時請勾選 "Add Python to PATH"
    echo.
    echo   按任意鍵在安裝 Python 後繼續...
    pause >nul
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VER=%%i
echo   → %PYTHON_VER%
echo.

:: ── 檢查/安裝 Ollama ──
echo [3/8] 檢查 Ollama 本地 AI 引擎...
where ollama >nul 2>&1
if %errorlevel% neq 0 (
    echo   [!] 未偵測到 Ollama，正在下載...
    echo   → 下載 Ollama for Windows...
    curl -L -o "%TEMP%\OllamaSetup.exe" "https://ollama.com/download/OllamaSetup.exe"
    if exist "%TEMP%\OllamaSetup.exe" (
        echo   → 啟動 Ollama 安裝程式...
        start /wait "" "%TEMP%\OllamaSetup.exe"
        echo   → Ollama 安裝完成
    ) else (
        echo   [!] 下載失敗，請手動從 https://ollama.com 下載安裝
    )
) else (
    echo   → Ollama 已安裝
)
echo.

:: ── 啟動 Ollama 服務 ──
echo [4/8] 啟動 Ollama 服務並下載 AI 模型...
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I "ollama.exe" >NUL
if %errorlevel% neq 0 (
    echo   → 啟動 Ollama 服務...
    start "" ollama serve
    timeout /t 5 /nobreak >nul
)

:: 下載必要模型
echo   → 下載主要推理模型 (qwen3:8b)...
ollama pull qwen3:8b 2>>"%LOG_FILE%"
echo   → 下載程式碼模型 (qwen2.5-coder:7b)...
ollama pull qwen2.5-coder:7b 2>>"%LOG_FILE%"
echo   → 下載 Embedding 模型 (nomic-embed-text)...
ollama pull nomic-embed-text:latest 2>>"%LOG_FILE%"
echo   → 模型下載完成
echo.

:: ── 建立 Python 虛擬環境 ──
echo [5/8] 建立 Python 虛擬環境...
if not exist "%INSTALL_DIR%\venv" (
    python -m venv "%INSTALL_DIR%\venv"
)
call "%INSTALL_DIR%\venv\Scripts\activate.bat"

:: 安裝依賴
echo   → 安裝 Python 套件...
pip install --quiet --upgrade pip 2>>"%LOG_FILE%"
pip install --quiet chromadb==1.5.0 requests httpx fastapi uvicorn 2>>"%LOG_FILE%"
echo   → 套件安裝完成
echo.

:: ── 複製核心檔案 ──
echo [6/8] 部署 Jarvis AI 核心模組...
set "SRC_DIR=%~dp0.."

:: 核心模組
copy /Y "%SRC_DIR%\license_manager.py" "%INSTALL_DIR%\" >nul 2>&1
copy /Y "%SRC_DIR%\client_config.py" "%INSTALL_DIR%\" >nul 2>&1
copy /Y "%SRC_DIR%\usage_metering.py" "%INSTALL_DIR%\" >nul 2>&1
copy /Y "%SRC_DIR%\kb_snapshot.py" "%INSTALL_DIR%\" >nul 2>&1
copy /Y "%SRC_DIR%\auth_manager.py" "%INSTALL_DIR%\" >nul 2>&1
copy /Y "%SRC_DIR%\ai_service.py" "%INSTALL_DIR%\" >nul 2>&1

:: AI 模組
if not exist "%INSTALL_DIR%\ai_modules" mkdir "%INSTALL_DIR%\ai_modules"
xcopy /Y /Q "%SRC_DIR%\ai_modules\*.*" "%INSTALL_DIR%\ai_modules\" >nul 2>&1

:: 知識庫學習系統
if not exist "%INSTALL_DIR%\Jarvis_Training" mkdir "%INSTALL_DIR%\Jarvis_Training"
copy /Y "%SRC_DIR%\Jarvis_Training\local_learning_system.py" "%INSTALL_DIR%\Jarvis_Training\" >nul 2>&1
copy /Y "%SRC_DIR%\Jarvis_Training\jarvis_brain.py" "%INSTALL_DIR%\Jarvis_Training\" >nul 2>&1
copy /Y "%SRC_DIR%\Jarvis_Training\env_loader.py" "%INSTALL_DIR%\Jarvis_Training\" >nul 2>&1

:: brain_workspace
if not exist "%INSTALL_DIR%\brain_workspace" mkdir "%INSTALL_DIR%\brain_workspace"
if not exist "%INSTALL_DIR%\brain_workspace\static" mkdir "%INSTALL_DIR%\brain_workspace\static"
xcopy /Y /Q /S "%SRC_DIR%\brain_workspace\static\*.*" "%INSTALL_DIR%\brain_workspace\static\" >nul 2>&1

echo   → 核心模組部署完成
echo.

:: ── License 啟用 ──
echo [7/8] License 啟用...
echo.
echo   請輸入您的 License Key（格式：ZW-XXXX-XXXX-XXXX-XXXX）
echo   如果沒有 License，直接按 Enter 使用免費體驗版
echo.
set /p LICENSE_DATA="  License 資料: "

if not "%LICENSE_DATA%"=="" (
    echo   → 正在啟用 License...
    "%INSTALL_DIR%\venv\Scripts\python.exe" -c "import sys; sys.path.insert(0, r'%INSTALL_DIR%'); from license_manager import activate_license; r=activate_license('%LICENSE_DATA%'); print('  → 啟用成功！方案:', r.get('tier_name','?')) if r.get('ok') else print('  → 啟用失敗:', r.get('error','?'))"
) else (
    echo   → 使用免費體驗版（可隨時升級）
)
echo.

:: ── 建立啟動腳本 ──
echo [8/8] 建立啟動捷徑...

:: 主啟動腳本
(
echo @echo off
echo chcp 65001 ^>nul 2^>^&1
echo title Jarvis AI 客戶端
echo.
echo :: 啟動 Ollama
echo tasklist /FI "IMAGENAME eq ollama.exe" 2^>NUL ^| find /I "ollama.exe" ^>NUL
echo if %%errorlevel%% neq 0 ^(
echo     echo 啟動 Ollama AI 引擎...
echo     start "" ollama serve
echo     timeout /t 3 /nobreak ^>nul
echo ^)
echo.
echo :: 啟動 Jarvis
echo call "%INSTALL_DIR%\venv\Scripts\activate.bat"
echo cd /d "%INSTALL_DIR%"
echo echo.
echo echo ============================================================
echo echo   Jarvis AI 客戶端已啟動
echo echo   本地 AI: http://localhost:11434
echo echo ============================================================
echo echo.
echo python -c "from client_config import get_config; import json; c=get_config(); s=c.get_system_status(); print('系統狀態:'); print(json.dumps(s, ensure_ascii=False, indent=2))"
echo echo.
echo pause
) > "%INSTALL_DIR%\啟動Jarvis.bat"

:: 系統狀態檢查腳本
(
echo @echo off
echo chcp 65001 ^>nul 2^>^&1
echo call "%INSTALL_DIR%\venv\Scripts\activate.bat"
echo cd /d "%INSTALL_DIR%"
echo echo === License 狀態 ===
echo python license_manager.py validate
echo echo.
echo echo === 離線狀態 ===
echo python license_manager.py offline-check
echo echo.
echo echo === 系統狀態 ===
echo python -c "from client_config import get_config; import json; c=get_config(); print(json.dumps(c.get_system_status(), ensure_ascii=False, indent=2))"
echo pause
) > "%INSTALL_DIR%\系統狀態檢查.bat"

echo   → 啟動腳本已建立
echo.

:: ── 完成 ──
echo ============================================================
echo   安裝完成！
echo ============================================================
echo.
echo   安裝路徑: %INSTALL_DIR%
echo   啟動方式: 雙擊「啟動Jarvis.bat」
echo   狀態檢查: 雙擊「系統狀態檢查.bat」
echo.
echo   已安裝的 AI 模型:
echo     - qwen3:8b（主要推理）
echo     - qwen2.5-coder:7b（程式碼）
echo     - nomic-embed-text（語意搜尋）
echo.
echo   [%date% %time%] 安裝完成 >> "%LOG_FILE%"
echo.
echo 按任意鍵結束安裝程式...
pause >nul
