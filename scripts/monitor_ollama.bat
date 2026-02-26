@echo off
REM ============================================
REM Ollama 服務監控與自動重啟腳本
REM ============================================
REM 功能：
REM - 監控 Ollama 服務狀態
REM - 自動重啟離線服務
REM - 健康檢查與日誌記錄

setlocal

REM 設定
set OLLAMA_URL=http://localhost:11434
set CHECK_INTERVAL=60
set MAX_RETRIES=3
set LOG_FILE=brain_workspace\logs\ollama_monitor.log
set OLLAMA_PATH=%USERPROFILE%\.ollama

echo ============================================ >> %LOG_FILE%
echo [%date% %time%] Ollama Monitor Started >> %LOG_FILE%

:LOOP
echo [%date% %time%] Checking Ollama... >> %LOG_FILE%

REM 檢查 Ollama 是否運行
powershell -Command "$wc = New-Object System.Net.WebClient; try { $wc.DownloadString('%OLLAMA_URL%/api/tags') | Out-Null; Write-Host 'ONLINE' } catch { Write-Host 'OFFLINE' }" > %TEMP%\ollama_status.txt

set /p STATUS=<%TEMP%\ollama_status.txt
del %TEMP%\ollama_status.txt

if "%STATUS%"=="OFFLINE" (
    echo [%date% %time%] Ollama is OFFLINE, attempting restart... >> %LOG_FILE%
    
    REM 嘗試重啟 Ollama
    set RETRY=0
    :RETRY_LOOP
    if %RETRY% LSS %MAX_RETRIES% (
        set /a RETRY+=1
        echo [%date% %time%] Retry %RETRY%/%MAX_RETRIES%... >> %LOG_FILE%
        
        REM 檢查是否有 ollama.exe 運行
        tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | findstr /I "ollama.exe" >NUL
        if %ERRORLEVEL% equ 0 (
            echo [%date% %time%] Killing existing Ollama process... >> %LOG_FILE%
            taskkill /F /IM ollama.exe >NUL 2>&1
            timeout /T 3 /NOBREAK >NUL
        )
        
        REM 啟動 Ollama
        start "" ollama.exe serve
        timeout /T 5 /NOBREAK >NUL
        
        REM 再次檢查
        powershell -Command "$wc = New-Object System.Net.WebClient; try { $wc.DownloadString('%OLLAMA_URL%/api/tags') | Out-Null; Write-Host 'ONLINE' } catch { Write-Host 'OFFLINE' }" > %TEMP%\ollama_status.txt
        set /p STATUS=<%TEMP%\ollama_status.txt
        del %TEMP%\ollama_status.txt
        
        if "%STATUS%"=="ONLINE" (
            echo [%date% %time%] Ollama restarted successfully >> %LOG_FILE%
        ) else (
            echo [%date% %time%] Restart attempt %RETRY% failed >> %LOG_FILE%
            goto RETRY_LOOP
        )
    ) else (
        echo [%date% %time%] Failed to restart Ollama after %MAX_RETRIES% attempts >> %LOG_FILE%
    )
) else (
    echo [%date% %time%] Ollama is ONLINE >> %LOG_FILE%
)

REM 等待下次檢查
timeout /T %CHECK_INTERVAL% /NOBREAK >NUL
goto LOOP

endlocal
