# -*- coding: utf-8 -*-
"""
築未科技 — 手機代理人模組（DroidRun + Ollama 本地控制）
透過 ADB over WiFi 連接 Android 手機，用本地 LLM 驅動操作。

功能：
  - 連接/斷開 Android 設備
  - 截圖分析（Ollama 視覺模型）
  - 自然語言指令控制手機
  - LINE 訊息讀取/回覆
  - 任意 App 自動化操作

依賴：pip install droidrun adbutils Pillow httpx
硬體：Android 11+ 手機，開啟 WiFi ADB

環境變數：
  PHONE_ADB_HOST     — 手機 IP (預設 192.168.1.100)
  PHONE_ADB_PORT     — ADB 端口 (預設 5555)
  PHONE_OLLAMA_MODEL — 控制用模型 (預設 qwen3:32b)
  PHONE_VISION_MODEL — 視覺模型 (預設 moondream)
"""
import asyncio
import base64
import json
import logging
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

log = logging.getLogger("phone_agent")

# ===== 設定 =====
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11460")
PHONE_ADB_HOST = os.environ.get("PHONE_ADB_HOST", "192.168.1.100")
PHONE_ADB_PORT = os.environ.get("PHONE_ADB_PORT", "5555")
PHONE_OLLAMA_MODEL = os.environ.get("PHONE_OLLAMA_MODEL", "qwen3:32b")
PHONE_VISION_MODEL = os.environ.get("PHONE_VISION_MODEL", "moondream")
SCREENSHOT_DIR = Path(__file__).parent / "phone_agent_data" / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


# ===== ADB 底層操作 =====

class ADBController:
    """ADB 設備控制器 — 透過 adb 命令行操作手機"""

    def __init__(self, host: str = "", port: str = ""):
        self.host = host or PHONE_ADB_HOST
        self.port = port or PHONE_ADB_PORT
        self.device_id = f"{self.host}:{self.port}"
        self._connected = False

    def _adb(self, *args, timeout=30):
        """執行 ADB 命令"""
        cmd = ["adb", "-s", self.device_id] + list(args)
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            output = r.stdout.strip()
            if r.returncode != 0:
                err = r.stderr.strip()
                return False, err or output
            return True, output
        except FileNotFoundError:
            return False, "ADB 未安裝。請安裝 Android SDK Platform Tools。"
        except subprocess.TimeoutExpired:
            return False, f"ADB 命令超時 ({timeout}s)"
        except Exception as e:
            return False, str(e)

    def connect(self):
        """連接設備（WiFi ADB）"""
        ok, out = self._adb("connect", self.device_id)
        if ok and ("connected" in out.lower() or "already" in out.lower()):
            self._connected = True
            log.info(f"📱 已連接: {self.device_id}")
            return {"success": True, "message": f"已連接 {self.device_id}", "output": out}
        return {"success": False, "message": f"連接失敗: {out}"}

    def disconnect(self):
        """斷開設備"""
        self._adb("disconnect", self.device_id)
        self._connected = False
        return {"success": True, "message": f"已斷開 {self.device_id}"}

    def is_connected(self):
        """檢查連線狀態"""
        ok, out = self._adb("get-state")
        self._connected = ok and "device" in out
        return self._connected

    def screenshot(self, local_path=""):
        """截圖並拉回本地"""
        if not local_path:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            local_path = str(SCREENSHOT_DIR / f"screen_{ts}.png")

        remote = "/sdcard/screenshot_tmp.png"
        ok1, out1 = self._adb("shell", "screencap", "-p", remote)
        if not ok1:
            return {"success": False, "message": f"截圖失敗: {out1}"}

        ok2, out2 = self._adb("pull", remote, local_path)
        self._adb("shell", "rm", remote)
        if not ok2:
            return {"success": False, "message": f"拉取失敗: {out2}"}

        return {"success": True, "path": local_path, "message": "截圖完成"}

    def tap(self, x, y):
        """點擊螢幕座標"""
        ok, out = self._adb("shell", "input", "tap", str(x), str(y))
        return {"success": ok, "message": f"tap({x},{y})" if ok else out}

    def swipe(self, x1, y1, x2, y2, duration_ms=300):
        """滑動"""
        ok, out = self._adb("shell", "input", "swipe",
                            str(x1), str(y1), str(x2), str(y2), str(duration_ms))
        return {"success": ok, "message": f"swipe({x1},{y1}->{x2},{y2})" if ok else out}

    def input_text(self, text):
        """輸入文字（英文直接打，中文用廣播）"""
        if all(ord(c) < 128 for c in text):
            escaped = text.replace(" ", "%s").replace("'", "\\'")
            ok, out = self._adb("shell", "input", "text", escaped)
        else:
            ok, out = self._adb("shell", "am", "broadcast",
                                "-a", "ADB_INPUT_TEXT",
                                "--es", "msg", text)
            if not ok:
                ok, out = self._adb("shell", "input", "text",
                                    text.encode("unicode_escape").decode("ascii"))
        return {"success": ok, "message": f"輸入: {text[:30]}..." if ok else out}

    def press_key(self, key):
        """按鍵（BACK, HOME, ENTER 等）"""
        key_map = {
            "back": "4", "home": "3", "enter": "66", "recent": "187",
            "power": "26", "volume_up": "24", "volume_down": "25",
            "tab": "61", "delete": "67", "menu": "82",
        }
        keycode = key_map.get(key.lower(), key)
        ok, out = self._adb("shell", "input", "keyevent", keycode)
        return {"success": ok, "message": f"按鍵: {key}" if ok else out}

    def open_app(self, package):
        """啟動 App"""
        ok, out = self._adb("shell", "monkey", "-p", package,
                            "-c", "android.intent.category.LAUNCHER", "1")
        return {"success": ok, "message": f"啟動: {package}" if ok else out}

    def current_app(self):
        """取得當前 App"""
        ok, out = self._adb("shell", "dumpsys", "window", "|", "grep", "mCurrentFocus")
        return {"success": ok, "current": out}

    def get_screen_xml(self):
        """取得 UI 樹（accessibility dump）"""
        remote = "/sdcard/ui_dump.xml"
        ok1, _ = self._adb("shell", "uiautomator", "dump", remote)
        if not ok1:
            return {"success": False, "message": "UI dump 失敗"}
        ok2, xml = self._adb("shell", "cat", remote)
        self._adb("shell", "rm", remote)
        return {"success": ok2, "xml": xml if ok2 else ""}


# ===== 常用 App 包名 =====

APP_PACKAGES = {
    "line": "jp.naver.line.android",
    "chrome": "com.android.chrome",
    "camera": "com.android.camera",
    "settings": "com.android.settings",
    "files": "com.google.android.apps.nbu.files",
    "maps": "com.google.android.apps.maps",
    "youtube": "com.google.android.youtube",
    "facebook": "com.facebook.katana",
    "messenger": "com.facebook.orca",
    "wechat": "com.tencent.mm",
    "telegram": "org.telegram.messenger",
    "whatsapp": "com.whatsapp",
}


# ===== Ollama 視覺分析 =====

def _ollama_vision(image_path, prompt="描述這個手機螢幕截圖的內容"):
    """用 Ollama 視覺模型分析截圖"""
    try:
        import httpx
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")

        payload = {
            "model": PHONE_VISION_MODEL,
            "prompt": prompt,
            "images": [img_b64],
            "stream": False,
        }
        r = httpx.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=60)
        r.raise_for_status()
        return r.json().get("response", "")
    except Exception as e:
        log.error(f"視覺分析失敗: {e}")
        return f"[視覺分析錯誤] {e}"


def _ollama_think(prompt, system=""):
    """用 Ollama 文字模型思考下一步"""
    try:
        import httpx
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": PHONE_OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": 2048},
        }
        r = httpx.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload, timeout=120)
        r.raise_for_status()
        return r.json().get("message", {}).get("content", "")
    except Exception as e:
        log.error(f"LLM 思考失敗: {e}")
        return f"[LLM 錯誤] {e}"


# ===== 手機代理人 =====

class PhoneAgent:
    """
    AI 手機代理人 — 截圖觀察 → LLM 思考 → ADB 執行

    循環：截圖 → 視覺描述 → LLM 規劃 → 執行動作 → 重複至完成
    """

    SYSTEM_PROMPT = (
        "你是手機操作 AI 助手。你能看到手機螢幕截圖的描述，並決定下一步操作。\n\n"
        "可用動作（每次只回傳一個 JSON）：\n"
        '- {"action": "tap", "x": 500, "y": 800, "reason": "點擊某按鈕"}\n'
        '- {"action": "swipe", "x1": 500, "y1": 1500, "x2": 500, "y2": 500, "reason": "向上滑動"}\n'
        '- {"action": "input_text", "text": "要輸入的文字", "reason": "在輸入框打字"}\n'
        '- {"action": "press_key", "key": "back|home|enter|recent", "reason": "按返回鍵"}\n'
        '- {"action": "open_app", "app": "line|chrome|camera", "reason": "開啟 App"}\n'
        '- {"action": "wait", "seconds": 2, "reason": "等待頁面載入"}\n'
        '- {"action": "done", "result": "任務完成的描述", "reason": "任務已完成"}\n'
        '- {"action": "failed", "result": "失敗原因", "reason": "無法完成"}\n\n'
        "規則：\n"
        "1. 每次只回傳一個 JSON 動作\n"
        "2. 只回傳 JSON，不要其他文字\n"
        "3. 仔細觀察螢幕描述再決定動作\n"
        "4. LINE 回覆：先點對話 → 點輸入框 → 輸入文字 → 按發送\n"
        "5. 最多執行 20 步，超過則回報 failed"
    )

    def __init__(self, adb=None):
        self.adb = adb or ADBController()
        self.max_steps = 20
        self.history = []

    async def execute_task(self, task, callback=None):
        """執行自然語言任務"""
        if not self.adb.is_connected():
            conn = self.adb.connect()
            if not conn["success"]:
                return {"success": False, "steps": 0,
                        "result": f"無法連接手機: {conn['message']}", "history": []}

        self.history = []

        for step in range(self.max_steps):
            step_info = {"step": step + 1, "action": None, "screenshot": None}

            # 1. 截圖
            sc = self.adb.screenshot()
            if not sc["success"]:
                step_info["error"] = sc["message"]
                self.history.append(step_info)
                continue
            step_info["screenshot"] = sc["path"]

            # 2. 視覺分析
            screen_desc = _ollama_vision(
                sc["path"],
                "請詳細描述這個 Android 手機螢幕截圖：包含哪些按鈕/文字/輸入框/對話內容。用中文回答。"
            )
            step_info["screen_description"] = screen_desc[:500]

            # 3. LLM 規劃
            history_text = ""
            if self.history:
                recent = self.history[-5:]
                history_text = "\n".join([
                    f"步驟{h['step']}: {json.dumps(h.get('action', {}), ensure_ascii=False)}"
                    for h in recent
                ])

            prompt = (
                f"任務：{task}\n\n"
                f"當前螢幕畫面：\n{screen_desc}\n\n"
                + (f"已執行步驟：\n{history_text}\n\n" if history_text else "這是第一步。\n\n")
                + "請決定下一個動作（只回傳 JSON）："
            )

            llm_response = _ollama_think(prompt, self.SYSTEM_PROMPT)

            # 4. 解析動作
            action = self._parse_action(llm_response)
            step_info["action"] = action

            if callback:
                await callback(step_info)

            # 5. 完成/失敗判斷
            if action.get("action") == "done":
                self.history.append(step_info)
                return {"success": True, "steps": step + 1,
                        "result": action.get("result", "任務完成"), "history": self.history}

            if action.get("action") == "failed":
                self.history.append(step_info)
                return {"success": False, "steps": step + 1,
                        "result": action.get("result", "任務失敗"), "history": self.history}

            # 6. 執行動作
            exec_result = self._execute_action(action)
            step_info["exec_result"] = exec_result
            self.history.append(step_info)

            wait_time = action.get("seconds", 1) if action.get("action") == "wait" else 1
            await asyncio.sleep(wait_time)

        return {"success": False, "steps": self.max_steps,
                "result": "超過最大步數限制", "history": self.history}

    def _parse_action(self, llm_response):
        """從 LLM 回應中解析 JSON 動作"""
        import re
        json_match = re.search(r'\{[^{}]*\}', llm_response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return {"action": "failed", "result": f"無法解析 LLM 回應: {llm_response[:100]}"}

    def _execute_action(self, action):
        """執行 ADB 動作"""
        act = action.get("action", "")
        if act == "tap":
            return self.adb.tap(int(action.get("x", 0)), int(action.get("y", 0)))
        elif act == "swipe":
            return self.adb.swipe(
                int(action.get("x1", 0)), int(action.get("y1", 0)),
                int(action.get("x2", 0)), int(action.get("y2", 0)))
        elif act == "input_text":
            return self.adb.input_text(action.get("text", ""))
        elif act == "press_key":
            return self.adb.press_key(action.get("key", "back"))
        elif act == "open_app":
            app = action.get("app", "")
            package = APP_PACKAGES.get(app, app)
            return self.adb.open_app(package)
        elif act == "wait":
            return {"success": True, "message": f"等待 {action.get('seconds', 1)}s"}
        return {"success": False, "message": f"未知動作: {act}"}


# ===== 快捷功能 =====

def phone_connect(host="", port=""):
    """連接手機"""
    return ADBController(host, port).connect()

def phone_disconnect(host="", port=""):
    """斷開手機"""
    return ADBController(host, port).disconnect()

def phone_screenshot(host="", port=""):
    """手機截圖 + AI 分析"""
    adb = ADBController(host, port)
    if not adb.is_connected():
        adb.connect()
    sc = adb.screenshot()
    if sc["success"]:
        sc["description"] = _ollama_vision(sc["path"])
    return sc

def phone_task(task, host="", port=""):
    """執行手機任務（同步包裝）"""
    adb = ADBController(host, port)
    agent = PhoneAgent(adb)
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(agent.execute_task(task))
    finally:
        loop.close()

async def phone_task_async(task, host="", port="", callback=None):
    """執行手機任務（異步版，供 FastAPI 呼叫）"""
    adb = ADBController(host, port)
    agent = PhoneAgent(adb)
    return await agent.execute_task(task, callback)


# ===== LINE 專用快捷 =====

def line_reply(message, contact=""):
    """LINE 回覆訊息"""
    if contact:
        task = f"打開 LINE，找到「{contact}」的對話，回覆：{message}"
    else:
        task = f"打開 LINE，在最新的對話中回覆：{message}"
    return phone_task(task)

def line_read_latest():
    """讀取 LINE 最新訊息"""
    adb = ADBController()
    if not adb.is_connected():
        adb.connect()
    adb.open_app(APP_PACKAGES["line"])
    time.sleep(3)
    sc = adb.screenshot()
    if sc["success"]:
        desc = _ollama_vision(
            sc["path"],
            "請詳細列出這個 LINE 畫面中所有對話和訊息內容，包括發送者和時間。用中文回答。")
        return {"success": True, "messages": desc, "screenshot": sc["path"]}
    return {"success": False, "message": "截圖失敗"}


# ===== DroidRun 進階模式（選裝）=====

def droidrun_available():
    """檢查 DroidRun 是否已安裝"""
    try:
        import droidrun  # noqa: F401
        return True
    except ImportError:
        return False

async def droidrun_task(task, device_id=""):
    """使用 DroidRun 框架執行任務（需 pip install droidrun）"""
    if not droidrun_available():
        return {"success": False, "message": "DroidRun 未安裝。請執行: pip install droidrun"}
    try:
        from droidrun.agent.react_agent import ReActAgent
        from droidrun.agent.llm_config import LLMConfig

        config = LLMConfig(
            provider="ollama",
            model=PHONE_OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
        )
        device = device_id or f"{PHONE_ADB_HOST}:{PHONE_ADB_PORT}"
        agent = ReActAgent(config=config, device_id=device)
        result = await agent.run(task)
        return {"success": True, "result": str(result)}
    except Exception as e:
        log.error(f"DroidRun 執行失敗: {e}")
        return {"success": False, "message": str(e)}