@echo off
echo === 啟動 Jarvis Host API (port 8010) ===
cd /d D:\zhe-wei-tech
call Jarvis_Training\.venv312\Scripts\activate.bat
python scripts\host_api.py
pause
