@echo off
chcp 65001 >nul
setlocal EnableExtensions
title 築未科技 - 同步資料上傳至雲端

cd /d "%~dp0\.."
set "PROJ=%CD%"

:: 檢查 rclone
where rclone >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [錯誤] 找不到 rclone，請先安裝。
    pause
    exit /b 1
)

:: 檢查 gdrive 遠端
rclone listremotes | findstr /C:"gdrive:" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [錯誤] 未找到 gdrive 遠端，請先執行 rclone config
    pause
    exit /b 1
)

echo ============================================================
echo 築未科技 - 資料同步上傳至 Google Drive
echo ============================================================
echo.

:: 1. 同步 D:\brain_workspace -> gdrive:Zhewei_Brain/workspace_backup
if exist "D:\brain_workspace" (
    echo [1/4] 同步 brain_workspace...
    rclone sync "D:\brain_workspace" "gdrive:Zhewei_Brain/workspace_backup" ^
        --exclude "venv*/" --exclude "**/__pycache__/" --exclude "*.pyc" ^
        --transfers 4 --checkers 8 --progress
    if %ERRORLEVEL% NEQ 0 echo [警告] brain_workspace 同步有誤
) else (
    echo [1/4] 略過 brain_workspace（路徑不存在）
)

:: 2. 同步專案（排除大型/可重建目錄）
echo.
echo [2/4] 同步專案程式碼...
rclone sync "%PROJ%" "gdrive:Zhewei_Brain/tech_repo_backup" ^
    --exclude ".venv312/" --exclude "venv*/" --exclude "node_modules/" ^
    --exclude ".git/objects/" --exclude "**/__pycache__/" --exclude "*.pyc" ^
    --exclude "*.pt" --exclude "*.onnx" --exclude "raw_footage/**" ^
    --exclude "reports/self_heal_runs/**" --exclude "Jarvis_Training/chroma_db/**" ^
    --transfers 4 --checkers 8 --progress
if %ERRORLEVEL% NEQ 0 echo [警告] 專案同步有誤

:: 3. 同步 ChromaDB 與關鍵資料（Jarvis）
if exist "%PROJ%\Jarvis_Training\chroma_db" (
    echo.
    echo [3/4] 同步 Jarvis 知識庫...
    rclone sync "%PROJ%\Jarvis_Training\chroma_db" "gdrive:Zhewei_Brain/jarvis_chroma_backup" ^
        --transfers 2 --checkers 4 --progress
)
if exist "%PROJ%\reports" (
    rclone sync "%PROJ%\reports" "gdrive:Zhewei_Brain/reports_backup" ^
        --exclude "self_heal_runs/**" --transfers 4 --checkers 8 --progress
)

:: 4. Z 槽 Reports 已在雲端，僅確認
echo.
echo [4/4] Z 槽 Reports 已透過掛載直接存於雲端，無需額外同步。
echo.
echo ============================================================
echo 同步完成。請確認雲端 drive.google.com 中 Zhewei_Brain 資料夾。
echo ============================================================
if /i not "%1"=="quiet" if /i not "%1"=="auto" pause
