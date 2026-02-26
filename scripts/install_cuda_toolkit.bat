@echo off
echo ============================================
echo   CUDA Toolkit 12.6 完整安裝
echo   （exllamav2 JIT 編譯需要 nvcc）
echo ============================================
echo.
echo 步驟 1: 下載 CUDA Toolkit 12.6（約 3GB）
echo 下載頁面: https://developer.nvidia.com/cuda-12-6-0-download-archive
echo.
echo 步驟 2: 安裝時選擇「自訂」，至少勾選：
echo   - CUDA Compiler (nvcc)
echo   - CUDA Runtime
echo   - CUDA Libraries
echo.
echo 步驟 3: 安裝完成後重啟終端，驗證：
echo   nvcc --version
echo   set CUDA_HOME=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.6
echo   python -c "import exllamav2; print('OK')"
echo.
echo 正在開啟下載頁面...
start https://developer.nvidia.com/cuda-12-6-0-download-archive
echo.
pause
