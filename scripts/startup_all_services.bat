@echo off
chcp 65001 >nul
echo ============================================================
echo   築未科技 — 全服務自動啟動
echo   %date% %time%
echo ============================================================

REM 等待網路就緒
timeout /t 15 /nobreak >nul

REM 1. 啟動 Docker Compose（包含 Gateway, Brain, Portal, Bridge, CMS, CodeSim, Tunnel）
echo [1/3] 啟動 Docker Compose...
cd /d "D:\zhe-wei-tech"
docker compose up -d
echo      Docker 服務已啟動

REM 等待 Docker 容器就緒
timeout /t 10 /nobreak >nul

REM 2. 啟動 AI 視覺辨識（本地 GPU 服務，不在 Docker 中）
echo [2/3] 啟動 AI 視覺辨識系統 (port 8030)...
start "Vision-AI" /min cmd /c "cd /d D:\AI_Vision_Recognition && D:\zhe-wei-tech\Jarvis_Training\.venv312\Scripts\python.exe web_server.py"
echo      Vision 服務已啟動

REM 3. 啟動 Ollama（如果未運行）
echo [3/3] 檢查 Ollama...
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I "ollama.exe" >NUL
if errorlevel 1 (
    echo      啟動 Ollama...
    start "" /min "C:\Users\%USERNAME%\AppData\Local\Programs\Ollama\ollama.exe" serve
) else (
    echo      Ollama 已在運行
)

echo.
echo ============================================================
echo   所有服務已啟動完成！
echo   Portal:   https://zhe-wei.net
echo   Jarvis:   https://jarvis.zhe-wei.net
echo   Bridge:   https://bridge.zhe-wei.net
echo   Dify:     https://dify.zhe-wei.net
echo   CMS:      https://cms.zhe-wei.net
echo   Vision:   https://vision.zhe-wei.net
echo   CodeSim:  https://codesim.zhe-wei.net
echo ============================================================
