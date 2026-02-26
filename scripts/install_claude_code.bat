@echo off
REM ============================================
REM Claude Code 安裝腳本
REM Anthropic 官方 CLI 工具
REM ============================================

echo ============================================
echo Claude Code 安裝程式
echo ============================================
echo.

REM 檢查 Homebrew
brew --version >nul 2>&1
if not errorlevel 1 (
    echo [1/3] 使用 Homebrew 安裝...
    brew install anthropic-ai/claude-code/claude-code
    goto verify
)

REM 檢查 curl
curl --version >nul 2>&1
if errorlevel 1 (
    echo [錯誤] 請安裝 curl
    pause
    exit /b 1
)

echo [1/3] 下載安裝腳本...
curl -s https://raw.githubusercontent.com/anthropics/claude-code/main/install.sh -o %TEMP%\install_claude.sh

echo [2/3] 執行安裝...
if exist %TEMP%\install_claude.sh (
    bash %TEMP%\install_claude.sh
    del %TEMP%\install_claude.sh
) else (
    echo [錯誤] 下載失敗
    pause
    exit /b 1
)

:verify
echo [3/3] 驗證安裝...
claude --version >nul 2>&1
if errorlevel 1 (
    echo [警告] 安裝可能未完成，請手動執行:
    echo   claude login
) else (
    echo.
    echo ============================================
    echo 安裝完成！
    echo ============================================
)

echo.
echo 使用方式:
echo   claude                    # 進入對話模式
echo   claude "分析程式碼"        # 單次對話
echo   claude --model sonnet-4   # 使用 Sonnet 4
echo.
echo 特色:
echo   - 原生 GitHub 整合
echo   - MCP 工具支援
echo   - Claude Sonnet 4.5 模型
echo.
echo 需要 Claude Pro ($20/月) 才能使用 API
echo.
echo 更多資訊:
echo   https://github.com/anthropics/claude-code
echo.
pause
