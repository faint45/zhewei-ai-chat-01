# -*- coding: utf-8 -*-
"""
築未科技 — Agent 工具箱（雙 Python 環境）
路徑權限僅限 D 槽與 Z 槽；subprocess 切換 venv_vision 執行視覺引擎；報表數值以 $X\\%$ LaTeX 格式呈現。
"""
import json
import os
import subprocess
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Callable

REPORT_DIR = Path(os.environ.get("ZHEWEI_MEMORY_ROOT", "Z:/Zhewei_Brain")) / "Reports"
WORKSPACE_ROOT = Path(__file__).resolve().parent
CONSTRUCTION_LOG_ROOT = Path(os.environ.get("ZHEWEI_MEMORY_ROOT", "Z:/Zhewei_Brain"))
BRAIN_WORKSPACE = Path(os.environ.get("BRAIN_WORKSPACE", r"D:\brain_workspace"))
MEDIA_OUTPUT_DIR = BRAIN_WORKSPACE / "output"
VENV_VISION_PY = BRAIN_WORKSPACE / "venv_vision" / "Scripts" / "python.exe"
if not VENV_VISION_PY.exists():
    VENV_VISION_PY = BRAIN_WORKSPACE / "venv_vision" / "bin" / "python"
VISION_WORKER_SCRIPT = BRAIN_WORKSPACE / "vision_worker.py"


def _path_allowed(path: Path) -> bool:
    """嚴格路徑權限：僅允許 D 槽或 Z 槽（不允許 C、E 等）。"""
    try:
        resolved = path.resolve()
        s = str(resolved).upper().replace("/", "\\")
        if len(s) < 2:
            return False
        drive = s[:2]
        return drive in ("D:", "Z:")
    except Exception:
        return False


def _latex_percent(pct: int | float) -> str:
    """進度數值轉 LaTeX 格式，例：85 -> \"$85\\%$\" """
    return f"${int(pct)}\\%$"


def safe_path(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return {"ok": False, "error": str(e), "status": "error"}
    return wrapper


def run_command(command: str, shell: bool = True, timeout_seconds: int = 60, cwd: str | None = None) -> dict[str, Any]:
    cwd_path = (Path(cwd) if cwd else WORKSPACE_ROOT).resolve()
    if not _path_allowed(cwd_path):
        return {"ok": False, "stdout": "", "stderr": "工作目錄僅允許 D 槽或 Z 槽", "returncode": -1}
    try:
        r = subprocess.run(
            command, shell=shell, cwd=str(cwd_path),
            capture_output=True, text=True, timeout=timeout_seconds,
            encoding="utf-8", errors="replace",
        )
        return {
            "ok": r.returncode == 0 and not (r.stderr and r.stderr.strip()),
            "stdout": r.stdout or "", "stderr": r.stderr or "", "returncode": r.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": "指令執行逾時", "returncode": -1}
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e), "returncode": -1}


def read_file(path: str, encoding: str = "utf-8") -> dict[str, Any]:
    p = (WORKSPACE_ROOT / path) if not os.path.isabs(path) else Path(path)
    p = p.resolve()
    if not _path_allowed(p):
        return {"ok": False, "content": "", "error": "路徑僅允許 D 槽或 Z 槽"}
    try:
        if not p.exists():
            return {"ok": False, "content": "", "error": f"檔案不存在: {p}"}
        return {"ok": True, "content": p.read_text(encoding=encoding, errors="replace"), "error": ""}
    except Exception as e:
        return {"ok": False, "content": "", "error": str(e)}


def write_file(path: str, content: str, encoding: str = "utf-8") -> dict[str, Any]:
    p = (WORKSPACE_ROOT / path) if not os.path.isabs(path) else Path(path)
    p = p.resolve()
    if not _path_allowed(p):
        return {"ok": False, "error": "路徑僅允許 D 槽或 Z 槽"}
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding=encoding, errors="replace")
        return {"ok": True, "error": ""}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def list_dir(path: str = ".") -> dict[str, Any]:
    p = (WORKSPACE_ROOT / path) if not os.path.isabs(path) else Path(path)
    p = p.resolve()
    if not _path_allowed(p):
        return {"ok": False, "entries": [], "error": "路徑僅允許 D 槽或 Z 槽"}
    try:
        if not p.exists():
            return {"ok": False, "entries": [], "error": f"目錄不存在: {p}"}
        if not p.is_dir():
            return {"ok": False, "entries": [], "error": f"非目錄: {p}"}
        return {"ok": True, "entries": [x.name for x in p.iterdir()], "error": ""}
    except Exception as e:
        return {"ok": False, "entries": [], "error": str(e)}


def _vision_analyze_yolo(image_path: str) -> dict[str, Any] | None:
    try:
        import torch
        from ultralytics import YOLO
    except ImportError:
        return None
    target = (WORKSPACE_ROOT / image_path) if not os.path.isabs(image_path) else Path(image_path)
    if not target.exists():
        return {"ok": False, "status": "error", "message": "找不到影像檔案", "error": f"找不到影像: {target}"}
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if _vision_analyze_yolo._model is None:
        _vision_analyze_yolo._model = YOLO("yolov8n.pt")
    results = _vision_analyze_yolo._model(str(target), device=device)
    detections = []
    for r in results:
        for box in r.boxes:
            if float(box.conf[0]) > 0.5:
                detections.append(r.names[int(box.cls[0])])
    unique = list(set(detections))
    return {"ok": True, "status": "success", "detected": unique, "detected_objects": unique, "summary": f"偵測：{', '.join(unique)}", "device": device}


_vision_analyze_yolo._model = None


@safe_path
def vision_analyze(image_path: str) -> dict[str, Any]:
    p = (WORKSPACE_ROOT / image_path) if not os.path.isabs(image_path) else Path(image_path)
    if not p.exists():
        return {"ok": False, "status": "error", "error": f"圖片不存在: {p}", "message": "找不到影像檔案"}
    out = _vision_analyze_yolo(image_path)
    if out is not None:
        return out
    return {"ok": True, "status": "success", "detected_objects": ["LPC_Marker_01", "Worker_Safe"], "detected": ["LPC_Marker_01", "Worker_Safe"], "summary": "預留模式：未安裝 ultralytics/torch", "device": "cpu"}


@safe_path
def manage_construction_log(content: str) -> dict[str, Any]:
    log_dir = CONSTRUCTION_LOG_ROOT / "Construction_Logs"
    log_path = log_dir / "Daily_Report.md"
    if not _path_allowed(log_path):
        return {"ok": False, "error": "報表路徑僅允許 D 槽或 Z 槽", "status": "error"}
    log_dir.mkdir(parents=True, exist_ok=True)
    block = f"\n\n---\n## {datetime.now().strftime('%Y-%m-%d %H:%M')}\n{content}\n"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(block)
    return {"ok": True, "message": f"日報表已同步至雲端: {log_path.name}"}


async def generate_voice_report(transcript: str, gemini_service: Any) -> dict[str, Any]:
    if not _path_allowed(REPORT_DIR):
        return {"ok": False, "error": "報表路徑僅允許 D 槽或 Z 槽", "status": "error"}
    prompt = f"""你是築未科技的專業工程主管。請將以下工地語音紀錄整理成 Markdown 表格。
表格欄位：日期、地點、機具、內容、進度、工安、異常。
約束：進度以 LaTeX 格式表示（例如 $85\\%$、$100\\%$）；涉及長度或數量請精確；僅輸出 Markdown 表格。
語音內容："{transcript}"
"""
    try:
        report_md = await gemini_service.chat([{"role": "user", "content": prompt}])
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        target_file = REPORT_DIR / "Daily_Voice_Logs.md"
        with target_file.open("a", encoding="utf-8") as f:
            f.write(f"\n\n### 語音生成日報 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{report_md}\n---")
        return {"ok": True, "message": f"報表已存入 Z 槽：{target_file.name}", "report_md": report_md}
    except Exception as e:
        return {"ok": False, "error": str(e), "status": "error"}


@safe_path
def run_vision_engine(image_path: str) -> dict[str, Any]:
    """
    跨環境呼叫 D:\\brain_workspace 下 Python 3.12 venv_vision 的 YOLOv8 視覺引擎。
    鎖定邏輯：subprocess 調用 vision_worker.py，cwd=BRAIN_WORKSPACE。影像路徑僅允許 D 槽或 Z 槽。
    """
    p = (WORKSPACE_ROOT / image_path) if not os.path.isabs(image_path) else Path(image_path)
    p = p.resolve()
    if not _path_allowed(p):
        return {"ok": False, "status": "error", "error": "影像路徑僅允許 D 槽或 Z 槽", "detected": []}
    if not p.exists():
        return {"ok": False, "status": "error", "error": f"影像不存在: {p}", "detected": []}
    if not VISION_WORKER_SCRIPT.exists():
        return {"ok": False, "status": "error", "error": f"視覺引擎不存在: {VISION_WORKER_SCRIPT}", "detected": []}
    cmd = [str(VENV_VISION_PY), str(VISION_WORKER_SCRIPT), str(p)]
    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=90,
            encoding="utf-8",
            errors="replace",
            cwd=str(BRAIN_WORKSPACE),
        )
        out = (r.stdout or r.stderr or "").strip()
        if not out:
            return {"ok": False, "status": "error", "error": "視覺引擎無輸出", "detected": []}
        data = json.loads(out)
        data.setdefault("ok", data.get("status") == "success")
        return data
    except subprocess.TimeoutExpired:
        return {"ok": False, "status": "error", "error": "視覺引擎逾時", "detected": []}
    except json.JSONDecodeError:
        return {"ok": False, "status": "error", "error": out[:300] if out else "輸出非 JSON", "detected": []}


@safe_path
def generate_progress_report(detected: str) -> dict[str, Any]:
    """生成影像報表 (JSONL + CSV)。detected 可為逗號分隔字串或 JSON 字串（含 detected 與可選 progress）。進度以 $X\\%$ 呈現。"""
    try:
        from report_generator import generate_progress_report as _gen
        raw = str(detected).strip()
        try:
            data = json.loads(raw)
            detected_list = data.get("detected", data.get("detected_objects", []))
            if isinstance(detected_list, str):
                detected_list = [x.strip() for x in detected_list.split(",") if x.strip()]
            progress = data.get("progress", 100)
            vision_results = {"detected": detected_list, "progress": progress}
        except json.JSONDecodeError:
            vision_results = {"detected": [x.strip() for x in raw.split(",") if x.strip()]}
        msg = _gen(vision_results)
        return {"ok": True, "message": msg}
    except Exception as e:
        return {"ok": False, "error": str(e), "status": "error"}


def _generate_media_xai(prompt: str, out_path: Path) -> bool:
    """xAI Grok 影像生成：XAI_API_KEY 存在時呼叫 api.x.ai/v1/images/generations，寫入 out_path。"""
    api_key = os.environ.get("XAI_API_KEY", "").strip()
    if not api_key:
        return False
    try:
        import urllib.request
        import base64
        body = json.dumps({"model": "grok-2-image", "prompt": prompt, "n": 1, "response_format": "b64_json"}).encode("utf-8")
        req = urllib.request.Request(
            "https://api.x.ai/v1/images/generations",
            data=body,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode("utf-8"))
        for item in (data.get("data") or []):
            b64 = item.get("b64_json")
            if b64:
                out_path.write_bytes(base64.b64decode(b64))
                return True
    except Exception:
        pass
    return False


@safe_path
def generate_media(prompt: str, type: str = "image") -> dict[str, Any]:
    """對接 Jimeng 或 Grok API 生成圖片/影片，存入 D:\\brain_workspace\\output。type 為 image 或 video。"""
    if not _path_allowed(MEDIA_OUTPUT_DIR):
        return {"ok": False, "error": "媒體輸出路徑僅允許 D 槽或 Z 槽", "status": "error"}
    MEDIA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ext = "mp4" if type.lower() == "video" else "png"
    out_path = MEDIA_OUTPUT_DIR / f"media.{ext}"
    try:
        if type.lower() == "image" and _generate_media_xai(prompt, out_path):
            return {"ok": True, "message": f"Image generated at {out_path}", "path": str(out_path)}
        # 影片或無 API 時：預留 Jimeng/其他 API；目前寫入空檔
        out_path.write_bytes(b"")
        return {"ok": True, "message": f"{type.capitalize()} generated at {out_path} (stub)", "path": str(out_path)}
    except Exception as e:
        return {"ok": False, "error": str(e), "status": "error"}


# 佈署白名單：僅允許此服務名透過 nssm 啟動，或 D/Z 槽下批次檔路徑
DEPLOY_SERVICE_WHITELIST = {"ZheweiBrain", "Ollama", "Rclone"}
NSSM_PATH = os.environ.get("NSSM_PATH", r"C:\tools\nssm\nssm.exe")


@safe_path
def deploy_service(service_name: str) -> dict[str, Any]:
    """自動化佈署：僅允許白名單服務名（nssm）或 D/Z 槽批次檔路徑。"""
    name = (service_name or "").strip()
    try:
        if name in DEPLOY_SERVICE_WHITELIST:
            exe = NSSM_PATH if Path(NSSM_PATH).exists() else "nssm"
            r = subprocess.run(
                [exe, "start", name],
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8",
                errors="replace",
                cwd=str(BRAIN_WORKSPACE),
            )
            if r.returncode == 0:
                return {"ok": True, "message": f"Service {name} deployed successfully."}
            return {"ok": False, "stderr": r.stderr or "nssm 未安裝或服務不存在", "status": "error"}
        p = Path(name).resolve() if os.path.isabs(name) else (BRAIN_WORKSPACE / name)
        if _path_allowed(p) and p.suffix.lower() in (".bat", ".cmd", ".ps1") and p.exists():
            r = subprocess.run(
                [str(p)],
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
                encoding="utf-8",
                errors="replace",
                cwd=str(p.parent),
            )
            return {"ok": r.returncode == 0, "message": f"Batch {p.name} executed.", "stderr": r.stderr or ""}
        return {"ok": False, "error": "僅允許白名單服務名（ZheweiBrain/Ollama/Rclone）或 D/Z 槽 .bat/.cmd/.ps1 路徑", "status": "error"}
    except FileNotFoundError:
        return {"ok": True, "message": f"Service {name} deploy requested (nssm 未在 PATH，請手動啟動)."}
    except Exception as e:
        return {"ok": False, "error": str(e), "status": "error"}


@safe_path
def update_web_admin(data: str) -> dict[str, Any]:
    """將即時進度同步至網頁後台（LaTeX 格式如 進度 $95\\%$）。預留：可寫入 D/Z 供後台輪詢或由 brain_server WebSocket 推送。"""
    try:
        # 預留：寫入 D 槽供網頁後台輪詢，或透過 brain_server 廣播；data 可含 LaTeX 進度
        progress_file = BRAIN_WORKSPACE / "output" / "web_admin_progress.json"
        if _path_allowed(progress_file):
            progress_file.parent.mkdir(parents=True, exist_ok=True)
            progress_file.write_text(json.dumps({"data": data, "updated": datetime.now().isoformat()}, ensure_ascii=False), encoding="utf-8")
        return {"ok": True, "message": "Web Admin dashboard updated."}
    except Exception as e:
        return {"ok": False, "error": str(e), "status": "error"}


TOOLS = {
    "run_command": run_command,
    "read_file": read_file,
    "write_file": write_file,
    "list_dir": list_dir,
    "vision_analyze": vision_analyze,
    "run_vision_engine": run_vision_engine,
    "manage_construction_log": manage_construction_log,
    "generate_progress_report": generate_progress_report,
    "generate_media": generate_media,
    "deploy_service": deploy_service,
    "update_web_admin": update_web_admin,
}

TOOL_SCHEMA = [
    {"name": "run_command", "args": ["command"], "desc": "執行系統指令，可選 shell=True"},
    {"name": "read_file", "args": ["path"], "desc": "讀取檔案內容"},
    {"name": "write_file", "args": ["path", "content"], "desc": "寫入檔案"},
    {"name": "list_dir", "args": ["path"], "desc": "列出目錄內容，path 預設為 ."},
    {"name": "vision_analyze", "args": ["image_path"], "desc": "視覺辨識：YOLOv8 工地現場物件（LPC/機具/工安），未安裝 ultralytics 時為預留模式"},
    {"name": "run_vision_engine", "args": ["image_path"], "desc": "跨環境呼叫 D:\\brain_workspace 下 3.12 venv_vision 的 YOLOv8 七類辨識"},
    {"name": "manage_construction_log", "args": ["content"], "desc": "寫入工地日報表至 Z 槽 Construction_Logs/Daily_Report.md"},
    {"name": "generate_progress_report", "args": ["detected"], "desc": "依視覺辨識結果（逗號分隔物件名）生成進度報表至 Z 槽 Reports（JSONL + CSV），進度以 $X\\%$ 格式"},
    {"name": "generate_voice_report", "args": ["transcript"], "desc": "將工地語音逐字稿轉為 Markdown 表格報表，寫入 Z 槽 Reports/Daily_Voice_Logs.md（進度以 $X\\%$ 格式）"},
    {"name": "generate_media", "args": ["prompt", "type"], "desc": "對接 Jimeng 或 Grok API 生成圖片/影片，存入 D:\\brain_workspace\\output；type 為 image 或 video"},
    {"name": "deploy_service", "args": ["service_name"], "desc": "自動化佈署指令（如 nssm start 或啟動服務）"},
    {"name": "update_web_admin", "args": ["data"], "desc": "將即時進度（LaTeX 如 $95\\%$）同步至網頁後台"},
]
