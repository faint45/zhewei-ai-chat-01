@echo off
chcp 65001 >nul
title 停止築未科技系統

echo.
echo ════════════════════════════════════════════════════
echo  停止築未科技系統服務
echo ════════════════════════════════════════════════════
echo.

echo 正在查找並停止相關進程...
echo.

:: 查找並終止佔用端口 8000 的進程
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000"') do (
    echo 終止端口 8000 的進程 (PID: %%a)
    taskkill /F /PID %%a >nul 2>&1
)

:: 查找並終止佔用端口 8005 的進程
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8005"') do (
    echo 終止端口 8005 的進程 (PID: %%a)
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo ════════════════════════════════════════════════════
echo.
echo ✅ 服務已停止
echo.
echo 💡 提示：某些進程可能需要手動關閉對應的終端窗口
echo.
pause
