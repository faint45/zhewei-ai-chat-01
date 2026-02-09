@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 築未科技 — 本地執行：視覺辨識 + 報表生成
echo 本地手腳：運算（視覺辨識） + 生成（Z 槽 Reports）
echo 輸入目錄預設：D:\brain_workspace\input
echo.
python scripts\run_workflow_step.py --step 視覺與報表 --input D:\brain_workspace\input
echo.
pause
