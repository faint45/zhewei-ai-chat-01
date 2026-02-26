@echo off
REM ============================================
REM Gemini CLI 安裝腳本
REM Google 官方 CLI 工具
REM ============================================

echo ============================================
echo Gemini CLI 安裝程式
echo ============================================
echo.

REM 檢查 Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [錯誤] 請先安裝 Node.js 18+
    echo 下載網址: https://nodejs.org
    pause
    exit /b 1
)

echo [1/3] 安裝 Gemini CLI...
npm install -g @google/gemini-cli

echo [2/3] 驗證安裝...
gemini --version >nul 2>&1
if errorlevel 1 (
    echo [錯誤] 安裝失敗
    pause
    exit /b 1
)

echo [3/3] 登入 Google 帳號...
echo 執行以下指令登入:
echo   gemini login

echo.
echo ============================================
echo 安裝完成！
echo ============================================
echo.
echo 使用方式:
echo   gemini                    # 進入對話模式
echo   gemini "分析這段程式碼"   # 單次對話
echo   gemini --model pro        # 使用 Pro 模型
echo.
echo 特色:
echo   - 完全免費
echo   - 大型重構處理能力強
echo   - 原生 Google 生態整合
echo.
echo 更多資訊:
echo   https://github.com/google-gemini/gemini-cli
echo.
pause
