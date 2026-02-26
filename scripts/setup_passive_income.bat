@echo off
chcp 65001 >nul
title 築未科技 — 被動收入一鍵安裝
echo ============================================
echo   築未科技 — 被動收入安裝指南
echo   目標：每月 NT$2,650+ 被動收入
echo ============================================
echo.
echo   硬體：i7-14700 / 64GB RAM / RTX 4060 Ti / 15TB HDD
echo.
echo ┌─────────────────────────────────────────────┐
echo │  收入來源          預估月收入    狀態        │
echo │  ① GPU 算力出租    NT$1,500     待設定      │
echo │  ② 頻寬出租        NT$400       待設定      │
echo │  ③ HDD 儲存出租    NT$750       待設定      │
echo │  ─────────────────────────────────           │
echo │  合計              NT$2,650                  │
echo └─────────────────────────────────────────────┘
echo.

echo ============================================
echo   [1] GPU 算力出租 — IO.net + Salad.com
echo ============================================
echo.
echo   IO.net（推薦）:
echo     1. 前往 https://io.net 註冊
echo     2. 下載 IO Worker
echo     3. 安裝後登入，GPU 自動偵測
echo     4. RTX 4060 Ti 預估: $0.15-0.25/hr idle
echo     5. 月收入: ~$30-50 USD (NT$900-1,500)
echo.
echo   Salad.com（備選）:
echo     1. 前往 https://salad.com 註冊
echo     2. 下載 Salad App
echo     3. 啟動後自動分配 GPU 任務
echo     4. 月收入: ~$15-30 USD (NT$450-900)
echo.
echo   ⚠️ 注意：GPU 出租與本地 AI 服務會競爭 VRAM
echo   建議：閒置時出租，有客戶請求時暫停
echo.

echo ============================================
echo   [2] 頻寬出租 — Grass.io + Honeygain
echo ============================================
echo.
echo   Grass.io:
echo     1. 前往 https://app.getgrass.io 註冊
echo     2. 安裝 Chrome 擴充功能
echo     3. 保持瀏覽器開啟即可
echo     4. 月收入: ~$5-15 USD (NT$150-450)
echo.
echo   Honeygain:
echo     1. 前往 https://honeygain.com 註冊
echo     2. 下載桌面版 App
echo     3. 安裝後自動運行
echo     4. 月收入: ~$5-10 USD (NT$150-300)
echo.

echo ============================================
echo   [3] HDD 儲存出租 — Storj (10TB)
echo ============================================
echo.
echo   Storj 節點設定:
echo     1. 前往 https://storj.io/host-a-node 註冊
echo     2. 取得 Auth Token
echo     3. 執行以下 Docker 指令:
echo.
echo   docker run -d --restart unless-stopped ^
echo     --stop-timeout 300 ^
echo     -p 28967:28967/tcp -p 28967:28967/udp ^
echo     -p 14002:14002 ^
echo     -e WALLET="你的ETH錢包地址" ^
echo     -e EMAIL="你的Email" ^
echo     -e ADDRESS="你的公網IP:28967" ^
echo     -e STORAGE="10TB" ^
echo     --mount type=bind,source="D:\storj\identity",target=/app/identity ^
echo     --mount type=bind,source="D:\storj\data",target=/app/config ^
echo     --mount type=bind,source="E:\storj_storage",target=/app/storage ^
echo     --name storj-node storjlabs/storagenode:latest
echo.
echo   ⚠️ 需要:
echo     - 公網 IP 或 port forwarding (28967)
echo     - 10TB 可用空間（建議用 10TB Lenovo HDD）
echo     - 穩定網路（99.5%+ uptime）
echo     - ETH 錢包地址（收款用）
echo.
echo   預估收入:
echo     - 前 9 個月（審核期）: ~$1.5/TB/月
echo     - 審核通過後: ~$2.5/TB/月
echo     - 10TB 滿載: ~$15-25/月 (NT$450-750)
echo.

echo ============================================
echo   [4] 快速安裝指令
echo ============================================
echo.

set /p CHOICE="要安裝 Honeygain 嗎？(Y/N): "
if /i "%CHOICE%"=="Y" (
    echo 正在開啟 Honeygain 下載頁面...
    start https://honeygain.com/download
)

set /p CHOICE2="要安裝 Grass.io 嗎？(Y/N): "
if /i "%CHOICE2%"=="Y" (
    echo 正在開啟 Grass.io 註冊頁面...
    start https://app.getgrass.io/register
)

set /p CHOICE3="要設定 Storj 節點嗎？(Y/N): "
if /i "%CHOICE3%"=="Y" (
    echo 建立 Storj 目錄...
    if not exist "D:\storj\identity" mkdir "D:\storj\identity"
    if not exist "D:\storj\data" mkdir "D:\storj\data"
    echo 正在開啟 Storj 節點設定頁面...
    start https://storj.io/host-a-node
    echo.
    echo ⚠️ 請先完成以下步驟:
    echo   1. 在 Storj 網站取得 Auth Token
    echo   2. 產生 Identity（約需 4-24 小時）
    echo   3. 設定 port forwarding 28967
    echo   4. 再回來執行 Docker 指令
)

echo.
echo ============================================
echo   設定完成！請依照上方指引完成各平台註冊。
echo   所有收入會自動反映在 Asset Commander 儀表板。
echo ============================================
pause
