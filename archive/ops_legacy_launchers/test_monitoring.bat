@echo off
chcp 65001 >nul
echo.
echo ========================================
echo    API 监控服务测试脚本
echo ========================================
echo.

echo 运行测试程序...
echo.

python test_monitoring.py

echo.
pause
