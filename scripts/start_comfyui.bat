@echo off
echo === 啟動 ComfyUI 本地生圖服務 ===
cd /d D:\zhe-wei-tech\ComfyUI
call venv\Scripts\activate.bat
python main.py --listen 127.0.0.1 --port 9188 --preview-method auto
pause
