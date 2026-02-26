@echo off
chcp 65001 >nul
echo ======================================================
echo    築未科技 AI 系統 - 一鍵部署與自癒測試
echo ======================================================
echo.

set SCRIPT_DIR=%~dp0
set PYTHON_EXE=python
set BRAIN_WS=D:\brain_workspace

echo [1/5] 檢查環境變數...
if not defined BRAIN_WORKSPACE set BRAIN_WORKSPACE=%BRAIN_WS%
echo    BRAIN_WORKSPACE: %BRAIN_WORKSPACE%

echo.
echo [2/5] 執行系統自檢...
echo.

echo    A. 檢查 Python 環境...
%PYTHON_EXE% -c "import sys; print(f'    Python 版本: {sys.version}')" 2>nul
if errorlevel 1 (
    echo    ❌ Python 未找到，請確認 Python 路徑
    pause
    exit /b 1
)

echo.
echo    B. 檢查核心服務狀態...
echo    測試 Brain Server (port 8002)...
curl -s -o nul -w "%%{http_code}" http://localhost:8002/health 2>nul
if errorlevel 7 (
    echo    ⚠️ Brain Server 未運行
) else (
    echo    ✅ Brain Server 正常
)

echo.
echo    C. 檢查 Ollama 服務...
curl -s -o nul -w "%%{http_code}" http://localhost:11434/api/tags 2>nul
if errorlevel 7 (
    echo    ⚠️ Ollama 未運行
) else (
    echo    ✅ Ollama 正常
)

echo.
echo    D. 檢查 GPU 加速...
%PYTHON_EXE% -c "import torch; print(f'    CUDA 可用: {torch.cuda.is_available()}')" 2>nul
if errorlevel 0 (
    echo    ✅ CUDA 正常
) else (
    echo    ⚠️ CUDA 不可用，使用 CPU
)

echo.
echo [3/5] 執行 autonomous_coder 自檢模組...
%PYTHON_EXE% "%SCRIPT_DIR%..\ai_modules\autonomous_coder.py" 2>nul

echo.
echo [4/5] 執行 test_system.py...
echo.
%PYTHON_EXE% "%SCRIPT_DIR%..\test_system.py"
set TEST_RESULT=%errorlevel%

echo.
echo [5/5] 部署完成摘要...
echo.
if %TEST_RESULT% == 0 (
    echo    ✅ 所有測試通過
    echo    ✅ 系統健康狀態: 正常
) else (
    echo    ⚠️ 部分測試失敗
    echo    ℹ️  請查看 test_report.json 了解詳情
)

echo.
echo ======================================================
echo    部署檢查完成
echo    報告位置: test_report.json
echo ======================================================
pause
