@echo off
chcp 65001 >nul
title 築未科技 - Phone Agent 測試
echo ========================================
echo   📱 Phone Agent 連線測試
echo ========================================
echo.

cd /d D:\zhe-wei-tech

echo [1] 檢查 ADB 是否安裝...
adb version
if %errorlevel% neq 0 (
    echo ❌ ADB 未安裝！
    echo    請下載 Android SDK Platform Tools:
    echo    https://developer.android.com/tools/releases/platform-tools
    pause
    exit /b 1
)

echo.
echo [2] 列出已連接設備...
adb devices

echo.
echo [3] 嘗試 WiFi ADB 連接（預設 192.168.1.100:5555）...
set /p PHONE_IP="輸入手機 IP（直接 Enter 用預設 192.168.1.100）: "
if "%PHONE_IP%"=="" set PHONE_IP=192.168.1.100
adb connect %PHONE_IP%:5555

echo.
echo [4] Python 模組測試...
python -c "from phone_agent import ADBController; adb=ADBController('%PHONE_IP%'); print(adb.is_connected())"

echo.
echo ========================================
echo   測試完成！
echo   API 端點（brain_server 啟動後）:
echo     GET  /api/phone/status
echo     POST /api/phone/connect
echo     POST /api/phone/task
echo     POST /api/phone/line/reply
echo     GET  /api/phone/line/read
echo ========================================
pause