@echo off
chcp 65001 >nul
title 築未科技 - Rclone 掛載測試

echo ============================================================
echo 築未科技 - Rclone / Google Drive 測試
echo ============================================================
echo.

:: [測試 1/5] rclone 版本
echo [測試 1/5] 檢查 rclone 版本...
where rclone >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [失敗] 找不到 rclone，請先安裝並加入 PATH。
    goto :end
)
rclone version
if %ERRORLEVEL% NEQ 0 (
    echo [失敗] rclone 執行錯誤。
    goto :end
)
echo [通過]
echo.

:: [測試 2/5] Google Drive 連線
echo [測試 2/5] 檢查 Google Drive 連線（gdrive）...
rclone listremotes | findstr /C:"gdrive:" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [失敗] 未找到遠端 gdrive，請執行 rclone config 建立。
    goto :end
)
rclone lsd gdrive: --max-depth 1
if %ERRORLEVEL% NEQ 0 (
    echo [失敗] 無法連線至 gdrive，請檢查網路與 OAuth。
    goto :end
)
echo [通過]
echo.

:: [測試 3/5] 儲存空間
echo [測試 3/5] 檢查儲存空間...
rclone about gdrive:
if %ERRORLEVEL% NEQ 0 (
    echo [警告] 無法取得儲存空間資訊（不影響掛載）。
) else (
    echo [通過]
)
echo.

:: [測試 4/5] Z 槽檔案讀寫（僅在已掛載時）
echo [測試 4/5] 測試 Z 槽檔案讀寫...
if not exist Z:\ (
    echo [略過] Z 槽未掛載。請先執行「掛載 Google Drive 為 Z 槽.bat」再測。
) else (
    set "TS=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
    set "TS=%TS: =0%"
    set "TF=Z:\test_rclone_%TS%.txt"
    echo 築未科技 Rclone 測試 > "%TF%"
    if exist "%TF%" (
        echo [通過] 已寫入測試檔：%TF%
        echo 可至 Google Drive 網頁確認是否同步。
    ) else (
        echo [失敗] 無法在 Z 槽寫入檔案。
    )
)
echo.

:: [測試 5/5] 同步乾跑（僅在已掛載時）
echo [測試 5/5] 同步乾跑（dry-run）...
if not exist Z:\ (
    echo [略過] Z 槽未掛載。
) else (
    rclone sync Z:\ gdrive: --dry-run -v
    if %ERRORLEVEL% EQU 0 (
        echo [通過] 同步測試完成（未實際傳輸）。
    ) else (
        echo [警告] 同步乾跑有錯誤或無變更。
    )
)
echo.

:end
echo ============================================================
echo 測試結束。
echo ============================================================
pause
