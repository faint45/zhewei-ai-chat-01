@echo off
REM ================================================================
REM 築未科技大腦 - 軟件打包腳本
REM ================================================================
chcp 65001 >nul
setlocal enabledelayedexpansion

echo.
echo ================================================================
echo  築未科技 AI 大腦系統 - 打包程序
echo ================================================================
echo.

REM 檢查 Python 環境
python --version >nul 2>&1
if errorlevel 1 (
    echo [錯誤] 未找到 Python，請先安裝 Python 3.8+
    pause
    exit /b 1
)

REM 檢查並安裝 PyInstaller
echo [1/5] 檢查 PyInstaller...
python -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo 正在安裝 PyInstaller...
    python -m pip install pyinstaller --user
) else (
    echo PyInstaller 已安裝
)

REM 安裝依賴
echo.
echo [2/5] 安裝依賴套件...
python -m pip install -r requirements-brain.txt --user

REM 清理舊的構建文件
echo.
echo [3/5] 清理舊構建...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

REM 執行打包
echo.
echo [4/5] 打包應用程序...
echo 這可能需要幾分鐘時間，請耐心等待...
python -m PyInstaller brain_server.spec

if errorlevel 1 (
    echo.
    echo [錯誤] 打包失敗！
    echo 請檢查上方錯誤信息
    pause
    exit /b 1
)

REM 複製額外文件
echo.
echo [5/5] 複製配置文件...
if exist "dist\ZheweiTechBrain" (
    copy /y ".env.example" "dist\ZheweiTechBrain\"
    copy /y "README_軟件使用說明.md" "dist\ZheweiTechBrain\" 2>nul

    REM 創建啟動腳本
    echo @echo off > "dist\ZheweiTechBrain\啟動大腦.bat"
    echo chcp 65001 ^>nul >> "dist\ZheweiTechBrain\啟動大腦.bat"
    echo echo 正在啟動築未科技 AI 大腦... >> "dist\ZheweiTechBrain\啟動大腦.bat"
    echo ZheweiTechBrain.exe >> "dist\ZheweiTechBrain\啟動大腦.bat"
    echo pause >> "dist\ZheweiTechBrain\啟動大腦.bat"
)

echo.
echo ================================================================
echo  打包完成！
echo ================================================================
echo.
echo 軟件位置: dist\ZheweiTechBrain\
echo 執行文件: ZheweiTechBrain.exe
echo 啟動腳本: 啟動大腦.bat
echo.
echo 下一步：
echo 1. 將 .env.example 複製為 .env 並填入 API 金鑰
echo 2. 雙擊「啟動大腦.bat」啟動系統
echo 3. 瀏覽器訪問 http://localhost:8002
echo.
pause
