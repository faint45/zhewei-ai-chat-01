@echo off
REM ============================================
REM iFlow CLI 安裝腳本
REM 多模型 AI CLI 工具
REM 注意：需要 Rust 環境
REM ============================================

echo ============================================
echo iFlow CLI 安裝程式
echo ============================================
echo.

REM 檢查 Rust
rustc --version >nul 2>&1
if errorlevel 1 (
    echo [1/4] 未檢測到 Rust，正在安裝...
    echo 請選擇 [1] Proceed with installation (default)
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable
    echo.
    echo [重要] 請關閉此終端機並重新開啟，然後再次執行此腳本
    echo.
    pause
    exit /b 0
)

echo [2/4] 安裝 iFlow CLI...
echo 這可能需要幾分鐘時間...
cargo install iflow-cli

echo [3/4] 驗證安裝...
iflow --version >nul 2>&1
if errorlevel 1 (
    echo [錯誤] 安裝失敗
    pause
    exit /b 1
)

echo [4/4] 設定環境變數...
setx ILOW_DEFAULT_MODEL "deepseek-chat" >nul 2>&1

echo.
echo ============================================
echo 安裝完成！
echo ============================================
echo.
echo 使用方式:
echo   iflow login                    # 登入
echo   iflow analyze                  # 分析專案
echo   iflow task "優化程式碼"        # 執行任務
echo.
echo 支援模型:
echo   - Kimi K2
echo   - Qwen3 Coder
echo   - DeepSeek v3
echo   - 完全免費
echo.
echo 更多資訊:
echo   https://github.com/iflow-ai/iflow-cli
echo.
pause
