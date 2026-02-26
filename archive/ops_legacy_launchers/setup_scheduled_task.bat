@echo off
chcp 65001 >nul
cls
echo ================================================
echo     築未科技官方網站 - 自動化計劃任務配置
echo ================================================
echo.

echo 📅 配置DuckDNS自動更新計劃任務...
echo.

REM 檢查是否為管理員權限
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ⚠️  請以管理員身份運行此腳本！
    echo.
    echo 📋 操作方法：
    echo     1. 右鍵點擊此文件
    echo     2. 選擇"以管理員身份運行"
    echo.
    pause
    exit /b 1
)

echo ✅ 檢測到管理員權限
echo.

echo 🔧 創建DuckDNS自動更新任務...

REM 獲取當前目錄路徑
set "SCRIPT_PATH=%~dp0duckdns_update.bat"

REM 刪除現有任務（如果存在）
schtasks /delete /tn "築未科技DuckDNS更新" /f 2>nul

echo.
echo 📋 創建新的計劃任務：
echo     任務名稱: 築未科技DuckDNS更新
echo     執行頻率: 每10分鐘
echo     執行動作: 更新外部IP地址
echo.

REM 創建計劃任務
schtasks /create /tn "築未科技DuckDNS更新" ^
    /tr "%SCRIPT_PATH%" ^
    /sc minute /mo 10 ^
    /ru "SYSTEM" ^
    /rl HIGHEST ^
    /f

if %errorlevel% equ 0 (
    echo ✅ 計劃任務創建成功！
    echo.
    echo 🔧 任務配置詳情：
    schtasks /query /tn "築未科技DuckDNS更新" /fo list
    echo.
    echo 📅 運行計劃：
    echo     • 系統啟動時自動運行
    echo     • 每10分鐘檢查更新
    echo     • 無需用戶登錄
    echo.
    echo 🌐 測試任務執行：
    schtasks /run /tn "築未科技DuckDNS更新"
    echo.
    echo 💡 任務將在後台自動運行，確保域名始終指向正確IP
) else (
    echo ❌ 計劃任務創建失敗
    echo.
    echo 🔧 手動配置方法：
    echo     1. 打開"任務計劃程序"
    echo     2. 創建基本任務
    echo     3. 名稱: 築未科技DuckDNS更新
    echo     4. 觸發器: 每10分鐘
    echo     5. 操作: 啟動程序 → %SCRIPT_PATH%
)

echo.
echo ================================================
pause