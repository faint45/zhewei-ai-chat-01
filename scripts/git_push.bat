@echo off
chcp 65001 >nul
cd /d "%~dp0\.."
if "%~1"=="" (
    echo 用法: scripts\git_push.bat ^<你的 GitHub repo URL^>
    echo 例: scripts\git_push.bat https://github.com/你的帳號/zhe-wei-tech.git
    exit /b 1
)
git remote add origin "%~1" 2>nul
git branch -M main 2>nul
git push -u origin main
pause
