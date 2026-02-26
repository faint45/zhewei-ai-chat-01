@echo off
chcp 65001 >nul
echo ═══════════════════════════════════════════════════
echo   築未科技 — 雙 GPU AI 分工設定
echo   RTX 5070 Ti (16GB) → LLM 推理 (Ollama)
echo   RTX 4060 Ti (8GB)  → 生圖/影片 (Forge/ComfyUI)
echo ═══════════════════════════════════════════════════
echo.

REM ── 偵測 GPU ──
echo [1/5] 偵測 GPU...
nvidia-smi --query-gpu=index,name,memory.total --format=csv,noheader,nounits
echo.

REM ── 設定 Ollama 環境變數 ──
echo [2/5] 設定 Ollama 環境變數...

REM 預設 GPU 0 = 5070 Ti（VRAM 較大者）
REM 如果 GPU 順序相反，請手動調整 CUDA_VISIBLE_DEVICES
set OLLAMA_HOST=0.0.0.0:11460
set OLLAMA_FLASH_ATTENTION=1
set OLLAMA_NUM_PARALLEL=2
set OLLAMA_MAX_LOADED_MODELS=3
set OLLAMA_KEEP_ALIVE=30m

echo   OLLAMA_HOST=%OLLAMA_HOST%
echo   OLLAMA_FLASH_ATTENTION=%OLLAMA_FLASH_ATTENTION%
echo   OLLAMA_NUM_PARALLEL=%OLLAMA_NUM_PARALLEL%
echo   OLLAMA_MAX_LOADED_MODELS=%OLLAMA_MAX_LOADED_MODELS%
echo   OLLAMA_KEEP_ALIVE=%OLLAMA_KEEP_ALIVE%
echo.

REM ── 確認模型 ──
echo [3/5] 確認已安裝的模型...
ollama list
echo.

REM ── 確認 qwen3:32b 可用 ──
echo [4/5] 測試 qwen3:32b 推理...
echo 你好 | ollama run qwen3:32b --nowordwrap 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ⚠️ qwen3:32b 尚未安裝，正在拉取...
    ollama pull qwen3:32b
)
echo.

REM ── 顯示最終狀態 ──
echo [5/5] 雙 GPU 設定完成！
echo.
echo ┌─────────────────────────────────────────────┐
echo │  GPU 0 (5070 Ti 16GB) → Ollama LLM 推理      │
echo │    • qwen3:32b (軍師, ~14GB VRAM)             │
echo │    • qwen3:8b  (士兵, ~5GB VRAM)              │
echo │    • nomic-embed-text (Embedding)             │
echo │                                               │
echo │  GPU 1 (4060 Ti 8GB) → 生圖/影片              │
echo │    • Forge SDXL (--device-id 1)               │
echo │    • ComfyUI (--cuda-device 1)                │
echo │    • LivePortrait                             │
echo └─────────────────────────────────────────────┘
echo.
echo 提示：
echo   Forge 啟動加參數: --device-id 1
echo   ComfyUI 啟動加參數: --cuda-device 1
echo.
pause
