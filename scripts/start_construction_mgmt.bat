@echo off
chcp 65001 >nul
echo ============================================================
echo   營建自動化管理系統 v1.0.0
echo   http://localhost:8020
echo ============================================================

cd /d "%~dp0\..\construction_mgmt"

REM 嘗試使用 Jarvis venv
if exist "..\Jarvis_Training\.venv312\Scripts\python.exe" (
    set PYTHON=..\Jarvis_Training\.venv312\Scripts\python.exe
    echo [INFO] 使用 Jarvis venv Python
) else (
    set PYTHON=python
    echo [INFO] 使用系統 Python
)

REM 檢查依賴
%PYTHON% -c "import fastapi" 2>nul
if errorlevel 1 (
    echo [INFO] 安裝依賴...
    %PYTHON% -m pip install -r requirements.txt
)

echo.
echo [啟動] 營建自動化管理系統...
echo [網址] http://localhost:8020
echo.
%PYTHON% app.py

pause
