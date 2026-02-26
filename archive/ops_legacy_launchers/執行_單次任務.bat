@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 築未科技 — 本地執行單次任務
echo 本地手腳：單次任務（完整八階段 ReAct）
echo.
set /p TASK="請輸入任務內容（直接 Enter 使用預設「列出 D:\brain_workspace 目錄」）："
if "%TASK%"=="" set TASK=請列出 D:\brain_workspace 目錄內容
python scripts\run_workflow_step.py --step 單次任務 --task "%TASK%"
echo.
pause
