@echo off
chcp 65001 >nul
setlocal EnableExtensions
title 築未科技 - 從雲端還原資料

cd /d "%~dp0\.."

where rclone >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [錯誤] 找不到 rclone
    pause
    exit /b 1
)

rclone listremotes | findstr /C:"gdrive:" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [錯誤] 未找到 gdrive 遠端
    pause
    exit /b 1
)

echo ============================================================
echo 築未科技 - 從雲端還原資料到本地
echo ============================================================
echo.
echo 警告：此操作會以雲端內容覆蓋本地，請確認後再執行。
set /p "REPLY=確定要還原？(y/N): "
if /i not "%REPLY%"=="y" (
    echo 已取消。
    pause
    exit /b 0
)

:: 還原 brain_workspace
if not exist "D:\brain_workspace" mkdir "D:\brain_workspace"
echo [1/4] 還原 brain_workspace...
rclone sync "gdrive:Zhewei_Brain/workspace_backup" "D:\brain_workspace" ^
    --transfers 4 --checkers 8 --progress

:: 還原專案（需指定目標）
set "PROJ=D:\zhe-wei-tech"
if not exist "%PROJ%" mkdir "%PROJ%"
echo.
echo [2/4] 還原專案程式碼...
rclone sync "gdrive:Zhewei_Brain/tech_repo_backup" "%PROJ%" ^
    --transfers 4 --checkers 8 --progress

:: 還原 ChromaDB
if not exist "%PROJ%\Jarvis_Training\chroma_db" mkdir "%PROJ%\Jarvis_Training\chroma_db"
echo.
echo [3/4] 還原 Jarvis 知識庫...
rclone sync "gdrive:Zhewei_Brain/jarvis_chroma_backup" "%PROJ%\Jarvis_Training\chroma_db" ^
    --transfers 2 --checkers 4 --progress

:: 還原 reports
if not exist "%PROJ%\reports" mkdir "%PROJ%\reports"
echo.
echo [4/4] 還原 reports...
rclone sync "gdrive:Zhewei_Brain/reports_backup" "%PROJ%\reports" ^
    --transfers 4 --checkers 8 --progress

echo.
echo ============================================================
echo 還原完成。
echo ============================================================
pause
