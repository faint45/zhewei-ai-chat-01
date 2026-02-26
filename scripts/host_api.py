#!/usr/bin/env python3
"""
主機端輕量 API — 提供截圖、系統資訊、電腦控制等功能。
運行在 Windows 主機上（非 Docker），供 brain_server 代理呼叫。
預設 port: 8010
"""
import base64
import io
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

app = FastAPI(title="Jarvis Host API", docs_url="/docs")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports" / "screenshots"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/health")
def health():
    return {"ok": True, "host": platform.node(), "time": datetime.now().isoformat()}


@app.get("/screenshot")
def screenshot(format: str = Query("base64", enum=["base64", "file", "png"])):
    """截取整個螢幕，回傳 base64 或直接 PNG。"""
    try:
        import pyautogui
        img = pyautogui.screenshot()
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"截圖失敗: {e}"}, status_code=500)

    if format == "png":
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return Response(content=buf.read(), media_type="image/png")

    # Save to file
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = REPORTS_DIR / f"screen_{ts}.png"
    img.save(str(filepath))

    if format == "file":
        return {"ok": True, "path": str(filepath), "size": filepath.stat().st_size}

    # base64
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return {"ok": True, "image": b64, "path": str(filepath), "width": img.width, "height": img.height}


@app.get("/screenshot/region")
def screenshot_region(x: int = 0, y: int = 0, w: int = 800, h: int = 600):
    """截取指定區域。"""
    try:
        import pyautogui
        img = pyautogui.screenshot(region=(x, y, w, h))
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return {"ok": True, "image": b64, "width": img.width, "height": img.height}


@app.get("/sysinfo")
def sysinfo():
    """取得系統資訊：CPU、記憶體、磁碟、GPU。"""
    info = {
        "hostname": platform.node(),
        "os": f"{platform.system()} {platform.release()} ({platform.version()})",
        "arch": platform.machine(),
        "python": platform.python_version(),
        "cpu": platform.processor(),
        "time": datetime.now().isoformat(),
    }

    try:
        import psutil
        mem = psutil.virtual_memory()
        info["memory"] = {
            "total_gb": round(mem.total / 1e9, 1),
            "used_gb": round(mem.used / 1e9, 1),
            "percent": mem.percent,
        }
        info["cpu_percent"] = psutil.cpu_percent(interval=0.5)
        info["cpu_count"] = psutil.cpu_count()
        disks = []
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
                disks.append({
                    "mount": part.mountpoint,
                    "total_gb": round(usage.total / 1e9, 1),
                    "used_gb": round(usage.used / 1e9, 1),
                    "percent": usage.percent,
                })
            except Exception:
                pass
        info["disks"] = disks
        # Top processes
        procs = []
        for p in sorted(psutil.process_iter(["pid", "name", "memory_percent", "cpu_percent"]),
                        key=lambda x: x.info.get("memory_percent") or 0, reverse=True)[:10]:
            procs.append({
                "pid": p.info["pid"],
                "name": p.info["name"],
                "mem%": round(p.info.get("memory_percent") or 0, 1),
                "cpu%": round(p.info.get("cpu_percent") or 0, 1),
            })
        info["top_processes"] = procs
    except ImportError:
        info["warning"] = "psutil not installed"

    # GPU info via nvidia-smi
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if r.returncode == 0:
            gpus = []
            for line in r.stdout.strip().split("\n"):
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 6:
                    gpus.append({
                        "name": parts[0],
                        "vram_total_mb": int(parts[1]),
                        "vram_used_mb": int(parts[2]),
                        "vram_free_mb": int(parts[3]),
                        "gpu_util%": int(parts[4]),
                        "temp_c": int(parts[5]),
                    })
            info["gpus"] = gpus
    except Exception:
        pass

    return info


@app.get("/processes")
def processes(top: int = 20):
    """列出 top N 記憶體使用量最高的程序。"""
    try:
        import psutil
        procs = []
        for p in sorted(psutil.process_iter(["pid", "name", "memory_percent", "status"]),
                        key=lambda x: x.info.get("memory_percent") or 0, reverse=True)[:top]:
            procs.append(p.info)
        return {"ok": True, "processes": procs}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/windows")
def list_windows():
    """列出所有可見視窗。"""
    try:
        import pyautogui
        import pygetwindow as gw
        wins = []
        for w in gw.getAllWindows():
            if w.title and w.visible and w.width > 50 and w.height > 50:
                wins.append({
                    "title": w.title[:100],
                    "x": w.left, "y": w.top,
                    "w": w.width, "h": w.height,
                    "active": w.isActive,
                })
        return {"ok": True, "windows": wins}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/execute")
def execute_command(request_body: dict = {}):
    """
    執行命令或開啟軟體。
    {
        "command": "notepad" 或 "dir C:\\" 或 "python -c 'print(1)'",
        "type": "app|cmd|python|shell",
        "timeout": 30
    }
    """
    import subprocess
    command = request_body.get("command", "").strip()
    cmd_type = request_body.get("type", "shell")
    timeout = int(request_body.get("timeout", 30))

    if not command:
        return {"ok": False, "error": "command is required"}

    DENY_COMMANDS = ["format", "del /f", "rd /s", "shutdown", "reboot", "deltree"]
    for deny in DENY_COMMANDS:
        if deny.lower() in command.lower():
            return {"ok": False, "error": f"blocked dangerous command: {deny}"}

    try:
        if cmd_type == "app":
            import os
            os.startfile(command)
            return {"ok": True, "action": "opened", "target": command}
        else:
            shell = cmd_type in ["cmd", "shell"]
            result = subprocess.run(
                command,
                shell=shell,
                capture_output=True,
                text=True,
                timeout=min(timeout, 120)
            )
            return {
                "ok": True,
                "command": command,
                "stdout": result.stdout[:5000],
                "stderr": result.stderr[:1000],
                "returncode": result.returncode
            }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "command timed out"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/search")
def search_files(request_body: dict = {}):
    """
    搜尋檔案。
    {
        "path": "C:\\Users",
        "pattern": "*.py",
        "recursive": true
    }
    """
    import subprocess
    path = request_body.get("path", "C:\\Users")
    pattern = request_body.get("pattern", "*")
    recursive = request_body.get("recursive", True)

    cmd = f'dir /b "{path}\\{pattern}"' if not recursive else f'dir /s /b "{path}\\{pattern}"'
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        files = [f.strip() for f in result.stdout.splitlines() if f.strip()][:100]
        return {"ok": True, "path": path, "pattern": pattern, "files": files, "count": len(files)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/open_terminal")
def open_terminal(request_body: dict = {}):
    """
    開啟終端機。
    {
        "type": "cmd|powershell|wt",
        "command": "dir"  (可選，開啟後自動執行的命令)
    }
    """
    import subprocess
    term_type = request_body.get("type", "cmd")
    init_cmd = request_body.get("command", "")

    try:
        if term_type == "wt" or term_type == "windows_terminal":
            cmd = 'wt.exe'
            if init_cmd:
                cmd += f' -d . && {init_cmd}'
            subprocess.Popen(cmd, shell=True)
        elif term_type == "powershell":
            cmd = 'powershell.exe'
            if init_cmd:
                cmd += f' -Command \\"{init_cmd}\\"'
            subprocess.Popen(cmd, shell=True)
        else:
            cmd = 'cmd.exe'
            if init_cmd:
                cmd += f' /c {init_cmd}'
            subprocess.Popen(cmd, shell=True)
        return {"ok": True, "action": "opened terminal", "type": term_type, "command": init_cmd}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/keystroke")
def send_keystroke(request_body: dict = {}):
    """
    傳送鍵盤輸入。
    {
        "text": "hello world",
        "keys": ["ctrl", "c"] 或 ["win", "r"]
    }
    """
    import pyautogui
    text = request_body.get("text", "")
    keys = request_body.get("keys", [])

    try:
        if text:
            pyautogui.write(text, interval=0.02)
        if keys:
            pyautogui.hotkey(*[str(k) for k in keys])
        return {"ok": True, "action": "keystrokes sent"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/mouse")
def mouse_action(request_body: dict = {}):
    """
    滑鼠操作。
    {
        "action": "move|click|right_click|double_click",
        "x": 100,
        "y": 200
    }
    """
    import pyautogui
    action = request_body.get("action", "move")
    x = int(request_body.get("x", 0))
    y = int(request_body.get("y", 0))

    try:
        if action == "move":
            pyautogui.moveTo(x, y, duration=0.1)
        elif action == "click":
            pyautogui.click(x, y)
        elif action == "right_click":
            pyautogui.rightClick(x, y)
        elif action == "double_click":
            pyautogui.doubleClick(x, y)
        else:
            return {"ok": False, "error": f"unknown action: {action}"}
        return {"ok": True, "action": action, "x": x, "y": y}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── 預留：本地模型接入介面 ──────────────────────────────────
# 後續開發可在此區塊擴充本地 LLM / Embedding / TTS / STT 等功能
# 請勿修改上方已穩定的截圖、系統資訊、視窗等端點

OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")


@app.post("/api/local/chat")
def local_chat(request_body: dict = {}):
    """預留：轉發到本地 Ollama 進行對話推理。"""
    import urllib.request
    model = request_body.get("model", "zhewei-brain")
    messages = request_body.get("messages", [])
    payload = json.dumps({"model": model, "messages": messages, "stream": False}).encode()
    try:
        req = urllib.request.Request(
            f"{OLLAMA_BASE}/api/chat", data=payload,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
            return {"ok": True, "message": data.get("message", {}), "model": model}
    except Exception as e:
        return {"ok": False, "error": str(e), "hint": "請確認 Ollama 正在運行"}


@app.post("/api/local/embed")
def local_embed(request_body: dict = {}):
    """預留：本地 Embedding 向量生成。"""
    import urllib.request
    model = request_body.get("model", "nomic-embed-text")
    text = request_body.get("text", "")
    payload = json.dumps({"model": model, "prompt": text}).encode()
    try:
        req = urllib.request.Request(
            f"{OLLAMA_BASE}/api/embeddings", data=payload,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            return {"ok": True, "embedding": data.get("embedding", []), "model": model}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/local/models")
def local_models():
    """預留：列出本地可用模型。"""
    import urllib.request
    try:
        req = urllib.request.Request(f"{OLLAMA_BASE}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            models = [m.get("name", "") for m in data.get("models", [])]
            return {"ok": True, "models": models}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── 預留結束 ────────────────────────────────────────────────

VERSION = "1.0.0"


@app.get("/version")
def version():
    return {"version": VERSION, "name": "Jarvis Host API", "build": "exe" if getattr(sys, 'frozen', False) else "source"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("HOST_API_PORT", "8010"))
    print(f"=== Jarvis Host API v{VERSION} starting on port {port} ===")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
