@echo off
REM LivePortrait 本地安裝腳本
REM 虛擬人物動畫生成工具

echo =========================================
echo  安裝 LivePortrait - 虛擬人物動畫引擎
echo =========================================

set LIVEPORTRAIT_DIR=D:\zhe-wei-tech\LivePortrait
set VENV_PATH=D:\zhe-wei-tech\Jarvis_Training\.venv312

if not exist "%LIVEPORTRAIT_DIR%" (
    echo [1/5] 克隆 LivePortrait 專案...
    git clone https://github.com/KwaiVGI/LivePortrait.git "%LIVEPORTRAIT_DIR%"
) else (
    echo [1/5] LivePortrait 已存在，更新中...
    cd /d "%LIVEPORTRAIT_DIR%"
    git pull
)

cd /d "%LIVEPORTRAIT_DIR%"

echo [2/5] 安裝依賴...
call "%VENV_PATH%\Scripts\activate.bat"

pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt

echo [3/5] 下載模型檔案...
if not exist "pretrained_weights" (
    mkdir pretrained_weights
)

REM 使用模型下載腳本
cd pretrained_weights

REM 下載 LivePortrait 模型
echo 下載 LivePortrait 主模型...
if not exist "liveportrait" (
    mkdir liveportrait
    cd liveportrait
    curl -L -o appearance_feature_extractor.pth "https://huggingface.co/KwaiVGI/LivePortrait/resolve/main/liveportrait/appearance_feature_extractor.pth"
    curl -L -o motion_extractor.pth "https://huggingface.co/KwaiVGI/LivePortrait/resolve/main/liveportrait/motion_extractor.pth"
    curl -L -o spade_generator.pth "https://huggingface.co/KwaiVGI/LivePortrait/resolve/main/liveportrait/spade_generator.pth"
    curl -L -o warping_module.pth "https://huggingface.co/KwaiVGI/LivePortrait/resolve/main/liveportrait/warping_module.pth"
    cd ..
)

echo [4/5] 安裝 ComfyUI 節點...
set COMFYUI_DIR=D:\zhe-wei-tech\ComfyUI
if exist "%COMFYUI_DIR%" (
    if not exist "%COMFYUI_DIR%\custom_nodes\comfyui-liveportrait" (
        echo 安裝 ComfyUI LivePortrait 節點...
        cd /d "%COMFYUI_DIR%\custom_nodes"
        git clone https://github.com/PowerHouseMan/ComfyUI-LivePortraitKJ.git comfyui-liveportrait
        cd comfyui-liveportrait
        pip install -r requirements.txt
    )
)

echo [5/5] 安裝完成！
echo.
echo 使用方法：
echo   1. 啟動 ComfyUI 並載入 LivePortrait workflow
echo   2. 或使用命令行：python inference.py --source src.jpg --driving drv.mp4
echo.
echo 目錄：%LIVEPORTRAIT_DIR%
pause
