@echo off
title 築未科技 - 系統環境診斷
chcp 65001 > nul
cd /d "%~dp0"
echo 正在執行 AI 大腦環境診斷...
python startup_diagnostics.py
pause
