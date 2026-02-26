# LivePortrait 本地安裝腳本 (修正版)
# 虛擬人物動畫生成工具

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " 安裝 LivePortrait - 虛擬人物動畫引擎" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

$LIVEPORTRAIT_DIR = "D:\zhe-wei-tech\LivePortrait"
$VENV_PATH = "D:\zhe-wei-tech\Jarvis_Training\.venv312"

# Step 1: Clone repository
Write-Host "[1/5] 克隆 LivePortrait 專案..." -ForegroundColor Yellow
if (-not (Test-Path $LIVEPORTRAIT_DIR)) {
    git clone https://github.com/KwaiVGI/LivePortrait.git $LIVEPORTRAIT_DIR
} else {
    Write-Host "LivePortrait 已存在，更新中..."
    Set-Location $LIVEPORTRAIT_DIR
    git pull
}

Set-Location $LIVEPORTRAIT_DIR

# Step 2: Install dependencies (使用預編譯版本)
Write-Host "[2/5] 安裝依賴..." -ForegroundColor Yellow
& "$VENV_PATH\Scripts\Activate.ps1"

# 先安裝預編譯的 scipy，避免編譯錯誤
Write-Host "  安裝預編譯 scipy..."
pip install scipy --only-binary :all:

# 安裝其他依賴（跳過 scipy）
Write-Host "  安裝其他依賴..."
pip install numpy pyyaml opencv-python scikit-image scikit-learn
pip install imageio imageio-ffmpeg
pip install lmdb
pip install rich

# 安裝 PyTorch（如果還沒安裝）
Write-Host "  安裝 PyTorch..."
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# Step 3: Download models
Write-Host "[3/5] 下載模型檔案（約 1GB）..." -ForegroundColor Yellow
$pretrainedDir = Join-Path $LIVEPORTRAIT_DIR "pretrained_weights"
if (-not (Test-Path $pretrainedDir)) {
    New-Item -ItemType Directory -Path $pretrainedDir -Force | Out-Null
}

Set-Location $pretrainedDir

# Create liveportrait directory and download models
$liveportraitDir = Join-Path $pretrainedDir "liveportrait"
if (-not (Test-Path $liveportraitDir)) {
    New-Item -ItemType Directory -Path $liveportraitDir -Force | Out-Null
    Set-Location $liveportraitDir
    
    Write-Host "  下載 appearance_feature_extractor.pth..."
    Invoke-WebRequest -Uri "https://huggingface.co/KwaiVGI/LivePortrait/resolve/main/liveportrait/appearance_feature_extractor.pth" -OutFile "appearance_feature_extractor.pth" -UseBasicParsing
    
    Write-Host "  下載 motion_extractor.pth..."
    Invoke-WebRequest -Uri "https://huggingface.co/KwaiVGI/LivePortrait/resolve/main/liveportrait/motion_extractor.pth" -OutFile "motion_extractor.pth" -UseBasicParsing
    
    Write-Host "  下載 spade_generator.pth..."
    Invoke-WebRequest -Uri "https://huggingface.co/KwaiVGI/LivePortrait/resolve/main/liveportrait/spade_generator.pth" -OutFile "spade_generator.pth" -UseBasicParsing
    
    Write-Host "  下載 warping_module.pth..."
    Invoke-WebRequest -Uri "https://huggingface.co/KwaiVGI/LivePortrait/resolve/main/liveportrait/warping_module.pth" -OutFile "warping_module.pth" -UseBasicParsing
}

# Step 4: Install ComfyUI node
Write-Host "[4/5] 安裝 ComfyUI 節點..." -ForegroundColor Yellow
$COMFYUI_DIR = "D:\zhe-wei-tech\ComfyUI"
if (Test-Path $COMFYUI_DIR) {
    $nodeDir = Join-Path $COMFYUI_DIR "custom_nodes\comfyui-liveportrait"
    if (-not (Test-Path $nodeDir)) {
        Set-Location (Join-Path $COMFYUI_DIR "custom_nodes")
        git clone https://github.com/PowerHouseMan/ComfyUI-LivePortraitKJ.git comfyui-liveportrait
        Set-Location "comfyui-liveportrait"
        pip install -r requirements.txt 2>$null
    }
}

# Step 5: Done
Write-Host "[5/5] LivePortrait 安裝完成！" -ForegroundColor Green
Write-Host ""
Write-Host "使用方法：" -ForegroundColor Cyan
Write-Host "  1. 啟動 ComfyUI 並載入 LivePortrait workflow"
Write-Host "  2. 或使用命令行：python inference.py --source src.jpg --driving drv.mp4"
Write-Host ""
Write-Host "目錄：$LIVEPORTRAIT_DIR" -ForegroundColor Yellow
