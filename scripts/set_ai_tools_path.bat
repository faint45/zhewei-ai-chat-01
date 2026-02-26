@echo off
REM ============================================
REM AI 工具 PATH 環境設定
REM ============================================

echo ============================================
echo 設定 AI 工具 PATH
echo ============================================
echo.

REM Python Scripts 路徑
set "PYTHON_SCRIPTS=%APPDATA%\Python\Python314\Scripts"

REM 檢查路徑是否存在
if exist "%PYTHON_SCRIPTS%" (
    echo 找到 Python Scripts 目錄: %PYTHON_SCRIPTS%
    echo.
    echo 正在新增到 PATH...
    
    REM 使用 PowerShell 設定系統 PATH
    powershell -Command "[Environment]::SetEnvironmentVariable('Path', $env:Path + ';%PYTHON_SCRIPTS%', 'Machine')"
    
    if errorlevel 1 (
        echo [錯誤] 設定失敗，請以管理員身份執行此腳本
        pause
        exit /b 1
    )
    
    echo.
    echo [成功] PATH 已更新
    echo.
    echo 請重新開啟終端機以套用變更
) else (
    echo [警告] 未找到 Python Scripts 目錄
    echo 請先安裝 GPT Engineer 和 Aider
)

echo.
echo ============================================
echo 可用工具列表
echo ============================================
echo.
echo 重新開啟終端機後可使用:
echo   gpt-engineer  - 從需求生成專案
echo   aider         - 與現有 IDE 整合
echo   gemini        - Google CLI
echo   claude        - Anthropic CLI
echo.
pause
