"""
築未科技大腦橋接 API - 與 Discord 機器人功能一致
讓手機 APP 與築未科技大腦直接溝通，支援：天氣、時間、授權、Agent、開發協議
"""
import os
import time
from collections import defaultdict
from pathlib import Path

try:
    from flask import Flask, request, jsonify
    from flask_cors import CORS
except ImportError:
    print("請安裝: pip install flask flask-cors")
    raise

# 確保在專案目錄
BASE = Path(__file__).parent.resolve()
os.chdir(str(BASE))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from guard_core import (
    process_message,
    get_weather,
    get_time,
    grant_auth,
    revoke_auth,
    _is_authorized,
    _can_control,
)

app = Flask(__name__)
CORS(app)

API_KEY = os.environ.get("BRAIN_BRIDGE_API_KEY", "").strip()
RATE_LIMIT_PER_MIN = int(os.environ.get("BRAIN_BRIDGE_RATE_LIMIT", "30"))
_rate_cache = defaultdict(list)


def _rate_limit_key():
    return request.headers.get("X-Forwarded-For", request.remote_addr or "unknown")


def _check_rate_limit():
    if RATE_LIMIT_PER_MIN <= 0:
        return True, ""
    key = _rate_limit_key()
    now = time.time()
    cutoff = now - 60
    _rate_cache[key] = [t for t in _rate_cache[key] if t > cutoff]
    if len(_rate_cache[key]) >= RATE_LIMIT_PER_MIN:
        return False, f"速率限制：每分鐘最多 {RATE_LIMIT_PER_MIN} 次，請稍後再試"
    _rate_cache[key].append(now)
    return True, ""


def _require_auth():
    if not API_KEY:
        return True
    key = (
        request.headers.get("X-API-Key")
        or request.args.get("api_key")
        or (request.headers.get("Authorization") or "").replace("Bearer ", "").strip()
    )
    return key == API_KEY


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "service": "zhewei-brain-bridge", "features": ["chat", "agent", "weather", "time", "auth", "dev"]})


@app.route("/chat", methods=["POST"])
def chat():
    """
    發送訊息給大腦，與 Discord 機器人邏輯一致。
    Body: { "message": "用戶輸入", "user_id": "mobile" }
    支援：天氣、時間、授權、Agent、開發：協議
    """
    if not _require_auth():
        return jsonify({"error": "Unauthorized", "message": "API key required"}), 401
    ok, err = _check_rate_limit()
    if not ok:
        return jsonify({"error": "Too Many Requests", "message": err}), 429

    data = request.get_json() or {}
    msg = (data.get("message") or "").strip()
    if not msg:
        return jsonify({"error": "Bad request", "message": "message is required"}), 400

    user_id = str(data.get("user_id") or "mobile")
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    model = os.environ.get("OLLAMA_MODEL", "gemma3:4b")

    try:
        result, msg_type = process_message(msg, user_id, base_url, model)
        return jsonify({
            "reply": result,
            "type": msg_type,  # action|agent|brain|dev
        })
    except Exception as e:
        return jsonify({"error": str(e), "reply": f"處理時發生錯誤：{e}"}), 500


@app.route("/agent", methods=["POST"])
def agent_chat():
    """強制 Agent 模式（讀寫檔、建置、部署）"""
    if not _require_auth():
        return jsonify({"error": "Unauthorized"}), 401
    ok, err = _check_rate_limit()
    if not ok:
        return jsonify({"error": "Too Many Requests", "message": err}), 429

    data = request.get_json() or {}
    msg = (data.get("message") or "").strip()
    if not msg:
        return jsonify({"error": "Bad request", "message": "message is required"}), 400

    user_id = str(data.get("user_id") or "mobile")

    try:
        from guard_core import run_agent
        result = run_agent(msg, user_id)
        return jsonify({"reply": result, "type": "agent"})
    except Exception as e:
        return jsonify({"error": str(e), "reply": f"Agent 錯誤：{e}"}), 500


@app.route("/weather", methods=["GET"])
def weather():
    """取得即時天氣。query: 台北|高雄|嘉義|民雄（可選）"""
    city = request.args.get("city") or request.args.get("query") or ""
    w = get_weather(city)
    return jsonify({"weather": w or "無法取得天氣", "city": city or "嘉義"})


@app.route("/time", methods=["GET"])
def time():
    """取得現在時間"""
    return jsonify({"time": get_time()})


@app.route("/auth/grant", methods=["POST"])
def auth_grant():
    """授權（等同 Discord 說「授權」）。Body: { "user_id": "xxx" }"""
    if not _require_auth():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json() or {}
    user_id = str(data.get("user_id") or "mobile")
    if not _can_control(user_id):
        return jsonify({"reply": "⚠️ 本機操作僅限授權用戶。"}), 403
    grant_auth(user_id)
    return jsonify({"reply": "✅ 已授權。接下來 10 分鐘內可執行本機指令。"})


@app.route("/auth/revoke", methods=["POST"])
def auth_revoke():
    """關閉授權。Body: { "user_id": "xxx" }"""
    if not _require_auth():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json() or {}
    user_id = str(data.get("user_id") or "mobile")
    revoke_auth(user_id)
    return jsonify({"reply": "✅ 已關閉授權。"})


@app.route("/auth/status", methods=["GET"])
def auth_status():
    """查詢授權狀態。query: user_id=xxx"""
    user_id = request.args.get("user_id") or "mobile"
    return jsonify({"authorized": _is_authorized(user_id), "user_id": user_id})


@app.route("/v1/chat/completions", methods=["POST"])
def openai_chat_completions():
    """
    OpenAI 相容 API：供 OpenClaw 等將築未科技大腦當作 LLM 使用。
    Body: { "model": "default", "messages": [{ "role": "user", "content": "..." }] }
    """
    if not _require_auth():
        return jsonify({"error": {"message": "Unauthorized", "type": "auth_error"}}), 401
    ok, err = _check_rate_limit()
    if not ok:
        return jsonify({"error": {"message": err, "type": "rate_limit"}}), 429

    data = request.get_json() or {}
    messages = data.get("messages") or []
    if not messages:
        return jsonify({"error": {"message": "messages is required", "type": "invalid_request"}}), 400

    content = ""
    for m in reversed(messages):
        if m.get("role") == "user" and m.get("content"):
            content = m["content"] if isinstance(m["content"], str) else (m["content"][0].get("text", "") if isinstance(m["content"], list) else "")
            break
    if not content:
        return jsonify({"error": {"message": "No user message found", "type": "invalid_request"}}), 400

    try:
        from ai_providers import ask_sync
        result, prov = ask_sync(content, ensemble=False)
        return jsonify({
            "id": "zhewei-brain-" + str(int(__import__("time").time() * 1000)),
            "object": "chat.completion",
            "model": data.get("model", "default"),
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": result or ""},
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        })
    except Exception as e:
        return jsonify({"error": {"message": str(e), "type": "server_error"}}), 500


if __name__ == "__main__":
    port = int(os.environ.get("BRAIN_BRIDGE_PORT", "5100"))
    host = os.environ.get("BRAIN_BRIDGE_HOST", "0.0.0.0")
    print(f"築未科技大腦橋接 API（與 Discord 機器人功能一致）: http://{host}:{port}")
    print("POST /chat       - 一般對話（自動辨識天氣/授權/Agent/開發：）")
    print("POST /v1/chat/completions - OpenAI 相容（供 OpenClaw 串接築未大腦）")
    print("POST /agent      - 強制 Agent 模式")
    print("GET  /weather    - 即時天氣")
    print("GET  /time       - 現在時間")
    print("POST /auth/grant - 授權")
    print("POST /auth/revoke- 關閉授權")
    app.run(host=host, port=port, threaded=True)
