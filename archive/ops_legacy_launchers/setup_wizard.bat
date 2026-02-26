@echo off
REM ================================================================
REM 築未科技大腦 - 首次安裝配置向導
REM ================================================================
chcp 65001 >nul
setlocal enabledelayedexpansion

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║          築未科技 AI 大腦系統 - 配置向導                  ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM 檢查 .env 文件
if exist ".env" (
    echo [檢查] 已找到 .env 配置文件
    echo.
    choice /c YN /m "是否要重新配置？(Y=是, N=否)"
    if errorlevel 2 goto :skip_config
    if errorlevel 1 goto :config
) else (
    echo [提示] 未找到 .env 配置文件，開始配置...
    goto :config
)

:config
echo.
echo ────────────────────────────────────────────────────────────
echo  步驟 1/4: 基礎配置
echo ────────────────────────────────────────────────────────────
echo.

REM 複製範例文件
if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo [✓] 已創建 .env 配置文件
)

echo 請選擇 AI 服務配置模式：
echo.
echo [1] 完全免費模式 (使用 Ollama 本地 AI)
echo [2] 高性能模式 (使用 Google Gemini - 免費額度)
echo [3] 專業模式 (多 AI 混合 - 需要 API 金鑰)
echo.
set /p ai_mode="請選擇 (1-3): "

echo.
echo ────────────────────────────────────────────────────────────
echo  步驟 2/4: AI 服務配置
echo ────────────────────────────────────────────────────────────
echo.

if "%ai_mode%"=="1" (
    echo [模式] 完全免費 - 使用 Ollama
    echo AI_COST_MODE=local_only >> .env
    echo.
    echo [提示] 需要安裝 Ollama: https://ollama.ai/
    echo 安裝後執行: ollama pull qwen2.5:7b
    pause
)

if "%ai_mode%"=="2" (
    echo [模式] 高性能 - Google Gemini
    echo.
    set /p gemini_key="請輸入 Gemini API Key (從 https://aistudio.google.com/app/apikey 獲取): "
    echo GEMINI_API_KEY=!gemini_key! >> .env
    echo GEMINI_MODEL=gemini-1.5-flash >> .env
    echo AI_COST_MODE=free_only >> .env
)

if "%ai_mode%"=="3" (
    echo [模式] 專業 - 多 AI 混合
    echo AI_COST_MODE=all >> .env
    echo AI_USE_ENSEMBLE=1 >> .env
    echo.
    echo 請依次輸入您擁有的 API Keys (直接按 Enter 跳過):
    echo.

    set /p gemini_key="Gemini API Key: "
    if not "!gemini_key!"=="" echo GEMINI_API_KEY=!gemini_key! >> .env

    set /p anthropic_key="Anthropic Claude API Key: "
    if not "!anthropic_key!"=="" echo ANTHROPIC_API_KEY=!anthropic_key! >> .env

    set /p groq_key="Groq API Key: "
    if not "!groq_key!"=="" echo GROQ_API_KEY=!groq_key! >> .env
)

echo.
echo ────────────────────────────────────────────────────────────
echo  步驟 3/4: 管理員帳號設置
echo ────────────────────────────────────────────────────────────
echo.

set /p admin_user="設置管理員帳號 (預設: admin): "
if "!admin_user!"=="" set admin_user=admin

set /p admin_pwd="設置管理員密碼: "
if "!admin_pwd!"=="" set admin_pwd=admin123

echo ADMIN_USER=!admin_user! >> .env
echo ADMIN_PASSWORD=!admin_pwd! >> .env

echo.
echo ────────────────────────────────────────────────────────────
echo  步驟 4/4: 資料儲存位置
echo ────────────────────────────────────────────────────────────
echo.

set /p brain_data="大腦資料目錄 (預設: D:\brain_workspace): "
if "!brain_data!"=="" set brain_data=D:\brain_workspace

echo BRAIN_WORKSPACE=!brain_data! >> .env

REM 創建資料目錄
if not exist "!brain_data!" (
    mkdir "!brain_data!"
    mkdir "!brain_data!\static"
    echo [✓] 已創建資料目錄
)

REM 複製靜態文件
if exist "brain_workspace\static" (
    xcopy /s /y "brain_workspace\static\*.*" "!brain_data!\static\" >nul
    echo [✓] 已複製靜態資源
)

:skip_config

echo.
echo ════════════════════════════════════════════════════════════
echo  配置完成！
echo ════════════════════════════════════════════════════════════
echo.
echo 配置文件: .env
echo 資料目錄: !brain_data!
echo 管理帳號: !admin_user!
echo.
echo 下一步：
echo 1. 執行「啟動大腦.bat」啟動系統
echo 2. 瀏覽器訪問 http://localhost:8002
echo 3. 使用管理員帳號登入
echo.

choice /c YN /m "是否現在啟動大腦系統？"
if errorlevel 2 goto :end
if errorlevel 1 (
    echo.
    echo 正在啟動...
    if exist "ZheweiTechBrain.exe" (
        start ZheweiTechBrain.exe
    ) else if exist "brain_server.py" (
        python brain_server.py
    ) else (
        echo [錯誤] 未找到執行文件
    )
)

:end
echo.
pause
