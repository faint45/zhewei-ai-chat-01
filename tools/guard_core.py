"""
築未科技 - 萬能助理共用邏輯（Discord 機器人與大腦橋接共用）
天氣、授權、AI 對話、Agent、軍師協議
"""
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import requests
except ImportError:
    requests = None

BASE_DIR = Path(__file__).parent.resolve()
try:
    from brain_data_config import DEV_OUTPUT_PATH
    DEV_OUTPUT = DEV_OUTPUT_PATH
except ImportError:
    DEV_OUTPUT = BASE_DIR / "dev_output.py"

STRATEGIST_CONFIG = {
    "active_api": os.environ.get("STRATEGIST_API", "PREMIUM_API"),
    "api_key": os.environ.get("STRATEGIST_API_KEY", ""),
    "endpoint": os.environ.get("STRATEGIST_ENDPOINT", "https://api.openai.com/v1/chat/completions"),
}
# 0=僅本地免費 AI 修正，不求助付費軍師；1=失敗時可呼叫付費軍師
USE_PREMIUM_STRATEGIST = os.environ.get("USE_PREMIUM_STRATEGIST", "0").strip().lower() in ("1", "true", "yes")
OLLAMA_TIMEOUT = 60
OLLAMA_WAIT_SEC = 5
AUTH_EXPIRE_SEC = 600

ASSISTANT_PROMPT = """築未科技萬能助理。只處理、不解釋。
規則：直接給作法或答案，不說明原因、不教學、不廢話。
嚴禁：自我介紹、LLM 本質分析、意識論述、局限性說明。"""

_authorized: dict[str, float] = {}
_premium_authorized: dict[str, float] = {}

ABNORMAL_ERR_KEYWORDS = ("路徑不存在", "專案路徑不存在", "permission denied", "權限不足", "access denied", "no such file", "找不到指定")
UNCERTAIN_REPLY_KEYWORDS = ("不確定", "可能", "建議手動", "無法自動", "需人工", "不一定", "或許", "maybe", "不太確定")


def _is_authorized(user_id: str) -> bool:
    now = datetime.now().timestamp()
    if user_id in _authorized and _authorized[user_id] > now:
        return True
    if user_id in _authorized:
        del _authorized[user_id]
    return False


def grant_auth(user_id: str):
    _authorized[user_id] = datetime.now().timestamp() + AUTH_EXPIRE_SEC


def revoke_auth(user_id: str):
    if user_id in _authorized:
        del _authorized[user_id]


def grant_premium_auth(user_id: str):
    _premium_authorized[str(user_id)] = datetime.now().timestamp() + AUTH_EXPIRE_SEC


def _is_premium_authorized(user_id: str) -> bool:
    now = datetime.now().timestamp()
    uid = str(user_id)
    if uid in _premium_authorized and _premium_authorized[uid] > now:
        return True
    if uid in _premium_authorized:
        del _premium_authorized[uid]
    return False


def _is_abnormal_error(err: str) -> bool:
    lower = (err or "").lower()
    return any(k.lower() in lower for k in ABNORMAL_ERR_KEYWORDS)


def _is_uncertain_reply(reply: str) -> bool:
    lower = (reply or "").lower()
    return any(k in lower for k in UNCERTAIN_REPLY_KEYWORDS)


def _can_control(user_id: str) -> bool:
    allowed = os.environ.get("AUTHORIZED_USER_ID", "").strip()
    if not allowed:
        return True
    return str(user_id) == allowed


def get_weather(msg: str = "") -> str:
    """取得即時天氣 (Open-Meteo 免費)"""
    if not requests:
        return ""
    coords = {"台北": (25.033, 121.565), "高雄": (22.627, 120.301), "嘉義": (23.487, 120.449), "民雄": (23.552, 120.432)}
    lat, lon = (23.487, 120.449)
    for k, v in coords.items():
        if k in msg:
            lat, lon = v
            break
    try:
        r = requests.get(
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true",
            timeout=5,
        )
        if r.status_code == 200:
            d = r.json().get("current_weather", {})
            temp = d.get("temperature", "?")
            wcode = d.get("weathercode", 0)
            wind = d.get("windspeed", "?")
            wdesc = {0: "晴", 1: "少雲", 2: "少雲", 3: "多雲", 45: "霧", 48: "霧", 51: "毛毛雨", 61: "雨", 80: "陣雨", 95: "雷雨"}.get(wcode, "—")
            return f"[即時天氣] 溫度 {temp}°C，{wdesc}，風速 {wind} km/h"
    except Exception:
        pass
    return ""


def get_time() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def build_prompt(user_msg: str) -> str:
    """組裝提示：含時間、天氣、意圖分流（問答類加 CoT）"""
    now = get_time()
    ctx = f"[現在] {now}\n\n"
    lower = user_msg.lower()
    if "天氣" in user_msg or "weather" in lower or "幾度" in user_msg:
        w = get_weather(user_msg)
        if w:
            ctx += f"{w}\n\n"
    intent = get_intent(user_msg)
    if intent == "question" and len(user_msg) > 30:
        ctx += "請先簡要分析再給出結論。\n\n"
    return f"{ASSISTANT_PROMPT}\n\n{ctx}用戶：{user_msg}"


def get_intent(content: str) -> str:
    """意圖分流：code | question | system | general。
    問答類（為什麼、怎麼、什麼是）優先於 code，避免「為什麼 Python...」被當程式任務。"""
    lower = content.lower().strip()
    if any(k in lower for k in ("開啟", "打開", "授權", "關閉", "檢查", "檢核", "修復", "重啟")):
        return "system"
    if any(k in lower for k in ("為什麼", "怎麼", "什麼是", "解釋", "說明", "差別", "比較", "why", "how", "what")):
        return "question"
    if "如何" in lower and len(content) < 25 and any(x in content for x in ("天氣", "幾度", "現在")):
        return "general"
    if any(k in lower for k in ("寫", "程式", "修改", "新增", "建立", "檔案", "deploy", "部署", "git", "元件", "py", "jsx", "code")):
        return "code"
    if any(k in lower for k in ("如何",)):
        return "question"
    return "general"


def is_agent_task(content: str) -> bool:
    """辨識是否為寫程式/部署/創意相關，需用 Agent"""
    lower = content.lower().strip()
    keywords = (
        "寫", "程式", "程式碼", "code", "修改", "新增", "建立", "檔案", "file",
        "deploy", "部署", "build", "建置", "git", "push", "commit",
        "改", "加", "創建", "加入", "加到",
        "修正", "更新", "網站", "首頁", "頁面", "元件", "app.jsx", "src/",
        "component", "jsx", "tsx", "py", "建立元件", "新增頁面",
        "3d", "生圖", "文字生圖", "圖片轉", "影音", "影片", "聲音", "克隆",
        "撰寫", "完案", "炒作", "人氣", "行銷", "文案",
        "邊緣", "偵測", "影像分析", "視覺", "物件偵測", "edge", "detect", "analyze", "vision", "yolo",
        "github", "git hub", "搜尋 repo", "學習資源", "自動學習", "self learn",
        "run_python", "pandas", "numpy 計算", "網頁搜尋", "fetch_url", "抓取網頁",
        "查知識庫", "search_knowledge", "diff", "比較檔案",
    )
    return any(k in lower for k in keywords)


def run_system_check() -> str:
    """檢核多個子系統狀態"""
    lines = ["【築未科技大腦 - 系統檢核】", ""]
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    try:
        if requests:
            r = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=5)
            if r.status_code == 200:
                models = r.json().get("models", []) or []
                names = [m.get("name", "") for m in models[:3] if m.get("name")]
                lines.append(f"✅ Ollama：已連線 ({', '.join(names) if names else '無模型'})")
            else:
                lines.append(f"⚠️ Ollama：HTTP {r.status_code}")
        else:
            lines.append("⚠️ Ollama：無法檢查 (缺 requests)")
    except Exception as e:
        lines.append(f"❌ Ollama：{str(e)[:80]}")
    try:
        from ai_providers import get_available, ask_sync
        provs = get_available()
        lines.append(f"✅ AI 提供者：{', '.join(provs) if provs else '無'}")
        resp, prov = ask_sync("回覆一個字：好", ensemble=False)
        if resp and "連線失敗" not in resp:
            lines.append(f"✅ AI 回應：正常 ({prov})")
        else:
            lines.append("⚠️ AI 回應：連線失敗")
    except Exception as e:
        lines.append(f"❌ AI 提供者：{str(e)[:60]}")
    try:
        from brain_knowledge import get_stats
        st = get_stats()
        lines.append(f"✅ 知識庫：{st.get('total', 0)} 筆")
    except Exception as e:
        lines.append(f"⚠️ 知識庫：{str(e)[:50]}")
    try:
        from ai_vision_monitor import health_check
        ok, err = health_check()
        lines.append("✅ AI 視覺辨識：健康" if ok else f"⚠️ AI 視覺辨識：{err[:100]}...")
    except ImportError:
        lines.append("⚠️ AI 視覺辨識：模組未安裝")
    except Exception as e:
        lines.append(f"❌ AI 視覺辨識：{str(e)[:60]}")
    try:
        url = (os.environ.get("ZHEWEI_BRAIN_URL") or "http://127.0.0.1:5100").strip().rstrip("/")
        if url and url.lower() not in ("0", "false") and requests:
            r = requests.get(f"{url}/health", timeout=3)
            lines.append("✅ Brain Bridge API：已連線" if r.status_code == 200 else f"⚠️ Brain Bridge：HTTP {r.status_code}")
        else:
            lines.append("— Brain Bridge：未啟用")
    except Exception:
        lines.append("⚠️ Brain Bridge API：離線")
    token = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
    lines.append("✅ Discord Token：已設定" if token and token != "your-discord-bot-token" and not token.startswith("your-") else "⚠️ Discord Token：未設定")
    try:
        from agent_tools import TOOL_MAP
        tools = list(TOOL_MAP.keys())
        lines.append(f"✅ Agent 工具：{len(tools)} 個")
    except Exception as e:
        lines.append(f"⚠️ Agent 工具：{str(e)[:50]}")
    return "\n".join(lines)


def handle_action(user_id: str, content: str) -> str | None:
    """授權、開啟指令。回傳結果或 None（非指令）"""
    lower = content.lower().strip()

    if any(k in lower for k in ["啟用gpt", "授權高階", "啟用高階軍師", "enable gpt"]):
        if not _can_control(user_id):
            return "⚠️ 啟用 GPT 高階軍師僅限授權用戶。請在 .env 設定 AUTHORIZED_USER_ID。"
        key = STRATEGIST_CONFIG.get("api_key", "").strip()
        if not key or key.startswith("your-"):
            return "⚠️ 請先在 .env 設定 STRATEGIST_API_KEY（OpenAI）方能啟用 GPT 高階軍師。"
        grant_premium_auth(user_id)
        return "✅ 已授權啟用 GPT 高階軍師。接下來 10 分鐘內，修復失敗時會自動啟用 GPT 協助。"

    if any(k in lower for k in ["重新啟動discord傳令兵", "重啟discord傳令兵", "重啟傳令兵", "restart discord bot"]):
        return "**重新啟動 Discord 傳令兵**\n\n請在本機專案目錄執行：`重新啟動Discord傳令兵.bat`\n或：`python zhewei_guard.py`\n（是重啟築未科技 Bot，不是 Discord 桌面程式）"

    check_kw = ("檢核", "檢查", "檢查系統", "檢核大腦", "檢核築未科技", "系統狀態", "status")
    check_scope = ("系統", "大腦", "狀態", "全部", "所有", "視覺", "ai視覺")
    if any(k in content for k in check_kw) and any(x in lower for x in check_scope):
        return run_system_check()

    if "ai視覺" in lower or "修復ai視覺" in lower or "ai視覺修正" in lower or "ai視覺監看" in lower:
        if _can_control(user_id) or _is_authorized(user_id):
            try:
                from ai_vision_monitor import health_check, ask_brain as _vision_ask, try_apply_fix
                MAX_FIX = 3
                for attempt in range(MAX_FIX):
                    ok, err = health_check()
                    if ok:
                        return "✅ AI視覺辨識系統 健康檢查通過。" if attempt == 0 else f"✅ 修復成功（第 {attempt + 1} 次檢查通過）"
                    if _is_abnormal_error(err):
                        return f"🛑 異常終止：{err[:200]}\n（路徑/權限等請手動處理）"
                    prompt = f"【AI視覺監看】健康檢查失敗。專案 {os.environ.get('AI_VISION_DIR', 'D:\\\\AI_Vision_Recognition')}。錯誤：{err[:500]}。"
                    if attempt > 0:
                        prompt += " 上次修正無效，請換其他方法。"
                    prompt += " 請給 1～3 條具體修正步驟，若缺套件請寫 pip install 套件名。"
                    reply = _vision_ask(prompt)
                    if not reply:
                        return f"⚠️ AI視覺檢查失敗：{err[:300]}\n（大腦無回覆）"
                    if _is_uncertain_reply(reply):
                        validated = ask_brain(reply, "", os.environ.get("OLLAMA_MODEL", "qwen2.5:7b"))
                        if validated and len(validated.strip()) > 20:
                            reply = validated.strip()
                    try_apply_fix(reply)
                if _is_premium_authorized(user_id):
                    gpt_reply = call_premium_diagnosis(
                        f"【AI視覺】健康檢查失敗。錯誤：{err[:500]}。請給 1～3 條具體修正步驟，若缺套件請寫 pip install 套件名。",
                        user_id,
                    )
                    if gpt_reply and len(gpt_reply.strip()) > 20:
                        try_apply_fix(gpt_reply)
                        ok2, _ = health_check()
                        if ok2:
                            return "✅ GPT 高階軍師已介入，AI視覺辨識系統修復成功。"
                hint = "\n\n若需 GPT 高階軍師協助，請回覆「啟用GPT」取得授權後，再重新說「修復AI視覺」。"
                return f"⚠️ 已嘗試 {MAX_FIX} 次修正仍失敗：{err[:200]}...{hint}"
            except ImportError:
                return "⚠️ ai_vision_monitor 模組未找到。"
            except Exception as e:
                return f"AI視覺監看異常：{e}"
        return "⚠️ 修復/檢核 AI 視覺需先授權。請說「授權」。"

    if any(k in content for k in ["關閉授權", "取消授權", "撤銷授權"]) or "revoke" in lower or "cancel auth" in lower:
        if _can_control(user_id):
            revoke_auth(user_id)
            return "✅ 已關閉授權。"
        return None
    is_control_cmd = content.strip() in ("授權", "authorize")
    wants_open = (
        ("google" in lower and any(x in content for x in ["開啟", "打開", "開", "對話"])) or
        ("cursor" in lower and any(x in content for x in ["開啟", "打開", "開", "對話"])) or
        (("gemini" in lower or "ai studio" in lower) and any(x in content for x in ["開啟", "打開", "開", "對話"]))
    )
    if (is_control_cmd or wants_open) and not _can_control(user_id):
        return "⚠️ 本機操作僅限授權用戶。請在 .env 設定 AUTHORIZED_USER_ID。"
    if is_control_cmd:
        grant_auth(user_id)
        return "✅ 已授權。接下來 10 分鐘內可執行本機指令。"
    if wants_open and not _is_authorized(user_id):
        return "⚠️ 請先說「授權」，核准後才能執行本機指令。"

    if not _is_authorized(user_id):
        return None

    open_kw = any(x in content for x in ["開啟", "打開", "開", "代開"])
    if open_kw and "google" in lower:
        try:
            import webbrowser
            webbrowser.open("https://www.google.com")
            return "已開啟 Google 瀏覽器。"
        except Exception as e:
            return f"開啟失敗: {e}"
    if open_kw and "cursor" in lower:
        try:
            subprocess.Popen(["cursor", str(BASE_DIR)], cwd=str(BASE_DIR), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return "已開啟 Cursor，正在載入專案。"
        except FileNotFoundError:
            try:
                os.startfile(str(BASE_DIR))
                return "已開啟專案資料夾。"
            except Exception as e:
                return f"開啟失敗: {e}"
        except Exception as e:
            return f"開啟失敗: {e}"
    if open_kw and ("gemini" in lower or "ai studio" in lower):
        try:
            import webbrowser
            webbrowser.open("https://aistudio.google.com/")
            return "已開啟 Google AI Studio (Gemini)。"
        except Exception as e:
            return f"開啟失敗: {e}"
    return None


def ask_brain(prompt: str, base_url: str = "", model: str = "gemma3:4b") -> str:
    """呼叫 AI 大腦"""
    try:
        from ai_providers import ask_sync
        out, _ = ask_sync(prompt, images=None)
        if out and "連線失敗" not in out:
            return out.strip()
    except Exception:
        pass
    base_url = base_url or os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    try:
        r = requests.post(
            f"{base_url.rstrip('/')}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=OLLAMA_TIMEOUT,
        )
        if r.status_code == 200:
            return r.json().get("response", "").strip() or "【大腦無回覆】"
        return f"【錯誤】HTTP {r.status_code}"
    except Exception as e:
        return f"【異常】{e}"


def run_agent(user_msg: str, user_id: str = "default") -> str:
    """執行 Agent"""
    try:
        from agent import run_agent_sync
        result, _ = run_agent_sync(user_msg, on_step=None, user_id=user_id)
        return result or "【Agent 無回覆】"
    except Exception as e:
        return f"【Agent 錯誤】{e}"


def call_local_strategist(demand: str, failed_code: str, error: str) -> str | None:
    """
    本地軍師：用免費 AI（Ollama/Groq/Gemini 等）依錯誤訊息修正代碼。
    零花費、不求助外部付費軍師。自動注入知識庫中相關修正經驗。
    """
    ctx = ""
    try:
        from brain_knowledge import search
        q = f"{demand} {error[:100]}"
        ctx = search(q, limit=2)
        if ctx:
            ctx = ctx + "\n\n---\n\n"
    except Exception:
        pass
    prompt = f"""{ctx}任務：{demand}
失敗代碼：
```
{failed_code[:2000]}
```
執行錯誤：
```
{error[:800]}
```
請直接輸出修正後的完整可執行 Python 代碼，僅代碼、無解釋、無 markdown。"""
    try:
        from ai_providers import ask_sync
        out, _ = ask_sync(prompt, images=None, ensemble=False)
        if out and "連線失敗" not in out:
            code = out.strip().removeprefix("```python").removeprefix("```").removesuffix("```").strip()
            return code if len(code) > 10 else None
    except Exception:
        pass
    try:
        r = requests.post(
            f"{os.environ.get('OLLAMA_BASE_URL', 'http://127.0.0.1:11434')}/api/generate",
            json={
                "model": os.environ.get("OLLAMA_MODEL", "gemma3:4b"),
                "prompt": f"修正以下 Python 錯誤，只輸出完整可執行代碼：\n任務:{demand}\n代碼:\n{failed_code[:1500]}\n錯誤:{error[:400]}",
                "stream": False,
            },
            timeout=OLLAMA_TIMEOUT,
        )
        if r.status_code == 200:
            t = r.json().get("response", "").strip().removeprefix("```python").removeprefix("```").removesuffix("```").strip()
            return t if len(t) > 10 else None
    except Exception:
        pass
    return None


def call_premium_diagnosis(prompt: str, user_id: str = "") -> str | None:
    """GPT 高階診斷：產出文字修正步驟，用於 AI 視覺等"""
    if not _is_premium_authorized(user_id):
        return None
    key = STRATEGIST_CONFIG.get("api_key", "").strip()
    if not key or key.startswith("your-"):
        return None
    try:
        r = requests.post(
            STRATEGIST_CONFIG.get("endpoint", "https://api.openai.com/v1/chat/completions"),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o",
                "messages": [
                    {"role": "system", "content": "你是築未科技軍師。根據錯誤給出 1～3 條具體修正步驟，若缺套件請明確寫出 pip install 套件名。僅輸出步驟文字。"},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=60,
        )
        if r.status_code != 200:
            return None
        content = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        return content.strip() if content else None
    except Exception:
        return None


def call_premium_strategist(demand: str, failed_code: str, error: str, user_id: str = "") -> str | None:
    """付費軍師：USE_PREMIUM_STRATEGIST=1 或用戶已授權啟用GPT"""
    if not USE_PREMIUM_STRATEGIST and not _is_premium_authorized(user_id):
        return None
    key = STRATEGIST_CONFIG.get("api_key", "").strip()
    if not key or key.startswith("your-"):
        return None
    try:
        r = requests.post(
            STRATEGIST_CONFIG.get("endpoint", "https://api.openai.com/v1/chat/completions"),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o",
                "messages": [
                    {"role": "system", "content": "你是築未科技軍師。只產出可執行的 Python 代碼，無解釋。"},
                    {"role": "user", "content": f"任務：{demand}\n\n失敗代碼：\n{failed_code}\n\nstderr：\n{error}\n\n請直接輸出修正後的完整 Python 代碼。"},
                ],
            },
            timeout=60,
        )
        if r.status_code != 200:
            return None
        content = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        code = content.strip().removeprefix("```python").removeprefix("```").removesuffix("```").strip()
        return code if code else None
    except Exception:
        return None


def call_local_ai_dev(prompt: str) -> str:
    """開發模式：本地 AI 產出代碼"""
    try:
        from ai_providers import ask_sync
        out, _ = ask_sync(f"產出可執行的 Python 代碼完成此任務，僅代碼無解釋：{prompt}", images=None, ensemble=False)
        if out and "連線失敗" not in out:
            return out.strip().removeprefix("```python").removeprefix("```").removesuffix("```").strip()
    except Exception:
        pass
    try:
        r = requests.post(
            f"{os.environ.get('OLLAMA_BASE_URL', 'http://127.0.0.1:11434')}/api/generate",
            json={"model": os.environ.get("OLLAMA_MODEL", "gemma3:4b"), "prompt": f"產出 Python 代碼：{prompt}", "stream": False},
            timeout=OLLAMA_TIMEOUT,
        )
        if r.status_code == 200:
            t = r.json().get("response", "").strip().removeprefix("```python").removeprefix("```").removesuffix("```").strip()
            return t or "# Local AI Offline"
    except Exception:
        pass
    return "# Local AI Offline"


def test_execution(code: str) -> tuple[bool, str]:
    """執行自檢"""
    try:
        DEV_OUTPUT.write_text(code, encoding="utf-8")
        res = subprocess.run([sys.executable, str(DEV_OUTPUT)], cwd=str(BASE_DIR), capture_output=True, text=True, timeout=30)
        return (res.returncode == 0, res.stderr or "")
    except subprocess.TimeoutExpired:
        return (False, "執行逾時")
    except Exception as e:
        return (False, str(e))


def process_message(content: str, user_id: str, base_url: str = "", model: str = "gemma3:4b") -> tuple[str, str]:
    """
    處理單一訊息，與 Discord 機器人邏輯一致。
    回傳 (結果, 類型) 類型: action|agent|brain|dev
    """
    content = (content or "").strip()
    if not content:
        return "請輸入內容。", "brain"

    # 【開發：】M2M 軍師協議
    if content.startswith("開發："):
        demand = content.replace("開發：", "").strip()
        code = call_local_ai_dev(demand)
        success, error_msg = test_execution(code)
        if success:
            try:
                from brain_self_learner import learn_from_dev_success
                learn_from_dev_success(demand, code)
            except Exception:
                pass
            return "✅ 本地系統已全權執行成功。", "dev"
        # 優先本地軍師（免費）：用 Ollama/Groq/Gemini 依錯誤修正
        fixed = call_local_strategist(demand, code, error_msg)
        if fixed:
            success2, err2 = test_execution(fixed)
            if success2:
                try:
                    from brain_self_learner import learn_from_dev_success
                    learn_from_dev_success(demand, fixed)
                except Exception:
                    pass
                return "✅ 本地軍師已修正，執行成功。", "dev"
            # 本地修正仍失敗，再試一次（帶新錯誤）
            fixed2 = call_local_strategist(demand, fixed, err2)
            if fixed2:
                success3, err3 = test_execution(fixed2)
                if success3:
                    try:
                        from brain_self_learner import learn_from_dev_success
                        learn_from_dev_success(demand, fixed2)
                    except Exception:
                        pass
                    return "✅ 本地軍師已修正，執行成功。", "dev"
                try:
                    from brain_self_learner import learn_from_dev_failure
                    learn_from_dev_failure(demand, err3)
                except Exception:
                    pass
                return f"本地軍師修正後仍失敗：\n{err3[:500]}\n\n若需 GPT 高階軍師，請回覆「啟用GPT」取得授權後再試。", "dev"
        fixed = call_premium_strategist(demand, code, error_msg, user_id)
        if fixed:
            success2, err2 = test_execution(fixed)
            if success2:
                try:
                    from brain_self_learner import learn_from_dev_success
                    learn_from_dev_success(demand, fixed)
                except Exception:
                    pass
                return "🔮 付費軍師已重構，執行成功。", "dev"
            try:
                from brain_self_learner import learn_from_dev_failure
                learn_from_dev_failure(demand, err2)
            except Exception:
                pass
            return f"付費軍師重構後仍失敗：\n{err2[:500]}", "dev"
        try:
            from brain_self_learner import learn_from_dev_failure
            learn_from_dev_failure(demand, error_msg)
        except Exception:
            pass
        return f"本地軍師無法修正（可用 Groq/Gemini 提升能力）\n{error_msg[:500]}\n\n若需 GPT 高階軍師，請回覆「啟用GPT」取得授權後再試。", "dev"

    # 授權、開啟指令
    action_result = handle_action(user_id, content)
    if action_result is not None:
        return action_result, "action"

    # Agent 模式（寫程式/部署）
    if _can_control(user_id) and is_agent_task(content):
        result = run_agent(content, user_id)
        return result, "agent"

    # 一般 AI 對話
    prompt = build_prompt(content)
    result = ask_brain(prompt, base_url, model)
    return result, "brain"
