@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set "ARCHIVE=%CD%\archive\ops_legacy_launchers"

if not exist "%ARCHIVE%" mkdir "%ARCHIVE%"

for %%f in (
  "啟動完整跑.bat"
  "一鍵啟動.bat"
  "Start_All_Stable.bat"
  "Start_All_Stable_Console.bat"
  "Start_OpenHands.bat"
  "Start_OpenWebUI.bat"
  "Start_48H_Warroom.bat"
  "Start_OpenInterpreter_Debug.bat"
  "Deploy_All.bat"
  "Boot_Health_Check_And_Start.bat"
  "診斷外網連線.bat"
  "build_simple.bat"
  "build_installer.bat"
  "test_package.bat"
  "setup_wizard.bat"
) do (
  if exist %%f (
    move /Y %%f "%ARCHIVE%\" >nul 2>&1 && echo Moved %%f
  )
)

echo Done.
pause
