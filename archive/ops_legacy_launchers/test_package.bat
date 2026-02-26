@echo off
REM ================================================================
REM 快速測試打包配置
REM ================================================================
chcp 65001 >nul

echo 測試 1: 檢查 Python
python --version
if errorlevel 1 (
    echo [失敗] Python 未安裝
    exit /b 1
)

echo.
echo 測試 2: 檢查 PyInstaller
python -m PyInstaller --version
if errorlevel 1 (
    echo [失敗] PyInstaller 未安裝
    exit /b 1
)

echo.
echo 測試 3: 檢查必要文件
if not exist "brain_server.py" (
    echo [失敗] 找不到 brain_server.py
    exit /b 1
)
if not exist "brain_server.spec" (
    echo [失敗] 找不到 brain_server.spec
    exit /b 1
)
if not exist "brain_workspace\static" (
    echo [警告] 找不到 brain_workspace\static 目錄
)

echo.
echo 測試 4: 檢查依賴模組
python -c "import fastapi; import uvicorn; import anthropic; print('[成功] 核心依賴已安裝')"
if errorlevel 1 (
    echo [失敗] 缺少核心依賴
    exit /b 1
)

echo.
echo ================================================================
echo 所有測試通過！可以執行 build_installer.bat 開始打包
echo ================================================================
pause
