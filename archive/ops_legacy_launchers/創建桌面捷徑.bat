@echo off
chcp 65001 >nul
echo 正在創建築未科技大腦桌面捷徑...
echo.

set "SCRIPT_PATH=%~dp0"
set "TARGET_DIR=D:\zhe-wei-tech"

REM 創建桌面捷徑
powershell -Command "
$WshShell = New-Object -comObject WScript.Shell;
$Shortcut = $WshShell.CreateShortcut('$env:USERPROFILE\Desktop\築未科技大腦.lnk');
$Shortcut.TargetPath = '$env:TARGET_DIR';
$Shortcut.WorkingDirectory = '$env:TARGET_DIR';
$Shortcut.Description = '築未科技大腦 - AI 辨識系統';
$Shortcut.Save();
Write-Host '✅ 桌面捷徑已創建！' -ForegroundColor Green;
Write-Host '捷徑位置: ' $env:USERPROFILE\Desktop\築未科技大腦.lnk;
"

echo.
echo 完成！請到桌面點擊「築未科技大腦」捷徑
pause
