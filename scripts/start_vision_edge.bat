@echo off
chcp 65001 >nul
title AI 視覺邊緣計算服務 (port 8015)
echo ============================================
echo   築未科技 - AI 視覺邊緣計算服務
echo   Port: 8015
echo ============================================

cd /d D:\zhe-wei-tech

:: 使用 Jarvis venv
set PYTHON=Jarvis_Training\.venv312\Scripts\python.exe
if not exist %PYTHON% (
    echo [ERROR] 找不到 Python: %PYTHON%
    pause
    exit /b 1
)

:: 啟動服務
%PYTHON% -m uvicorn tools.vision_edge_service:app --host 0.0.0.0 --port 8015 --reload
pause
