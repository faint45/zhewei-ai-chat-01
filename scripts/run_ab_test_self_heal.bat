@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

if not exist "Jarvis_Training\.venv312\Scripts\python.exe" (
  echo [ERROR] venv not found at Jarvis_Training\.venv312
  exit /b 1
)

echo [AB] Running Self-Heal Memory A/B Test...
echo.

"Jarvis_Training\.venv312\Scripts\python.exe" "scripts\ab_test_self_heal_memory.py" %*
if errorlevel 1 (
  echo.
  echo [AB] Test completed with failure(s)
  exit /b 1
)

echo.
echo [AB] Done.
exit /b 0
