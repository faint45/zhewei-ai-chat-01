@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   Tapo C230 星空攝影 / UFO 偵測
echo ============================================
echo.
echo   1. 🛸 UFO 偵測（Web 服務）
echo   2. 🛸 UFO 偵測（本地 GUI）
echo   3. 📹 相機模式（即時預覽）
echo   4. 📸 擷取星空幀
echo   5. 🔭 進階疊圖
echo   6. 🎬 縮時/星軌影片
echo   7. ⚙️ 設定 RTSP
echo   8. 🔍 測試 RTSP 連線
echo.
set /p CHOICE="選擇（1-8）："
if "%CHOICE%"=="1" call scripts\starfield\UFO偵測_Web.bat
if "%CHOICE%"=="2" call scripts\starfield\UFO偵測.bat
if "%CHOICE%"=="3" call scripts\starfield\相機模式.bat
if "%CHOICE%"=="4" call scripts\starfield\擷取_星空幀.bat
if "%CHOICE%"=="5" call scripts\starfield\進階疊圖.bat
if "%CHOICE%"=="6" call scripts\starfield\縮時影片.bat
if "%CHOICE%"=="7" call scripts\starfield\設定RTSP.bat
if "%CHOICE%"=="8" call scripts\starfield\測試RTSP.bat
