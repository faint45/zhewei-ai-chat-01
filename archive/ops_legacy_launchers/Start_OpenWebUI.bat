@echo off
echo Starting Open WebUI...
cd /d "c:\Users\user\Desktop\zhe-wei-tech"
docker compose -f docker-compose.openwebui.yml up -d
echo.
echo Open WebUI: http://localhost:3000
echo.
pause
