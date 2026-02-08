@echo off
echo ========================================
echo    啟動 Ollama 服務 (端口 11461)
echo ========================================

echo 正在設置環境變量...
set OLLAMA_HOST=0.0.0.0:11461

echo 正在啟動 Ollama 服務...
echo [提示] 請保持此窗口打開，不要關閉
echo.
ollama serve

pause
