#!/bin/bash
# 築未科技 — 雲端自動部署腳本
# 用途：一鍵部署到 VPS（Oracle Cloud / Linode / DigitalOcean 等）

set -e

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== 築未科技雲端部署腳本 ===${NC}"

# 檢查必要工具
command -v docker >/dev/null 2>&1 || { echo -e "${RED}錯誤: 未安裝 Docker${NC}"; exit 1; }
command -v docker compose >/dev/null 2>&1 || { echo -e "${RED}錯誤: 未安裝 Docker Compose${NC}"; exit 1; }

# 設定工作目錄
WORK_DIR=${WORK_DIR:-/opt/zhewei}
cd "$WORK_DIR" || { echo -e "${RED}錯誤: 找不到目錄 $WORK_DIR${NC}"; exit 1; }

# 檢查 .env 檔案
if [ ! -f .env ]; then
    echo -e "${RED}錯誤: 找不到 .env 檔案${NC}"
    echo "請先建立 .env 並設定必要環境變數："
    echo "  CLOUDFLARE_TOKEN=your_token"
    echo "  GEMINI_API_KEY=your_key"
    exit 1
fi

# 檢查 CLOUDFLARE_TOKEN
if ! grep -q "CLOUDFLARE_TOKEN=" .env; then
    echo -e "${YELLOW}警告: .env 中未設定 CLOUDFLARE_TOKEN${NC}"
    echo "外網存取將無法使用"
fi

echo -e "${GREEN}步驟 1/6: 停止舊容器${NC}"
docker compose -f docker-compose.cloud.yml down || true

echo -e "${GREEN}步驟 2/6: 拉取最新映像${NC}"
docker compose -f docker-compose.cloud.yml pull

echo -e "${GREEN}步驟 3/6: 構建應用映像${NC}"
docker compose -f docker-compose.cloud.yml build --no-cache

echo -e "${GREEN}步驟 4/6: 啟動 Ollama 並拉取模型${NC}"
docker compose -f docker-compose.cloud.yml up -d ollama

# 等待 Ollama 啟動
echo "等待 Ollama 啟動..."
for i in {1..30}; do
    if docker exec zhewei_ollama ollama list >/dev/null 2>&1; then
        echo -e "${GREEN}Ollama 已啟動${NC}"
        break
    fi
    sleep 2
    if [ $i -eq 30 ]; then
        echo -e "${RED}錯誤: Ollama 啟動超時${NC}"
        exit 1
    fi
done

# 檢查記憶體並選擇合適模型
TOTAL_MEM=$(free -m | awk '/^Mem:/{print $2}')
echo "系統記憶體: ${TOTAL_MEM}MB"

if [ "$TOTAL_MEM" -lt 2048 ]; then
    echo -e "${YELLOW}記憶體不足 2GB，僅安裝輕量模型${NC}"
    MODELS=("gemma2:2b" "nomic-embed-text")
elif [ "$TOTAL_MEM" -lt 4096 ]; then
    echo "記憶體 2-4GB，安裝中型模型"
    MODELS=("qwen2.5:3b" "gemma2:2b" "nomic-embed-text")
else
    echo "記憶體充足，安裝完整模型"
    MODELS=("qwen2.5-coder:7b" "qwen2.5:3b" "gemma2:2b" "nomic-embed-text" "llama3.2:3b")
fi

for model in "${MODELS[@]}"; do
    echo "拉取模型: $model"
    docker exec zhewei_ollama ollama pull "$model" || echo -e "${YELLOW}警告: $model 拉取失敗${NC}"
done

echo -e "${GREEN}步驟 5/6: 啟動所有服務${NC}"
docker compose -f docker-compose.cloud.yml up -d

echo -e "${GREEN}步驟 6/6: 健康檢查${NC}"
sleep 10

# 檢查服務狀態
SERVICES=("ollama" "brain_server" "gateway" "portal" "cms" "codesim" "tunnel")
FAILED=0

for service in "${SERVICES[@]}"; do
    if docker ps | grep -q "zhewei_$service"; then
        echo -e "${GREEN}✓ $service 運行中${NC}"
    else
        echo -e "${RED}✗ $service 未運行${NC}"
        FAILED=1
    fi
done

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}=== 部署成功！===${NC}"
    echo ""
    echo "服務狀態："
    docker compose -f docker-compose.cloud.yml ps
    echo ""
    echo "查看日誌："
    echo "  docker compose -f docker-compose.cloud.yml logs -f"
    echo ""
    echo "外網存取（需設定 Cloudflare Tunnel）："
    echo "  https://jarvis.zhe-wei.net"
    echo "  https://cms.zhe-wei.net"
    echo "  https://codesim.zhe-wei.net"
else
    echo -e "${RED}=== 部署失敗，請檢查日誌 ===${NC}"
    echo "查看錯誤："
    echo "  docker compose -f docker-compose.cloud.yml logs"
    exit 1
fi
