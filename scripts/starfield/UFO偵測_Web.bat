@echo off
chcp 65001 >nul
echo ============================================
echo   🛸 Tapo C230 UFO 偵測 — Web 服務
echo ============================================
echo.

cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo ❌ 尚未安裝，請先執行「安裝_星空攝影.bat」
    pause
    exit /b 1
)

echo 🛸 啟動 UFO 偵測 Web 服務...
echo    開啟瀏覽器：http://localhost:8035
echo    按 Ctrl+C 停止服務
echo.

call venv\Scripts\activate.bat
start "" http://localhost:8035
python ufo_web_service.py --port 8035
echo.
pause
