@echo off
chcp 65001 >nul
title 筑未科技 - Tailscale 状态检查

echo ============================================================
echo 筑未科技 - Tailscale 状态检查
echo ============================================================
echo.

echo [检查 1/3] 检查 Tailscale 服务状态...
sc query tailscale | find "RUNNING"
if %ERRORLEVEL% EQU 0 (
    echo [✅] Tailscale 服务正在运行
) else (
    echo [❌] Tailscale 服务未运行
    echo.
    echo 请启动服务：
    echo   net start tailscale
)
echo.

echo [检查 2/3] 检查 Tailscale IP 地址...
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /C:"100."') do (
    set TAILSCALE_IP=%%a
    goto :found_ip
)
:found_ip
if defined TAILSCALE_IP (
    set TAILSCALE_IP=%TAILSCALE_IP: =%
    echo [✅] 找到 Tailscale IP: %TAILSCALE_IP%
) else (
    echo [⚠️] 未找到 Tailscale IP 地址
    echo.
    echo 这可能是因为：
    echo   - Tailscale 未登录
    echo   - 网络连接问题
    echo   - 需要重新登录
)
echo.

echo [检查 3/3] 尝试获取 Tailscale 状态...
"C:\Program Files\Tailscale\tailscale.exe" status 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [✅] Tailscale 状态获取成功
) else (
    echo [⚠️] 无法获取详细状态
    echo.
    echo 可能的原因：
    echo   - Tailscale 未登录到账号
    echo   - 需要打开 Tailscale 应用完成登录
    echo.
    echo 请按以下步骤操作：
    echo   1. 找到系统托盘中的 Tailscale 图标
    echo   2. 双击打开 Tailscale
    echo   3. 如果未登录，点击登录按钮
    echo   4. 使用 Google/Microsoft/GitHub 账号登录
)
echo.

echo ============================================================
echo 网络信息
echo ============================================================
echo.
echo 当前网络适配器：
ipconfig | findstr /C:"IPv4" /C:"100."
echo.

echo ============================================================
echo 检查完成
echo ============================================================
echo.
echo 📋 下一步：
echo.
echo 如果 Tailscale 已登录：
echo   - 记录您的 Tailscale IP（格式：100.x.x.x）
echo   - 在其他设备上安装并登录 Tailscale
echo   - 从其他设备 ping 您的 Tailscale IP
echo.
echo 如果 Tailscale 未登录：
echo   1. 打开 Tailscale 应用（在系统托盘）
echo   2. 使用账号登录
echo   3. 重新运行此脚本
echo.
echo 详细配置指南：
echo   - 基础设施配置指南.md
echo   - TAILSCALE_SETUP.md
echo.
pause
