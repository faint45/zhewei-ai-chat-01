@echo off
chcp 65001 >nul
echo 🔍 築未科技全系統測試工具
echo.

python system_test.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ 所有測試通過！
) else (
    echo.
    echo ❌ 測試發現問題，請查看上方詳細信息
)

pause
