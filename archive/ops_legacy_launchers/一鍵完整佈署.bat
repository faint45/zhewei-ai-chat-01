@echo off
chcp 65001 >nul
color 0E
title 築未大腦 - 一鍵完整佈署

echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║                                                      ║
echo ║          築未科技大腦 - 一鍵完整佈署精靈             ║
echo ║                                                      ║
echo ║  此腳本將自動完成：                                  ║
echo ║    1. 環境檢查與診斷                                 ║
echo ║    2. .env 設定檢查                                  ║
echo ║    3. Docker 映像建置                                ║
echo ║    4. 容器啟動與驗證                                 ║
echo ║    5. 外網存取測試                                   ║
echo ║                                                      ║
echo ╚══════════════════════════════════════════════════════╝
echo.

REM 切換到專案目錄
cd /d "c:\Users\user\Desktop\zhe-wei-tech"
if %errorlevel% neq 0 (
    echo [X] 無法切換到專案目錄
    echo [i] 請確保專案位於 c:\Users\user\Desktop\zhe-wei-tech
    pause
    exit /b 1
)

echo [目前目錄] %cd%
echo.

echo [?] 請選擇佈署模式:
echo.
echo   1. 本機模式（僅本機存取 http://localhost:8000）
echo   2. Docker 模式（本機 + 外網 https://brain.zhe-wei.net）
echo   3. 僅診斷（不佈署）
echo.
set /p mode="請輸入選項 (1-3): "
echo.

if "%mode%"=="3" goto diagnostics_only
if "%mode%"=="1" goto local_mode
if "%mode%"=="2" goto docker_mode
echo [X] 無效選擇
pause
exit /b 1

:diagnostics_only
echo ═══════════════════════════════════════
echo  執行診斷檢查...
echo ═══════════════════════════════════════
if exist scripts\super_diagnostics.py (
    python scripts\super_diagnostics.py
) else if exist startup_diagnostics.py (
    python startup_diagnostics.py
) else (
    echo [!] 診斷腳本不存在，跳過診斷
)
pause
exit /b 0

:local_mode
echo ═══════════════════════════════════════
echo  本機模式佈署
echo ═══════════════════════════════════════
echo.

echo [1/4] 檢查 Python 環境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] 未找到 Python，請先安裝 Python 3.10+
    pause
    exit /b 1
)
echo [+] Python 環境正常
echo.

echo [2/4] 檢查依賴套件...
pip show fastapi >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] 缺少依賴，正在安裝...
    if exist requirements-brain.txt (
        pip install -r requirements-brain.txt
    ) else (
        echo [!] requirements-brain.txt 不存在，跳過依賴安裝
    )
)
echo [+] 依賴檢查完成
echo.

echo [3/4] 檢查關鍵檔案...
if not exist brain_server.py (
    echo [X] brain_server.py 不存在！
    echo [i] 請確保在正確的專案目錄
    pause
    exit /b 1
)
echo [+] 關鍵檔案存在
echo.

echo [4/4] 啟動 Brain Server...
echo [i] 服務將運行於 http://localhost:8000
echo [i] 管理介面: http://localhost:8000/static/index.html
echo [i] 按 Ctrl+C 可停止服務
echo.
timeout /t 3 >nul

python brain_server.py
pause
exit /b 0

:docker_mode
echo ═══════════════════════════════════════
echo  Docker 完整佈署
echo ═══════════════════════════════════════
echo.

REM 步驟 1: 檢查 Docker
echo [1/7] 檢查 Docker 環境...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] Docker 未安裝
    echo [i] 請至 https://www.docker.com/products/docker-desktop 安裝
    pause
    exit /b 1
)
echo [+] Docker 已安裝
echo.

REM 步驟 2: 檢查 .env
echo [2/7] 檢查 .env 檔案...
if not exist ".env" (
    echo [!] .env 不存在
    if exist ".env.example" (
        echo [i] 正在從 .env.example 建立 .env...
        copy .env.example .env
    ) else (
        echo [i] 正在建立基礎 .env 檔案...
        (
            echo # Cloudflare Tunnel Token
            echo CLOUDFLARE_TOKEN=
            echo.
            echo # Gemini API Key (可選^)
            echo GEMINI_API_KEY=
        ) > .env
    )
    echo.
    echo [!] 請編輯 .env 檔案，設定 CLOUDFLARE_TOKEN
    echo.
    echo 如何取得 Token:
    echo   1. 開啟 https://one.dash.cloudflare.com
    echo   2. Zero Trust ^> Networks ^> Tunnels ^> 你的隧道
    echo   3. 複製 Token (格式: eyJ...^)
    echo   4. 貼到 .env 的 CLOUDFLARE_TOKEN= 後面
    echo.
    notepad .env
    echo.
    echo [?] Token 已設定完成? (Y/N^)
    set /p token_ready=
    if /i not "%token_ready%"=="Y" (
        echo [!] 佈署取消
        pause
        exit /b 1
    )
)

REM 驗證 Token
findstr /C:"CLOUDFLARE_TOKEN=eyJ" .env >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] 未偵測到有效的 CLOUDFLARE_TOKEN
    echo [!] Token 應以 eyJ 開頭
    notepad .env
    echo.
    echo [?] Token 已修正? (Y/N^)
    set /p token_fixed=
    if /i not "%token_fixed%"=="Y" (
        echo [!] 佈署取消
        pause
        exit /b 1
    )
)
echo [+] .env 設定正確
echo.

REM 步驟 3: 停止舊容器
echo [3/7] 清理舊容器...
docker compose down 2>nul
echo [+] 清理完成
echo.

REM 步驟 4: 建置映像
echo [4/7] 建置 Docker 映像...
echo [i] 可能需要數分鐘，請稍候...
docker compose build --no-cache
if %errorlevel% neq 0 (
    echo [X] 建置失敗
    echo [i] 請檢查 Dockerfile 與網路連線
    pause
    exit /b 1
)
echo [+] 映像建置成功
echo.

REM 步驟 5: 啟動容器
echo [5/7] 啟動容器...
docker compose up -d
if %errorlevel% neq 0 (
    echo [X] 啟動失敗
    echo [i] 查看詳細日誌: docker compose logs
    pause
    exit /b 1
)
echo [+] 容器已啟動
echo.

REM 步驟 6: 等待服務就緒
echo [6/7] 等待服務啟動 (15 秒^)...
timeout /t 15 >nul
echo [+] 等待完成
echo.

REM 步驟 7: 驗證佈署
echo [7/7] 驗證佈署...
echo.

echo [測試 1/4] 檢查容器狀態...
docker compose ps
echo.

echo [測試 2/4] 本機健康檢查...
curl -f http://localhost:8000/health >nul 2>&1
if %errorlevel%==0 (
    echo [+] 本機存取正常
) else (
    echo [X] 本機存取失敗
    echo [i] 查看日誌: docker compose logs brain_server
    pause
    exit /b 1
)
echo.

echo [測試 3/4] 外網健康檢查...
curl -f https://brain.zhe-wei.net/health >nul 2>&1
if %errorlevel%==0 (
    echo [+] 外網存取正常
) else (
    echo [!] 外網存取失敗
    echo [i] 可能原因:
    echo     - DNS 尚在傳播 (等待 5-10 分鐘^)
    echo     - Token 設定錯誤
    echo     - Tunnel 未連線
    echo.
    echo [i] 檢查 tunnel 日誌:
    docker compose logs tunnel 2>nul | findstr /C:"registered" /C:"error"
)
echo.

echo [測試 4/4] 靜態檔案檢查...
curl -f http://localhost:8000/static/index.html >nul 2>&1
if %errorlevel%==0 (
    echo [+] 靜態檔案正常
) else (
    echo [!] 靜態檔案存取失敗
)
echo.

echo ╔══════════════════════════════════════════════════════╗
echo ║                  佈署完成！                          ║
echo ╠══════════════════════════════════════════════════════╣
echo ║                                                      ║
echo ║  存取位址：                                          ║
echo ║    本機: http://localhost:8000                       ║
echo ║    管理介面: http://localhost:8000/static/index.html ║
echo ║    外網: https://brain.zhe-wei.net                   ║
echo ║                                                      ║
echo ║  常用指令：                                          ║
echo ║    查看日誌: docker compose logs -f                  ║
echo ║    停止服務: docker compose down                     ║
echo ║    重啟服務: docker compose restart                  ║
echo ║    查看狀態: docker compose ps                       ║
echo ║                                                      ║
echo ╚══════════════════════════════════════════════════════╝
echo.

echo [?] 是否立即在瀏覽器中開啟管理介面? (Y/N^)
set /p open_browser=
if /i "%open_browser%"=="Y" (
    start http://localhost:8000/static/index.html
    echo.
    echo [i] 如需存取外網版本，請稍等約 5 分鐘後開啟:
    echo     https://brain.zhe-wei.net
)

pause
