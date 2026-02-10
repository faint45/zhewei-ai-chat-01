@echo off
chcp 65001 >nul
echo ========================================
echo    築未科技七階段指揮作戰系統
echo    Seven-Stage Command Operations
echo ========================================

echo.
echo 系統架構：
echo [1] 總指揮官 (Commander)   - Gemini Pro
echo [2] 首席開發官 (Lead Dev)   - Claude Pro
echo [3] 實體執行員 (Executor)   - Cursor Pro / Windsurf
echo [4] 地端勤務兵 (Local Guard) - Ollama (Qwen)
echo [5] 情報與驗證 (Verify)     - 千問 / 元寶 / CodeBuddy
echo [6] 基礎設施 (Platform)     - Docker
echo.

echo 正在初始化系統...
python seven_stage_system.py

echo.
echo ========================================
pause
