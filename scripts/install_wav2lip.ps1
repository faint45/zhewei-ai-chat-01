# Wav2Lip 本地安裝腳本
# 自動對口型工具

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " 安裝 Wav2Lip - 虛擬人物對口型引擎" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

$WAV2LIP_DIR = "D:\zhe-wei-tech\Wav2Lip"
$VENV_PATH = "D:\zhe-wei-tech\Jarvis_Training\.venv312"

# Step 1: Clone repository
Write-Host "[1/4] 克隆 Wav2Lip 專案..." -ForegroundColor Yellow
if (-not (Test-Path $WAV2LIP_DIR)) {
    git clone https://github.com/Rudrabha/Wav2Lip.git $WAV2LIP_DIR
} else {
    Write-Host "Wav2Lip 已存在，更新中..."
    Set-Location $WAV2LIP_DIR
    git pull
}

Set-Location $WAV2LIP_DIR

# Step 2: Install dependencies
Write-Host "[2/4] 安裝依賴..." -ForegroundColor Yellow
& "$VENV_PATH\Scripts\Activate.ps1"

pip install -r requirements.txt

# Step 3: Download models
Write-Host "[3/4] 下載模型檔案（約 300MB）..." -ForegroundColor Yellow
$checkpointsDir = Join-Path $WAV2LIP_DIR "checkpoints"
if (-not (Test-Path $checkpointsDir)) {
    New-Item -ItemType Directory -Path $checkpointsDir -Force | Out-Null
}

Set-Location $checkpointsDir

# Download Wav2Lip GAN model (better quality)
$ganModel = Join-Path $checkpointsDir "wav2lip_gan.pth"
if (-not (Test-Path $ganModel)) {
    Write-Host "  下載 Wav2Lip GAN 模型（品質較高）..."
    Invoke-WebRequest -Uri "https://huggingface.co/justinjohn/AI-Content-Generator/resolve/main/wav2lip_gan.pth" -OutFile "wav2lip_gan.pth" -UseBasicParsing
}

# Download standard Wav2Lip model
$standardModel = Join-Path $checkpointsDir "wav2lip.pth"
if (-not (Test-Path $standardModel)) {
    Write-Host "  下載 Wav2Lip 標準模型..."
    Invoke-WebRequest -Uri "https://huggingface.co/justinjohn/AI-Content-Generator/resolve/main/wav2lip.pth" -OutFile "wav2lip.pth" -UseBasicParsing
}

# Step 4: Done
Write-Host "[4/4] Wav2Lip 安裝完成！" -ForegroundColor Green
Write-Host ""
Write-Host "使用方法：" -ForegroundColor Cyan
Write-Host "  python inference.py --checkpoint_path checkpoints/wav2lip_gan.pth --face input_video.mp4 --audio input_audio.wav --outfile output.mp4"
Write-Host ""
Write-Host "目錄：$WAV2LIP_DIR" -ForegroundColor Yellow
