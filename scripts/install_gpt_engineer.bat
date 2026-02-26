@echo off
REM ============================================
REM GPT Engineer 安裝腳本
REM 完全免費的 AI 程式碼生成工具
REM ============================================

echo ============================================
echo GPT Engineer 安裝程式
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

echo [1/3] 安裝 GPT Engineer...
pip install gpt-engineer -q

echo [2/3] 驗證安裝...
pip show gpt-engineer >nul 2>&1
if errorlevel 1 (
    echo [錯誤] 安裝失敗
    pause
    exit /b 1
)

echo [3/3] 設定環境變數...
setx GPT_ENGINEER_MODEL "gpt-4" >nul 2>&1

echo.
echo ============================================
echo 安裝完成！
echo ============================================
echo.
echo 使用方式:
echo   gpt-engineer "建立一個 Python 計算機"
echo.
echo 更多資訊:
echo   https://github.com/gpt-engineer-org/gpt-engineer
echo.
pause
