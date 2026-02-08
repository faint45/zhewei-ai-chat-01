@echo off
chcp 65001 >nul
echo ==============================================================================
echo 築未科技大腦 - 啟動遠端對話服務
echo ==============================================================================
echo.

REM 檢查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [錯誤] 未找到 Python，請先安裝 Python
    pause
    exit /b 1
)
echo [OK] Python 已安裝
echo.

REM 檢查 brain_server.py
if not exist "brain_server.py" (
    echo [錯誤] 未找到 brain_server.py 文件
    pause
    exit /b 1
)
echo [OK] brain_server.py 已找到
echo.

REM 檢查 Ollama
ollama version >nul 2>&1
if %errorlevel% neq 0 (
    echo [警告] 未找到 Ollama，將使用演示模式
    echo        安裝 Ollama 以使用本地模型：https://ollama.ai/
    echo.
) else (
    echo [OK] Ollama 已安裝
    echo.
    echo 已安裝的模型：
    ollama list
    echo.
)

REM 檢查 Tailscale
where tailscale >nul 2>&1
if %errorlevel% neq 0 (
    echo [警告] 未找到 Tailscale，遠端訪問可能不可用
    echo.
) else (
    echo [OK] Tailscale 已安裝
    echo.
    echo 獲取 Tailscale IP...
    for /f "tokens=2 delims= " %%a in ('tailscale ip -4 2^>nul') do set TAILSCALE_IP=%%a
    if defined TAILSCALE_IP (
        echo Tailscale IP: %TAILSCALE_IP%
        echo 遠端訪問地址: http://%TAILSCALE_IP%:8000
    ) else (
        echo 無法獲取 Tailscale IP，請檢查 Tailscale 狀態
    )
    echo.
)

echo ==============================================================================
echo 服務配置
echo ==============================================================================
echo.
echo 本地訪問: http://localhost:8000
echo.

if defined TAILSCALE_IP (
    echo 遠端訪問: http://%TAILSCALE_IP%:8000
) else (
    echo 遠端訪問: 請先配置 Tailscale
)
echo.

echo AI 模型: Ollama 本地模型 (如已安裝)
echo.

echo ==============================================================================
echo 啟動服務...
echo ==============================================================================
echo.
echo 按 Ctrl+C 停止服務
echo.

REM 啟動服務
python brain_server.py

pause
