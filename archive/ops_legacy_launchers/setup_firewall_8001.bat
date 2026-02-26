@echo off
chcp 65001 >nul
title 設定防火牆 - 允許埠 8001

echo.
echo ════════════════════════════════════════════════════
echo   設定 Windows 防火牆 - 允許埠 8001
echo ════════════════════════════════════════════════════
echo.

:: 檢查是否以管理員權限運行
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 需要管理員權限
    echo.
    echo 請右鍵此文件，選擇「以管理員身分執行」
    echo.
    pause
    exit /b 1
)

echo [1/3] 刪除舊規則（如果存在）...
netsh advfirewall firewall delete rule name="Allow Port 8001" >nul 2>&1
echo ✅ 舊規則已清理
echo.

echo [2/3] 新增入站規則...
netsh advfirewall firewall add rule name="Allow Port 8001" dir=in action=allow protocol=TCP localport=8001 >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ 入站規則已建立（允許從外部連接到本機埠 8001）
) else (
    echo ❌ 入站規則建立失敗
    pause
    exit /b 1
)
echo.

echo [3/3] 新增出站規則...
netsh advfirewall firewall add rule name="Allow Port 8001 Outbound" dir=out action=allow protocol=TCP localport=8001 >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ 出站規則已建立
) else (
    echo ⚠️  出站規則建立失敗（但不影響主要功能）
)
echo.

echo ════════════════════════════════════════════════════
echo ✅ 防火牆設定完成！
echo.
echo 已建立的規則：
echo   • 入站: 允許 TCP 埠 8001
echo   • 出站: 允許 TCP 埠 8001
echo.
echo 💡 下一步：設定路由器埠轉發
echo ════════════════════════════════════════════════════
echo.

pause
