@echo off
cd /d "%~dp0"
python -c "from boost import main; main()"
pause
