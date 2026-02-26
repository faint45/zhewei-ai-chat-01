@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "EXE=Jarvis_Training\.venv312\Scripts\interpreter.exe"

if not exist "%EXE%" (
  echo [ERROR] Open Interpreter not found: %EXE%
  echo Please run: Jarvis_Training\.venv312\Scripts\python.exe -m pip install open-interpreter
  exit /b 1
)

echo [INFO] Starting Open Interpreter in safe debug mode...
echo [INFO] Tip: Use --help for all options.
"%EXE%" --safe_mode ask --plain

endlocal
