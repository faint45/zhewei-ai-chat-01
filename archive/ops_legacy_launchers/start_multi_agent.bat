@echo off
chcp 65001 >nul
title Start Multi-Agent System

echo.
echo =====================================================
echo   Multi-Agent System Launcher
echo =====================================================
echo.

cd /d "%~dp0"

echo [1/5] Checking Python environment...
if not exist "venv\Scripts\python.exe" (
    echo ERROR: Python virtual environment not found
    echo.
    echo Please create virtual environment first:
    echo   python -m venv venv
    echo   venv\Scripts\pip install -r requirements_ai.txt
    echo.
    pause
    exit /b 1
)
echo OK: Python environment check complete
echo.

echo [2/5] Checking required files...
if not exist "ai_service.py" (
    echo ERROR: ai_service.py not found
    pause
    exit /b 1
)
if not exist "brain_server.py" (
    echo ERROR: brain_server.py not found
    pause
    exit /b 1
)
if not exist "remote_control_server.py" (
    echo ERROR: remote_control_server.py not found
    pause
    exit /b 1
)
echo OK: All required files found
echo.

echo [3/5] Checking port usage...
netstat -ano | findstr ":8001" >nul 2>&1
if %errorlevel% equ 0 (
    echo WARNING: Port 8001 may be in use
)

netstat -ano | findstr ":8002" >nul 2>&1
if %errorlevel% equ 0 (
    echo WARNING: Port 8002 may be in use
)

netstat -ano | findstr ":8005" >nul 2>&1
if %errorlevel% equ 0 (
    echo WARNING: Port 8005 may be in use
)
echo.

echo [4/5] Setting environment variables...
set AI_PORT=8001
set BRAIN_PORT=8002
set CONTROL_PORT=8005
echo AI Service Port: %AI_PORT%
echo Brain Service Port: %BRAIN_PORT%
echo Remote Control Port: %CONTROL_PORT%
echo.

echo [5/5] Starting multi-agent services...
echo.

echo Starting AI Service on port %AI_PORT%...
start "AI Service [Port %AI_PORT%]" cmd /k "title AI Service && echo. && echo AI Service Started && echo Local: http://localhost:%AI_PORT% && echo Remote: http://huwei-tech.duckdns.org:%AI_PORT% && echo. && venv\Scripts\python.exe ai_service.py"

timeout /t 3 >nul

echo Starting Brain Service on port %BRAIN_PORT%...
start "Brain Service [Port %BRAIN_PORT%]" cmd /k "title Brain Service && echo. && echo Brain Service Started && echo Local: http://localhost:%BRAIN_PORT% && echo Remote: http://huwei-tech.duckdns.org:%BRAIN_PORT% && echo. && venv\Scripts\python.exe brain_server.py"

timeout /t 3 >nul

echo Starting Remote Control Service on port %CONTROL_PORT%...
start "Remote Control Service [Port %CONTROL_PORT%]" cmd /k "title Remote Control Service && echo. && echo Remote Control Service Started && echo Local: http://localhost:%CONTROL_PORT% && echo Remote: http://huwei-tech.duckdns.org:%CONTROL_PORT% && echo. && venv\Scripts\python.exe remote_control_server.py"

timeout /t 2 >nul

echo.
echo =====================================================
echo   Multi-Agent Services Started Successfully!
echo =====================================================
echo.
echo Service Access Addresses:
echo   - AI Service:    http://localhost:8001
echo   - Brain Service: http://localhost:8002
echo   - Remote Control:http://localhost:8005
echo.
echo Tips:
echo   - Each service runs in a separate window
echo   - Close window to stop the service
echo   - Run stop_all_services.bat to stop all services
echo   - Run test_all.py for system testing
echo.
echo Press any key to open AI Service...
pause >nul

start http://localhost:8001
