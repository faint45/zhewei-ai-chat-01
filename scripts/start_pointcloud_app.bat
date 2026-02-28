@echo off
chcp 65001 >nul
title 築未科技 — 點雲斷面分析系統 v2.0

echo ================================================
echo   築未科技 — 點雲斷面分析系統
echo   本地運算，本地模型，0 雲端消耗
echo ================================================
echo.

cd /d D:\zhe-wei-tech

REM 確認 Ollama 是否運行
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Ollama 未偵測到，嘗試啟動...
    start "" ollama serve
    timeout /t 3 /nobreak >nul
)

echo [INFO] 啟動點雲斷面分析 GUI...
python -m construction_brain.pointcloud.gui_app

pause
