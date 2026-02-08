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
