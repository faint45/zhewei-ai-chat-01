@echo off
chcp 65001 >nul
title 設定 Cloudflare 環境變數

echo.
echo ════════════════════════════════════════════════════
echo   設定 Cloudflare 環境變數
echo ════════════════════════════════════════════════════
echo.

setx CLOUDFLARE_ZONE_ID "8ba45d8905b38792b061bdcadac6dd39" /M >nul 2>&1
setx CLOUDFLARE_API_TOKEN "JS6dXN0-fQ4efSgUbunBTBMYM83bZKPND6872Rrc" /M >nul 2>&1
setx CLOUDFLARE_DOMAIN "zhe-wei.net" /M >nul 2>&1

if %errorlevel% equ 0 (
    echo ✅ 環境變數已設定成功
    echo.
    echo 設定的變數：
    echo   • CLOUDFLARE_ZONE_ID = 8ba45d8905b38792b061bdcadac6dd39
    echo   • CLOUDFLARE_API_TOKEN = JS6dXN0-fQ4efSgUbunBTBMYM83bZKPND6872Rrc
    echo   • CLOUDFLARE_DOMAIN = zhe-wei.net
    echo.
    echo ⚠️  請重新啟動終端機或重啟電腦以使變數生效
) else (
    echo ❌ 環境變數設定失敗
    echo 請確認已以管理員權限執行
)

echo.
pause
