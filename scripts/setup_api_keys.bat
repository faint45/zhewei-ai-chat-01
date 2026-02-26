@echo off
REM ============================================
REM 築未科技 AI 系統 API Key 設定腳本
REM ============================================
REM 請填入以下 API Key 後執行此腳本

echo === 築未科技 API Key 設定 ===
echo.
echo 請依序輸入以下 API Key（如已設定可直接跳過）：
echo.

set /p DEEPSEEK_KEY="DeepSeek API Key (https://platform.deepseek.com): "
set /p MINIMAX_KEY="MiniMax API Key (https://platform.minimax.io): "
set /p GEMINI_KEY="Gemini API Key (https://aistudio.google.com): "
set /p ANTHROPIC_KEY="Anthropic API Key (https://console.anthropic.com): "

echo.
echo === 寫入環境變數... ===

setx DEEPSEEK_API_KEY "%DEEPSEEK_KEY%" /M
setx MINIMAX_API_KEY "%MINIMAX_KEY%" /M
setx GEMINI_API_KEY "%GEMINI_KEY%" /M
setx ANTHROPIC_API_KEY "%ANTHROPIC_KEY%" /M

echo.
echo === 完成！ ===
echo 請重新啟動 Brain Server 使設定生效。
echo.
pause
