@echo off
REM ============================================
REM Aider 安裝腳本
REM 與現有 IDE 整合的 AI 程式碼助手
REM ============================================

echo ============================================
echo Aider 安裝程式
echo ============================================
echo.

REM 檢查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [錯誤] 請先安裝 Python 3.10+
    echo 下載網址: https://python.org
    pause
    exit /b 1
)

echo [1/3] 安裝 Aider...
pip install aider-chat --no-deps -q

echo [2/3] 驗證安裝...
pip show aider-chat >nul 2>&1
if errorlevel 1 (
    echo [錯誤] 安裝失敗
    pause
    exit /b 1
)

echo [3/3] 設定環境變數...
setx AIDER_MODEL "anthropic/claude-sonnet-4" >nul 2>&1

echo.
echo ============================================
echo 安裝完成！
echo ============================================
echo.
echo 使用方式:
echo   aider                    # 進入對話模式
echo   aider --file main.py     # 編輯單一檔案
echo   aider --chat-only        # 僅對話模式
echo.
echo 支援模型:
echo   - Claude (預設)
echo   - GPT-4
echo   - 本地 Ollama
echo.
echo 更多資訊:
echo   https://github.com/paul-gauthier/aider
echo.
pause
