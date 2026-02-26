@echo off
REM 虛擬人物 MV 自動化製作工具
REM LivePortrait + Wav2Lip + ComfyUI 整合流程

echo =========================================
echo  虛擬人物 MV 製作 - 自動化腳本
echo =========================================

set PROJECT_DIR=%1
set CHARACTER_IMG=%2
set AUDIO_FILE=%3

if "%~1"=="" (
    echo 使用方法：make_virtual_mv.bat [專案名稱] [角色圖片路徑] [音樂檔路徑]
    echo 範例：make_virtual_mv.bat my_mv character.png song.mp3
    pause
    exit /b 1
)

set WORK_DIR=D:\zhe-wei-tech\mv_projects\%PROJECT_DIR%
set LIVEPORTRAIT_DIR=D:\zhe-wei-tech\LivePortrait
set WAV2LIP_DIR=D:\zhe-wei-tech\Wav2Lip
set VENV_PATH=D:\zhe-wei-tech\Jarvis_Training\.venv312

REM 建立專案目錄
if not exist "%WORK_DIR%" (
    mkdir "%WORK_DIR%"
    mkdir "%WORK_DIR%\01_character"
    mkdir "%WORK_DIR%\02_backgrounds"
    mkdir "%WORK_DIR%\03_liveportrait"
    mkdir "%WORK_DIR%\04_wav2lip"
    mkdir "%WORK_DIR%\05_final"
    echo [1/6] 建立專案目錄：%WORK_DIR%
)

REM 啟動虛擬環境
call "%VENV_PATH%\Scripts\activate.bat"

echo.
echo [2/6] 步驟一：生成背景動畫（ComfyUI）
echo 請手動啟動 ComfyUI 並載入 workflow/mv_background.json
echo 背景將輸出到：%WORK_DIR%\02_backgrounds\
echo.
echo 按任意鍵繼續...
pause > nul

echo [3/6] 步驟二：LivePortrait 角色動畫
echo 為角色添加動作和表情...

cd /d "%LIVEPORTRAIT_DIR%"

REM 使用默認驅動影片或指定動作
set DRIVING_VIDEO=D:\zhe-wei-tech\mv_projects\resources\driving_samples\driving.mp4

if not exist "%DRIVING_VIDEO%" (
    echo 請提供驅動動作影片（例如：點頭、說話動作）
    set /p DRIVING_VIDEO="驅動影片路徑："
)

python inference.py --source "%CHARACTER_IMG%" --driving "%DRIVING_VIDEO%" --output "%WORK_DIR%\03_liveportrait\character_animated.mp4"

echo.
echo [4/6] 步驟三：Wav2Lip 對口型
echo 讓角色跟著音樂唱歌...

cd /d "%WAV2LIP_DIR%"

REM 將音訊轉為 wav 格式（如果需要的話）
set AUDIO_WAV=%WORK_DIR%\04_wav2lip\audio.wav

REM 使用 ffmpeg 提取音訊
ffmpeg -i "%AUDIO_FILE%" -ar 16000 -ac 1 -y "%AUDIO_WAV%"

python inference.py ^
    --checkpoint_path checkpoints/wav2lip_gan.pth ^
    --face "%WORK_DIR%\03_liveportrait\character_animated.mp4" ^
    --audio "%AUDIO_WAV%" ^
    --outfile "%WORK_DIR%\04_wav2lip\character_lipsync.mp4"

echo.
echo [5/6] 步驟四：合成最終 MV
echo 合併角色與背景...

REM 使用 FFmpeg 合成
ffmpeg -i "%WORK_DIR%\02_backgrounds\background.mp4" ^
    -i "%WORK_DIR%\04_wav2lip\character_lipsync.mp4" ^
    -filter_complex "[0:v][1:v]overlay=(W-w)/2:(H-h)/2:format=auto,format=yuv420p" ^
    -c:v libx264 -crf 18 -preset slow ^
    -c:a copy ^
    -y "%WORK_DIR%\05_final\mv_final.mp4"

echo.
echo [6/6] 完成！
echo 最終 MV：%WORK_DIR%\05_final\mv_final.mp4
echo.
pause
