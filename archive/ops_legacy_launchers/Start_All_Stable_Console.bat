@echo off
setlocal EnableExtensions
cd /d "%~dp0"
call "Start_All_Stable.bat" hold
exit /b %errorlevel%

