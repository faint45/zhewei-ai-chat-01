@echo off
title 築未科技大腦 - 本地機器人
cd /d "%~dp0"
set ZHEWEI_LOCAL_ROBOT=1
if "%1"=="--full" (
    call run-local-robot-full.bat
) else (
    python brain_core\local_robot.py %*
)
pause
