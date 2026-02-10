@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ========================================
REM 築未科技大腦 - 全系統啟動腳本
REM ========================================

echo.
echo ========================================
echo    築未科技大腦 - 全系統啟動
echo ========================================
echo.

REM 設置腳本目錄
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM 服務進程存儲數組
set PROCESS_COUNT=0

REM ========================================
REM 步驟 1: 檢查 Z 槽（Google Drive）
REM ========================================
echo [1/5] 檢查 Z 槽狀態...
if exist "Z:\" (
    echo     ✓ Z 槽已掛載
) else (
    echo     ⚠ Z 槽未掛載，請先執行 Rclone 掛載腳本
    echo     提示: 右鍵 "挂载 Google Drive 为 Z 槽.bat" 以管理員身份執行
    echo.
)

REM ========================================
REM 步驟 2: 檢查 Python 環境
REM ========================================
echo [2/5] 檢查 Python 環境...
where python >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo     ✓ Python 已安裝: !PYTHON_VERSION!
) else (
    echo     ✗ Python 未找到，請安裝 Python 3.x
    pause
    exit /b 1
)

REM ========================================
REM 步驟 3: 啟動主腦服務器
REM ========================================
echo [3/5] 啟動主腦服務器...
if exist "brain_server.py" (
    start "築未大腦 - 對話服務 (Port 8000)" cmd /k "python brain_server.py"
    echo     ✓ 主腦服務器啟動中... (http://localhost:8000)
    set /a PROCESS_COUNT+=1
) else (
    echo     ✗ 找不到 brain_server.py
)

REM 等待 2 秒讓服務初始化
timeout /t 2 /nobreak >nul

REM ========================================
REM 步驟 4: 啟動監控服務
REM ========================================
echo [4/5] 啟動監控服務...
if exist "monitoring_dashboard.py" (
    start "築未大腦 - 監控面板 (Port 8001)" cmd /k "python monitoring_dashboard.py"
    echo     ✓ 監控服務啟動中... (http://localhost:8001)
    set /a PROCESS_COUNT+=1
) else if exist "monitoring_service.py" (
    echo     ℹ 監控服務器已存在，可能已在運行
) else (
    echo     ⚠ 監控服務文件未找到
)

REM 等待 2 秒讓服務初始化
timeout /t 2 /nobreak >nul

REM ========================================
REM 步驟 5: 檢查 Ollama 服務
REM ========================================
echo [5/5] 檢查 Ollama 服務...
where ollama >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2" %%i in ('ollama list 2^>nul ^| findstr /C:"llama" /C:"qwen"') do (
        set MODEL_FOUND=1
    )
    if defined MODEL_FOUND (
        echo     ✓ Ollama 已安裝並有模型可用
        echo       訪問: http://localhost:11434
    ) else (
        echo     ⚠ Ollama 已安裝但沒有找到模型
        echo       提示: 執行 "ollama pull llama3.2" 安裝模型
    )
) else (
    echo     ⚠ Ollama 未安裝
    echo       提示: 從 https://ollama.com 下載安裝
)

REM ========================================
REM 啟動完成
REM ========================================
echo.
echo ========================================
echo    ✨ 啟動完成！
echo ========================================
echo.
echo 已啟動的服務:
echo   • 對話服務: http://localhost:8000
echo   • 監控面板: http://localhost:8001
echo   • Ollama:   http://localhost:11434
echo.
echo 遠端訪問（需要 Tailscale VPN）:
echo   • 對話服務: http://100.116.133.23:8000
echo   • 監控面板: http://100.116.133.23:8001
echo.
echo iOS 使用方式:
echo   1. Safari 打開: http://100.116.133.23:8000
echo   2. 分享 → 添加到主屏幕
echo   3. 像原生 App 一樣使用
echo.
echo 提示: 關閉所有服務請執行 "停止所有服務.bat"
echo ========================================
echo.

REM 開啟瀏覽器
echo 3 秒後自動開啟瀏覽器...
timeout /t 3 /nobreak >nul
start http://localhost:8000

endlocal
