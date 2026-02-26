"""
築未科技大腦橋接 API - Vercel 部署版
專門為無伺服器環境優化
"""
import os
import sys
from pathlib import Path

# 添加必要的路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "tools"))
sys.path.insert(0, str(project_root / "brain_core"))

# Vercel 環境變數設置
os.environ["BRAIN_BRIDGE_PORT"] = "3000"  # Vercel 使用 3000 端口
os.environ["OLLAMA_BASE_URL"] = os.environ.get("OLLAMA_BASE_URL", "https://api.ollama.ai")

# 導入必要的模組
try:
    from fastapi import FastAPI, Request, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    import uvicorn
except ImportError:
    print("請安裝 FastAPI 相關依賴")
    raise

# 創建 FastAPI 應用
app = FastAPI(title="築未科技大腦橋接 API - Vercel", version="2.2")

# 配置 CORS - Phase 1.3 安全修復：Vercel 部署環境使用白名單
VERCEL_CORS_ORIGINS = os.environ.get(
    "CORS_ORIGINS",
    "https://zhe-wei.net,https://www.zhe-wei.net,https://brain.zhe-wei.net,https://app.zhe-wei.net"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=VERCEL_CORS_ORIGINS,  # 白名單限制
    allow_methods=["GET", "POST", "OPTIONS"],  # 限制方法
    allow_headers=["Content-Type", "Authorization"],  # 限制標頭
    allow_credentials=True,
)

# 靜態文件服務
public_dir = project_root / "public"

# 健康檢查端點
@app.get("/api/health")
def health():
    return {"ok": True, "service": "zhewei-brain-bridge", "platform": "vercel"}

# 聊天端點 (簡化版)
@app.post("/api/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        message = data.get("message", "")
        
        # 這裡可以整合您的 AI 服務
        # 例如調用 OpenAI API 或其他 AI 服務
        
        return {
            "reply": f"這是 Vercel 部署的測試回應: {message}",
            "type": "text"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 提供靜態文件
@app.get("/")
def serve_index():
    index_file = public_dir / "chat.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse("<h1>築未科技 AI 對話窗口</h1><p>請確保 public/chat.html 存在</p>")

@app.get("/chat")
def serve_chat():
    return serve_index()

# Vercel 無伺服器函數處理器
async def handler(request):
    """Vercel 無伺服器函數入口點"""
    from fastapi import Request
    from starlette.requests import Request as StarletteRequest
    
    # 將 Vercel 請求轉換為 FastAPI 請求
    scope = {
        "type": "http",
        "method": request.method,
        "path": request.path,
        "headers": [(k.encode(), v.encode()) for k, v in request.headers.items()],
        "query_string": request.query_string.encode() if request.query_string else b"",
    }
    
    starlette_request = StarletteRequest(scope)
    starlette_request._body = await request.body()
    
    # 處理請求
    response = await app(starlette_request)
    
    return {
        "statusCode": response.status_code,
        "headers": dict(response.headers),
        "body": (await response.body()).decode() if hasattr(response, 'body') else ""
    }

# 本地開發時使用
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3000)