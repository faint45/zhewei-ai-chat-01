@echo off
chcp 65001 >nul
REM Wav2Lip Installation Script

echo =========================================
echo  Installing Wav2Lip - Lip Sync Engine
echo =========================================
echo.

set "WAV2LIP_DIR=D:\zhe-wei-tech\Wav2Lip"
set "VENV_PATH=D:\zhe-wei-tech\Jarvis_Training\.venv312"

REM Step 1: Clone repository
echo [1/4] Cloning Wav2Lip repository...
if not exist "%WAV2LIP_DIR%" (
    git clone https://github.com/Rudrabha/Wav2Lip.git "%WAV2LIP_DIR%"
) else (
    echo Wav2Lip exists, updating...
    cd /d "%WAV2LIP_DIR%"
    git pull
)

cd /d "%WAV2LIP_DIR%"

REM Step 2: Install dependencies
echo [2/4] Installing dependencies...
call "%VENV_PATH%\Scripts\activate.bat"

pip install -r requirements.txt 2>nul || (
    echo Installing individual packages...
    pip install numpy opencv-python librosa scipy
    pip install soundfile pillow
)

REM Step 3: Download models
echo [3/4] Downloading models (~300MB)...
if not exist "checkpoints" mkdir checkpoints
cd checkpoints

if not exist "wav2lip_gan.pth" (
    echo   Downloading wav2lip_gan.pth...
    curl -L -o wav2lip_gan.pth "https://huggingface.co/justinjohn/AI-Content-Generator/resolve/main/wav2lip_gan.pth" --progress-bar
)

if not exist "wav2lip.pth" (
    echo   Downloading wav2lip.pth...
    curl -L -o wav2lip.pth "https://huggingface.co/justinjohn/AI-Content-Generator/resolve/main/wav2lip.pth" --progress-bar
)

REM Step 4: Done
echo.
echo [4/4] Wav2Lip installation complete!
echo.
echo Usage:
echo   python inference.py --checkpoint_path checkpoints/wav2lip_gan.pth --face video.mp4 --audio audio.wav --outfile output.mp4
echo.
echo Directory: %WAV2LIP_DIR%
pause
