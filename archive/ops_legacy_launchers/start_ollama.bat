@echo off
echo ========================================
echo    築未科技大腦 - Ollama 模式啟動腳本
echo ========================================

REM 設置環境變量
set AI_MODEL_TYPE=ollama
set OLLAMA_MODEL=gemma3:4b
set OLLAMA_API_BASE=http://localhost:11461/v1

echo 環境變量設置完成：
echo AI_MODEL_TYPE=%AI_MODEL_TYPE%
echo OLLAMA_MODEL=%OLLAMA_MODEL%
echo OLLAMA_API_BASE=%OLLAMA_API_BASE%

echo.
echo 檢查 Ollama 服務狀態...
ollama list

echo.
echo 啟動築未科技大腦服務...
python brain_server.py

pause