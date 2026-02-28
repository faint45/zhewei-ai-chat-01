@echo off
chcp 65001 >nul
title 築未科技 AI 中心 — Open WebUI
color 0B

echo ═══════════════════════════════════════════════════
echo   築未科技 AI 中心 — Open WebUI 啟動器
echo   生圖(Forge) + 深度討論 + 代碼執行 + MCP
echo ═══════════════════════════════════════════════════
echo.

REM ── 檢查 Docker ──
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker 未啟動！請先啟動 Docker Desktop
    pause
    exit /b 1
)
echo [OK] Docker 運行中

REM ── 檢查 Ollama (port 11460) ──
curl -s http://localhost:11460/api/tags >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Ollama 未回應 port 11460，嘗試啟動...
    start /b "" "D:\zhe-wei-tech\ai_engines\ollama\ollama.exe" serve
    timeout /t 8 /nobreak >nul
    curl -s http://localhost:11460/api/tags >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Ollama 啟動失敗，請手動啟動
    ) else (
        echo [OK] Ollama 已啟動
    )
) else (
    echo [OK] Ollama 運行中 (port 11460)
)

REM ── 檢查 Forge (port 7860) ──
curl -s http://localhost:7860 >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Forge 未回應 port 7860
    echo           生圖功能將無法使用，請另開視窗啟動 Forge
) else (
    echo [OK] Forge 運行中 (port 7860) — 生圖功能就緒
)

echo.
echo ── 啟動 Open WebUI ──

REM ── 停止舊容器（若有） ──
docker stop open-webui >nul 2>&1
docker rm open-webui >nul 2>&1

REM ── 啟動 ──
docker compose -f "D:\zhe-wei-tech\docker-compose.openwebui.yml" up -d open-webui

if errorlevel 1 (
    echo [ERROR] Open WebUI 啟動失敗
    pause
    exit /b 1
)

echo.
echo [OK] Open WebUI 啟動中...
echo      等待服務就緒（約 30 秒）...
timeout /t 15 /nobreak >nul

REM ── 等待服務 ──
:WAIT_LOOP
curl -s http://localhost:3001 >nul 2>&1
if errorlevel 1 (
    echo.   等待中...
    timeout /t 5 /nobreak >nul
    goto WAIT_LOOP
)

echo.
echo ══════════════════════════════════════════════════
echo   ✅ Open WebUI 已就緒！
echo.
echo   🌐 網址：http://localhost:3001
echo   🤖 預設模型：zhewei-qwen3-32b-deep（深度討論）
echo   🎨 生圖：Forge 已接入（需 Forge 運行中）
echo   💻 代碼執行：Python 沙盒已啟用
echo.
echo   其他模式（在 Open WebUI 切換模型）：
echo   - zhewei-qwen3-32b-agent  → 代理模式
echo   - zhewei-brain-v5-structured → 結構化思考
echo ══════════════════════════════════════════════════
echo.

REM ── 開啟瀏覽器 ──
start "" "http://localhost:3001"

echo 按任意鍵關閉此視窗（Open WebUI 繼續在背景運行）
pause >nul
