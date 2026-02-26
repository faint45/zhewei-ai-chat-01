@echo off
REM ================================================================
REM 築未科技大腦 - 簡化打包腳本（除錯版）
REM ================================================================
chcp 65001 >nul
setlocal enabledelayedexpansion

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║     築未科技 AI 大腦系統 - 簡化打包程序                   ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM 步驟 1: 檢查環境
echo [1/4] 檢查環境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [錯誤] 未找到 Python
    pause
    exit /b 1
)
echo [✓] Python 已安裝

python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo [安裝] PyInstaller...
    python -m pip install pyinstaller --user
)
echo [✓] PyInstaller 已就緒

REM 步驟 2: 清理
echo.
echo [2/4] 清理舊構建...
if exist "build" (
    echo 刪除 build 目錄...
    rmdir /s /q "build"
)
if exist "dist" (
    echo 刪除 dist 目錄...
    rmdir /s /q "dist"
)
echo [✓] 清理完成

REM 步驟 3: 打包
echo.
echo [3/4] 開始打包（這可能需要 3-5 分鐘）...
echo.
python -m PyInstaller ^
    --name=ZheweiTechBrain ^
    --onedir ^
    --console ^
    --noconfirm ^
    --add-data="brain_workspace/static;brain_workspace/static" ^
    --add-data=".env.example;." ^
    --hidden-import=uvicorn.logging ^
    --hidden-import=uvicorn.loops ^
    --hidden-import=uvicorn.loops.auto ^
    --hidden-import=uvicorn.protocols ^
    --hidden-import=uvicorn.protocols.http ^
    --hidden-import=uvicorn.protocols.http.auto ^
    --hidden-import=uvicorn.protocols.websockets ^
    --hidden-import=uvicorn.protocols.websockets.auto ^
    --hidden-import=uvicorn.lifespan ^
    --hidden-import=uvicorn.lifespan.on ^
    --hidden-import=fastapi ^
    --hidden-import=google.generativeai ^
    --hidden-import=anthropic ^
    --hidden-import=ai_service ^
    --hidden-import=agent_logic ^
    --hidden-import=agent_tools ^
    brain_server.py

if errorlevel 1 (
    echo.
    echo [錯誤] 打包失敗！
    echo 請查看上方錯誤信息
    pause
    exit /b 1
)

echo.
echo [✓] 打包完成

REM 步驟 4: 後處理
echo.
echo [4/4] 複製額外文件...
if exist "dist\ZheweiTechBrain" (
    copy /y ".env.example" "dist\ZheweiTechBrain\" >nul 2>&1
    copy /y "README_軟件使用說明.md" "dist\ZheweiTechBrain\" >nul 2>&1

    REM 創建啟動腳本
    (
        echo @echo off
        echo chcp 65001 ^>nul
        echo echo 正在啟動築未科技 AI 大腦系統...
        echo echo.
        echo echo 端口: 8002
        echo echo 管理介面: http://localhost:8002/admin
        echo echo 對話介面: http://localhost:8002/chat
        echo echo.
        echo ZheweiTechBrain.exe
        echo if errorlevel 1 pause
    ) > "dist\ZheweiTechBrain\啟動大腦.bat"

    echo [✓] 後處理完成
) else (
    echo [警告] 未找到輸出目錄
)

echo.
echo ════════════════════════════════════════════════════════════
echo  🎉 打包成功！
echo ════════════════════════════════════════════════════════════
echo.
echo 輸出位置: dist\ZheweiTechBrain\
echo.
echo 檔案列表:
dir /b "dist\ZheweiTechBrain" 2>nul | findstr /v "_internal"
echo _internal\ (依賴文件)
echo.
echo 下一步:
echo 1. 測試執行: cd dist\ZheweiTechBrain ^&^& 啟動大腦.bat
echo 2. 配置系統: 複製 .env.example 為 .env 並填入 API 金鑰
echo 3. 壓縮分發: 使用 7-Zip 壓縮整個資料夾
echo.
pause
