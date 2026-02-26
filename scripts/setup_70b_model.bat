@echo off
chcp 65001 >nul
title 築未科技 — 70B 大模型下載
echo ============================================
echo   築未科技 — Qwen3 70B 大模型下載
echo   需要約 40GB 磁碟空間 + 64GB RAM
echo   下載時間約 1-3 小時（視網速）
echo ============================================
echo.

:: 檢查 Ollama
where ollama >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Ollama 未安裝！請先安裝 Ollama: https://ollama.com
    pause
    exit /b 1
)

:: 檢查記憶體
echo [INFO] 檢查系統記憶體...
for /f "tokens=2 delims==" %%a in ('wmic computersystem get TotalPhysicalMemory /value 2^>nul') do set RAM=%%a
echo [INFO] 系統記憶體: %RAM% bytes

echo.
echo [STEP 1/3] 下載 Qwen3 70B 模型（約 40GB）...
echo 這會使用 CPU offload（GPU 8GB + RAM 剩餘部分）
echo.
ollama pull qwen3:70b
if %errorlevel% neq 0 (
    echo [ERROR] 下載失敗！請檢查網路連線和磁碟空間。
    pause
    exit /b 1
)

echo.
echo [STEP 2/3] 驗證模型可用性...
ollama list | findstr "qwen3:70b"
if %errorlevel% neq 0 (
    echo [ERROR] 模型未出現在列表中！
    pause
    exit /b 1
)

echo.
echo [STEP 3/3] 快速測試推理...
echo 測試中（首次載入約 30-60 秒）...
ollama run qwen3:70b "用一句話介紹台灣" --verbose 2>&1
echo.

echo ============================================
echo   ✅ Qwen3 70B 安裝完成！
echo   速度：約 4-6 tok/s（CPU offload）
echo   用途：大模型 API 商務版專屬
echo ============================================
pause
