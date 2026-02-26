@echo off
REM Wav2Lip 本地安裝腳本
REM 自動對口型工具

echo =========================================
echo  安裝 Wav2Lip - 虛擬人物對口型引擎
echo =========================================

set WAV2LIP_DIR=D:\zhe-wei-tech\Wav2Lip
set VENV_PATH=D:\zhe-wei-tech\Jarvis_Training\.venv312

if not exist "%WAV2LIP_DIR%" (
    echo [1/5] 克隆 Wav2Lip 專案...
    git clone https://github.com/Rudrabha/Wav2Lip.git "%WAV2LIP_DIR%"
) else (
    echo [1/5] Wav2Lip 已存在，更新中...
    cd /d "%WAV2LIP_DIR%"
    git pull
)

cd /d "%WAV2LIP_DIR%"

echo [2/5] 安裝依賴...
call "%VENV_PATH%\Scripts\activate.bat"

pip install -r requirements.txt

echo [3/5] 下載模型檔案...
if not exist "checkpoints" (
    mkdir checkpoints
)

if not exist "checkpoints\wav2lip_gan.pth" (
    echo 下載 Wav2Lip GAN 模型（品質較高）...
    curl -L -o checkpoints\wav2lip_gan.pth "https://huggingface.co/justinjohn/AI-Content-Generator/resolve/main/wav2lip_gan.pth"
)

if not exist "checkpoints\wav2lip.pth" (
    echo 下載 Wav2Lip 標準模型...
    curl -L -o checkpoints\wav2lip.pth "https://huggingface.co/justinjohn/AI-Content-Generator/resolve/main/wav2lip.pth"
)

if not exist "checkpoints\visual_quality_disc.pth" (
    echo 下載視覺品質判別器...
    curl -L -o checkpoints\visual_quality_disc.pth "https://huggingface.co/justinjohn/AI-Content-Generator/resolve/main/visual_quality_disc.pth"
)

echo [4/5] 安裝額外依賴...
pip install opencv-python librosa numpy soundfile scipy

echo [5/5] 安裝完成！
echo.
echo 使用方法：
echo   python inference.py --checkpoint_path checkpoints/wav2lip_gan.pth --face input_video.mp4 --audio input_audio.wav --outfile output.mp4
echo.
echo 目錄：%WAV2LIP_DIR%
pause
