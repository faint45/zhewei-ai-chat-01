<<<<<<< HEAD
# 築未科技大腦 — WebSocket 服務 (端口 8000)
# 建置：docker build -t zhewei-brain .
# 執行：docker run -p 8000:8000 --env-file .env zhewei-brain

FROM python:3.12-slim

WORKDIR /app

# 安裝系統依賴（含 OpenCV 所需函式庫，預留視覺等模組；Debian Bookworm+ 用 libgl1 取代 libgl1-mesa-glx）
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-brain.txt .
RUN pip install --no-cache-dir -r requirements-brain.txt

COPY . .

# 預設啟動 WebSocket 服務（端口 8000，支援遠端 Tailscale 訪問）
EXPOSE 8000
CMD ["python", "brain_server.py"]
=======
# 築未科技七階段系統 - 基礎 Dockerfile

FROM python:3.12-slim

# 設置工作目錄
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴文件
COPY requirements_seven_stage.txt .

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements_seven_stage.txt

# 複製應用代碼
COPY *.py .
COPY config_ai.py .
COPY ai_service.py .

# 創建工作目錄
RUN mkdir -p /workspace/vision \
    /workspace/development \
    /workspace/retrieval \
    /workspace/reports \
    /workspace/logs

# 設置環境變量
ENV PYTHONUNBUFFERED=1
ENV WORKSPACE=/workspace
ENV LOG_LEVEL=INFO

# 暴露端口
EXPOSE 8000 8001 8005

# 啟動命令
CMD ["python", "seven_stage_system.py"]
>>>>>>> bd6537def53debaba0c16f279817e4a317eed98c
