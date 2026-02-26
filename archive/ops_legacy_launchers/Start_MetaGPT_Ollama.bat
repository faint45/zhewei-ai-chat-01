@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

call "MetaGPT_env\.venv\Scripts\python.exe" -c "import sys; print(sys.version)" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
  echo [ERROR] MetaGPT venv not ready: MetaGPT_env\.venv
  pause
  exit /b 1
)

powershell -ExecutionPolicy Bypass -File "scripts\switch_metagpt_model.ps1" -Provider ollama
if %ERRORLEVEL% NEQ 0 (
  echo [ERROR] Switch to Ollama failed
  pause
  exit /b 1
)

echo.
set /p IDEA=Enter idea for MetaGPT: 
if "%IDEA%"=="" set IDEA=Build a minimal Flask API with tests
"MetaGPT_env\.venv\Scripts\metagpt.exe" "%IDEA%"
pause
