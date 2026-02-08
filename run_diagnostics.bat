@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Running Zhewei Brain Startup Diagnostics...
echo.
python startup_diagnostics.py
if %errorlevel% neq 0 (
    echo.
    echo Diagnostics failed! Please fix the issues above.
    pause
    exit /b 1
)
echo.
echo Diagnostics passed! Ready to start brain.
pause
