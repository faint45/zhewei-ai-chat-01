# 築未科技大腦 — Brain Server v2.0 模組化架構 (端口 8000)
# 建置：docker build -t zhewei-brain .
# 執行：docker run -p 8000:8000 --env-file .env zhewei-brain

FROM python:3.12-slim

WORKDIR /app

# 安裝系統依賴（含 OpenCV 所需函式庫，預留視覺等模組；Debian Bookworm+ 用 libgl1 取代 libgl1-mesa-glx）
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 優先使用鎖定版本，避免 Playwright/Ollama 等快速更新導致壞掉
COPY requirements-brain.lock requirements-brain.txt ./
RUN if [ -f requirements-brain.lock ]; then pip install --no-cache-dir -r requirements-brain.lock; else pip install --no-cache-dir -r requirements-brain.txt; fi

COPY . .

# 預設啟動 WebSocket 服務（端口 8000，支援遠端 Tailscale 訪問）
EXPOSE 8000
CMD ["python", "brain_server.py"]
