# -*- coding: utf-8 -*-
"""
築未科技 — 全功能伺服器大腦與管理網頁（端口 8000）
核心伺服器：調度所有 AI 代理人，即時將處理狀態推播至網頁。
靜態資源：D:\\brain_workspace\\static；根路由靜態對話頁；/ws 對話中樞。
web_admin_progress.json 定期讀取並經 WebSocket 廣播進度。
"""
import asyncio
import json
import logging
import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass
BRAIN_WORKSPACE = Path(os.environ.get("BRAIN_WORKSPACE", r"D:\brain_workspace"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from ai_service import GeminiService, OllamaService
from agent_logic import AgentManager
import uvicorn

app = FastAPI(title="Zhewei Brain Command Center", description="端口 8000，/ 靜態頁、/static 靜態檔、/ws 對話中樞")

# 網域白名單（CORS）
origins = [
    "https://zhe-wei.net",
    "https://brain.zhe-wei.net",
    "http://localhost:3000",
    "http://localhost:8000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 雙引擎與代理人
gemini_ai = GeminiService()
ollama_ai = OllamaService(model_name="qwen2.5-coder:7b")

# WebSocket 連線集：供進度廣播
ws_clients: set[WebSocket] = set()
PROGRESS_FILE = BRAIN_WORKSPACE / "output" / "web_admin_progress.json"
if not PROGRESS_FILE.parent.exists():
    PROGRESS_FILE = ROOT / "brain_workspace" / "output" / "web_admin_progress.json"
_last_progress: str = ""


async def broadcast_progress():
    """定期讀取 web_admin_progress.json 並廣播至所有連線。"""
    global _last_progress
    while True:
        await asyncio.sleep(2)
        dead = set()
        try:
            if PROGRESS_FILE.exists():
                raw = PROGRESS_FILE.read_text(encoding="utf-8", errors="replace")
                data = json.loads(raw)
                content = data.get("data", "")
                if content and content != _last_progress:
                    _last_progress = content
                    msg = {"type": "progress", "content": content}
                    for ws in list(ws_clients):
                        try:
                            await ws.send_json(msg)
                        except Exception:
                            dead.add(ws)
        except (json.JSONDecodeError, OSError):
            pass
        for ws in dead:
            ws_clients.discard(ws)

# 掛載靜態檔案（D 槽 workspace）；本機開發時若專案內 brain_workspace/static 存在則優先使用
STATIC_DIR = BRAIN_WORKSPACE / "static"
FALLBACK_STATIC = ROOT / "brain_workspace" / "static"
if (not STATIC_DIR.exists() or not (STATIC_DIR / "index.html").exists()) and FALLBACK_STATIC.exists():
    STATIC_DIR = FALLBACK_STATIC
STATIC_DIR.mkdir(parents=True, exist_ok=True)
# 若 D 槽 static 無 index.html，從專案複製，避免 StaticFiles 回傳 404
if not (STATIC_DIR / "index.html").exists() and (FALLBACK_STATIC / "index.html").exists():
    import shutil
    shutil.copy2(str(FALLBACK_STATIC / "index.html"), str(STATIC_DIR / "index.html"))


@app.get("/static/index.html")
async def get_static_index():
    """優先回傳管理介面，避免 StaticFiles 路徑問題導致 404。"""
    for d in (STATIC_DIR, FALLBACK_STATIC):
        p = d / "index.html"
        if p.exists():
            return FileResponse(str(p))
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("index.html not found", status_code=404)


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def get_index():
    index_path = ROOT / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "築未科技大腦 WebSocket 服務運行中", "ws": "/ws"}


@app.get("/admin")
async def get_admin():
    """管理介面備用入口：與 /static/index.html 同內容。"""
    for d in (STATIC_DIR, FALLBACK_STATIC):
        p = d / "index.html"
        if p.exists():
            return FileResponse(str(p))
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("index.html not found", status_code=404)


@app.get("/chat")
async def get_chat():
    """手機版對話頁：/static/chat.html。"""
    for d in (STATIC_DIR, FALLBACK_STATIC):
        p = d / "chat.html"
        if p.exists():
            return FileResponse(str(p))
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("chat.html not found", status_code=404)


@app.get("/health")
def health_check():
    """健康檢查：含依賴狀態（Ollama、venv_vision、靜態目錄）。"""
    ollama_ok = False
    try:
        import urllib.request
        url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434") + "/api/tags"
        with urllib.request.urlopen(urllib.request.Request(url, method="GET"), timeout=2) as r:
            ollama_ok = r.status == 200
    except Exception:
        pass
    venv_vision = BRAIN_WORKSPACE / "venv_vision" / "Scripts" / "python.exe"
    if not venv_vision.exists():
        venv_vision = BRAIN_WORKSPACE / "venv_vision" / "bin" / "python"
    return {
        "status": "healthy",
        "engine": os.environ.get("BRAIN_ENGINE", "i7-14700-Core"),
        "ollama": ollama_ok,
        "venv_vision": venv_vision.exists(),
        "static_dir": (STATIC_DIR / "index.html").exists(),
        "progress_dir": PROGRESS_FILE.parent.exists(),
    }


@app.get("/api/progress")
def api_progress():
    """回傳 web_admin_progress.json 內容，供管理介面輪詢或初次載入。"""
    try:
        if PROGRESS_FILE.exists():
            data = json.loads(PROGRESS_FILE.read_text(encoding="utf-8", errors="replace"))
            return {"ok": True, "data": data.get("data", ""), "updated": data.get("updated", "")}
    except (json.JSONDecodeError, OSError):
        pass
    return {"ok": True, "data": "", "updated": ""}


@app.get("/api/agents")
def api_agents():
    """各引擎可用性（Gemini/Ollama 等），供管理介面動態顯示在線/離線。"""
    gemini_ok = bool(os.environ.get("GEMINI_API_KEY", "").strip() and os.environ.get("GEMINI_API_KEY", "").strip() != "your-gemini-api-key")
    ollama_ok = False
    try:
        import urllib.request
        req = urllib.request.Request(os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434") + "/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=2) as r:
            ollama_ok = r.status == 200
    except Exception:
        pass
    claude_ok = bool((os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY") or "").strip())
    return {
        "Gemini Admin": {"online": gemini_ok, "role": "複雜決策/管理員"},
        "Claude Dev": {"online": claude_ok, "role": "編碼/修正"},
        "Ollama Local": {"online": ollama_ok, "role": "地端檢核"},
        "Media Gen": {"online": bool(os.environ.get("XAI_API_KEY", "").strip()), "role": "Jimeng/Grok"},
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    ws_clients.add(websocket)

    async def send_to_client(message):
        await websocket.send_json(message)

    manager = AgentManager(
        gemini_service=gemini_ai,
        ollama_service=ollama_ai,
        max_turns=10,
    )

    try:
        while True:
            data = await websocket.receive_text()
            request = json.loads(data)
            user_input = request.get("text", "") or request.get("message", "")

            if not user_input:
                continue

            # 觸發八階段工作流；進度與結果即時推播
            await manager.run(user_input, send_message=send_to_client)

    except WebSocketDisconnect:
        ws_clients.discard(websocket)
        logging.info("Client disconnected")
    except json.JSONDecodeError:
        try:
            await websocket.send_json({"type": "error", "content": "請傳送 JSON，含 text 或 message 欄位"})
        except Exception:
            pass
    except Exception as e:
        logging.error("WS 異常: %s\n%s", e, traceback.format_exc())
        try:
            await websocket.send_json({"type": "error", "content": f"系統異常: {str(e)}"})
        except Exception:
            pass


@app.on_event("startup")
async def startup():
    asyncio.create_task(broadcast_progress())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    PORT = int(os.environ.get("PORT", os.environ.get("BRAIN_WS_PORT", "8000")))
    uvicorn.run(app, host="0.0.0.0", port=PORT)
