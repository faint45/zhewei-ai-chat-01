@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
set "ROOT=%CD%"
set "LOG=%ROOT%\reports\deploy_all.log"
set "PY=%ROOT%\Jarvis_Training\.venv312\Scripts\python.exe"
set "ENSURE=%ROOT%\scripts\ensure_env_ollama.py"

if not exist "%ROOT%\reports" mkdir "%ROOT%\reports"
echo [%date% %time%] Deploy_All begin>> "%LOG%"

echo [1/5] Installing locked dependencies (pip install -r requirements.lock)...
if exist "%PY%" if exist "%ROOT%\requirements.lock" (
  "%PY%" -m pip install -r "%ROOT%\requirements.lock" --quiet >> "%LOG%" 2>&1
)
if not exist "%ROOT%\requirements.lock" if exist "%ROOT%\requirements-brain.lock" (
  "%PY%" -m pip install -r "%ROOT%\requirements-brain.lock" --quiet >> "%LOG%" 2>&1
)
echo [2/5] Ensuring .env and OLLAMA model settings...
if exist "%PY%" if exist "%ENSURE%" (
  "%PY%" "%ENSURE%" >> "%LOG%" 2>&1
)
if not exist "%ROOT%\.env" (
  if exist "%ROOT%\.env.example" (
    copy "%ROOT%\.env.example" "%ROOT%\.env" >> "%LOG%" 2>&1
    echo Created .env from .env.example
  )
)

echo [3/5] Starting core stack (Docker + monitor + bot)...
call "%ROOT%\Start_All_Stable.bat"
if errorlevel 1 (
  echo [ERROR] Start_All_Stable failed
  exit /b 1
)

echo [4/5] Pulling Ollama models into container...
set "OLLAMA_CONTAINER=zhe-wei-ollama"
set /a wait_cnt=0
:wait_ollama
docker ps --format "{{.Names}}" 2>nul | findstr /x "%OLLAMA_CONTAINER%" >nul 2>nul
if not errorlevel 1 goto pull_models
set /a wait_cnt+=1
if !wait_cnt! GEQ 24 (
  echo [WARN] Ollama container not ready, skip model pull>> "%LOG%"
  goto done
)
timeout /t 5 /nobreak >nul
goto wait_ollama

:pull_models
echo Pulling qwen2.5-coder:7b...>> "%LOG%"
docker exec %OLLAMA_CONTAINER% ollama pull qwen2.5-coder:7b >> "%LOG%" 2>&1
echo Pulling deepseek-r1:8b...>> "%LOG%"
docker exec %OLLAMA_CONTAINER% ollama pull deepseek-r1:8b >> "%LOG%" 2>&1
echo [OK] Ollama models ready>> "%LOG%"

:done
echo [5/5] Deploy complete.
echo [%date% %time%] Deploy_All done>> "%LOG%"
echo.
echo === One-click deploy finished ===
echo - Brain: http://127.0.0.1:8002
echo - Agent Hub: http://127.0.0.1:8002/agent-hub
echo - Health: http://127.0.0.1:8002/health-dashboard
echo - Log: %LOG%
echo.
pause
exit /b 0
