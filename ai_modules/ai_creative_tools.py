"""
築未科技大腦 - 創意工具集
文字生圖、3D模型、圖片轉影音、聲音克隆、撰寫完案、炒作人氣、AI影片
"""
import base64
import os
import re
import requests
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE = Path(__file__).parent
try:
    from brain_data_config import CREATIVE_OUTPUT_DIR
    OUTPUT_DIR = CREATIVE_OUTPUT_DIR
except ImportError:
    OUTPUT_DIR = BASE / "creative_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _text_to_image_forge(prompt: str, filename: str, width: int = 1024, height: int = 1024, steps: int = 20) -> str | None:
    """Forge WebUI API 生圖（/sdapi/v1/txt2img）。"""
    forge_port = os.environ.get("FORGE_PORT", "7860").strip()
    forge_url = os.environ.get("FORGE_URL", "").strip()
    base = None
    candidates = []
    if forge_url:
        candidates.append(forge_url.rstrip("/"))
    for host in ["localhost", "127.0.0.1", "host.docker.internal"]:
        candidates.append(f"http://{host}:{forge_port}")
    seen = list(dict.fromkeys(candidates))
    for url in seen:
        try:
            r = requests.get(f"{url}/sdapi/v1/sd-models", timeout=3)
            if r.status_code == 200:
                base = url
                break
        except Exception:
            continue
    if not base:
        return None
    payload = {
        "prompt": prompt[:500],
        "negative_prompt": "blurry, low quality, distorted, watermark, text, ugly, deformed",
        "width": width, "height": height, "steps": steps,
        "cfg_scale": 7, "sampler_name": "Euler",
    }
    try:
        r = requests.post(f"{base}/sdapi/v1/txt2img", json=payload, timeout=120)
        if r.status_code == 200:
            images = r.json().get("images", [])
            if images:
                img_bytes = base64.b64decode(images[0])
                out_path = OUTPUT_DIR / (filename or "image.png")
                out_path.write_bytes(img_bytes)
                return f"已儲存: {out_path}"
    except Exception:
        pass
    return None


def _text_to_image_comfyui(prompt: str, filename: str) -> str | None:
    """本地 ComfyUI API 生圖（需 ComfyUI 運行，預設 port 9188）。"""
    import json as _json, time as _time, uuid as _uuid
    comfy_port = os.environ.get("COMFYUI_PORT", "9188").strip()
    comfy_url = os.environ.get("COMFYUI_URL", "").strip()
    base = None
    candidates = []
    if comfy_url:
        candidates.append(comfy_url.rstrip("/"))
    for host in ["localhost", "127.0.0.1", "host.docker.internal"]:
        for port in [comfy_port, "9188", "8188"]:
            candidates.append(f"http://{host}:{port}")
    seen = []
    for c in candidates:
        if c not in seen:
            seen.append(c)
    for url in seen:
        try:
            r = requests.get(f"{url}/system_stats", timeout=2)
            if r.status_code == 200:
                base = url
                break
        except Exception:
            continue
    if not base:
        return None

    client_id = str(_uuid.uuid4())
    neg = "blurry, low quality, distorted, watermark, text, ugly, deformed"
    workflow = {
        "3": {"class_type": "KSampler", "inputs": {
            "seed": int(_time.time()) % (2**32), "steps": 20, "cfg": 7.0,
            "sampler_name": "euler_ancestral", "scheduler": "normal",
            "denoise": 1.0, "model": ["4", 0], "positive": ["6", 0],
            "negative": ["7", 0], "latent_image": ["5", 0],
        }},
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {
            "ckpt_name": "v1-5-pruned-emaonly.safetensors",
        }},
        "5": {"class_type": "EmptyLatentImage", "inputs": {
            "width": 512, "height": 512, "batch_size": 1,
        }},
        "6": {"class_type": "CLIPTextEncode", "inputs": {
            "text": prompt[:500], "clip": ["4", 1],
        }},
        "7": {"class_type": "CLIPTextEncode", "inputs": {
            "text": neg, "clip": ["4", 1],
        }},
        "8": {"class_type": "VAEDecode", "inputs": {
            "samples": ["3", 0], "vae": ["4", 2],
        }},
        "9": {"class_type": "SaveImage", "inputs": {
            "filename_prefix": "jarvis", "images": ["8", 0],
        }},
    }
    try:
        r = requests.post(f"{base}/prompt", json={"prompt": workflow, "client_id": client_id}, timeout=10)
        if r.status_code not in (200, 201):
            return None
        prompt_id = r.json().get("prompt_id")
        if not prompt_id:
            return None
    except Exception:
        return None

    for _ in range(120):
        _time.sleep(2)
        try:
            hr = requests.get(f"{base}/history/{prompt_id}", timeout=5)
            if hr.status_code != 200:
                continue
            hist = hr.json()
            if prompt_id not in hist:
                continue
            outputs = hist[prompt_id].get("outputs", {})
            for node_id, out in outputs.items():
                images = out.get("images", [])
                if images:
                    img_info = images[0]
                    img_filename = img_info.get("filename", "")
                    subfolder = img_info.get("subfolder", "")
                    img_url = f"{base}/view?filename={img_filename}&subfolder={subfolder}&type=output"
                    img_data = requests.get(img_url, timeout=30)
                    if img_data.status_code == 200:
                        out_path = OUTPUT_DIR / (filename or "image.png")
                        out_path.write_bytes(img_data.content)
                        return f"已儲存: {out_path}"
            return None
        except Exception:
            continue
    return None


def text_to_image(prompt: str, filename: str = "image.png") -> str:
    """文字生圖。優先 Forge，其次 ComfyUI，無則需 REPLICATE_API_TOKEN。"""
    result = _text_to_image_forge(prompt, filename or "image.png")
    if result:
        return result
    result = _text_to_image_comfyui(prompt, filename or "image.png")
    if result:
        return result
    token = os.environ.get("REPLICATE_API_TOKEN", "").strip()
    if not token or token.startswith("your-"):
        return "[需設定] REPLICATE_API_TOKEN (https://replicate.com/account/api-tokens)"
    try:
        r = requests.post(
            "https://api.replicate.com/v1/predictions",
            headers={"Authorization": f"Token {token}", "Content-Type": "application/json"},
            json={
                "version": "39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
                "input": {"prompt": prompt[:1000]},
            },
            timeout=30,
        )
        if r.status_code != 201:
            return f"[錯誤] Replicate API: {r.status_code}"
        pred = r.json()
        poll_url = pred.get("urls", {}).get("get")
        for _ in range(60):
            pr = requests.get(poll_url, headers={"Authorization": f"Token {token}"}, timeout=30)
            data = pr.json()
            status = data.get("status")
            if status == "succeeded":
                out = data.get("output")
                url = out[0] if isinstance(out, list) else out
                img = requests.get(url, timeout=30)
                path = OUTPUT_DIR / (filename or "image.png")
                path.write_bytes(img.content)
                return f"已儲存: {path}"
            if status == "failed":
                return f"[失敗] {data.get('error', 'unknown')}"
        return "[逾時] 生圖超過 2 分鐘"
    except Exception as e:
        return f"[錯誤] {e}"


def generate_3d(prompt: str, filename: str = "model") -> str:
    """生成3D模型。需 MESHY_API_KEY。"""
    key = os.environ.get("MESHY_API_KEY", "").strip()
    if not key or key.startswith("your-"):
        return "[需設定] MESHY_API_KEY (https://meshy.ai/)"
    try:
        r = requests.post(
            "https://api.meshy.ai/v2/text-to-3d",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model_version": "v2", "prompt": prompt[:500], "art_style": "realistic"},
            timeout=30,
        )
        if r.status_code not in (200, 201, 202):
            return f"[錯誤] Meshy API: {r.status_code}"
        j = r.json()
        task_id = j.get("result") or j.get("task_id") or j.get("id")
        return f"3D 生成任務已提交，task_id: {task_id}。請至 Meshy 控制台查看。"
    except Exception as e:
        return f"[錯誤] {e}"


def image_to_video(image_path: str, prompt: str = "", filename: str = "video.mp4") -> str:
    """圖片轉影音。需 RUNWAY_API_KEY。"""
    key = os.environ.get("RUNWAY_API_KEY", "").strip()
    if not key or key.startswith("your-"):
        return "[需設定] RUNWAY_API_KEY (https://runwayml.com/)"
    path = BASE / image_path.lstrip("./")
    if not path.exists():
        return f"[錯誤] 找不到圖片: {image_path}"
    try:
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        r = requests.post(
            "https://api.runwayml.com/v1/image_to_video",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"image": f"data:image/png;base64,{b64}", "prompt": prompt or "smooth motion"},
            timeout=30,
        )
        if r.status_code not in (200, 201, 202):
            return f"[錯誤] Runway API: {r.status_code}"
        j = r.json()
        task_id = j.get("id") or j.get("task_id")
        return f"影音生成任務已提交，task_id: {task_id}。請至 Runway 控制台下載。"
    except Exception as e:
        return f"[錯誤] {e}"


def _voice_clone_piper(text: str, filename: str) -> str | None:
    """本地 Piper TTS（venv312 + scripts/piper_tts.py + piper_models/）。"""
    try:
        import subprocess
        venv_py = BASE / "venv312" / "Scripts" / "python.exe"
        script = BASE / "scripts" / "piper_tts.py"
        if not venv_py.exists() or not script.exists():
            return None
        out_path = OUTPUT_DIR / (filename or "audio.wav")
        r = subprocess.run(
            [str(venv_py), str(script), "--text", text[:500], "--output", str(out_path)],
            capture_output=True, text=True, timeout=30, cwd=str(BASE),
        )
        if r.returncode == 0 and out_path.exists():
            return f"已儲存: {out_path}"
    except Exception:
        pass
    return None


def voice_clone(text: str, voice_id: str = "default", filename: str = "audio.mp3") -> str:
    """聲音克隆／TTS。優先本地 Piper(venv312)，無則需 ELEVENLABS_API_KEY。"""
    result = _voice_clone_piper(text, filename.replace(".mp3", ".wav") if filename.endswith(".mp3") else filename or "audio.wav")
    if result:
        return result
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key or key.startswith("your-"):
        return "[需設定] ELEVENLABS_API_KEY (https://elevenlabs.io/)"
    try:
        r = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={"xi-api-key": key, "Content-Type": "application/json"},
            json={"text": text[:5000], "model_id": "eleven_multilingual_v2"},
            timeout=60,
        )
        if r.status_code != 200:
            return f"[錯誤] ElevenLabs: {r.status_code}"
        path = OUTPUT_DIR / (filename or "audio.mp3")
        path.write_bytes(r.content)
        return f"已儲存: {path}"
    except Exception as e:
        return f"[錯誤] {e}"


def draft_document(topic: str, output_path: str = "draft.md") -> str:
    """撰寫完案：依主題產出文件草稿並寫入檔案。"""
    try:
        from ai_providers import ask_sync
        content, _ = ask_sync(f"請撰寫一份完整的「{topic}」文件草稿，使用 Markdown 格式，內容充實專業。", ensemble=False)
        if not content or "連線失敗" in content:
            return content or "[無回覆]"
        path = (BASE / output_path).resolve()
        if not str(path).startswith(str(BASE)):
            return "[拒絕] 僅能寫入專案內"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"已寫入: {path}"
    except Exception as e:
        return f"[錯誤] {e}"


def hype_marketing(product: str, platform: str = "facebook") -> str:
    """炒作人氣：產出行銷文案、Hashtag、發文建議。"""
    try:
        from ai_providers import ask_sync
        content, _ = ask_sync(
            f"為「{product}」產出 {platform} 平台的炒作人氣內容："
            "1. 吸睛標題 2. 短文案(100字內) 3. 10個Hashtag 4. 發文時機建議",
            ensemble=False,
        )
        return content or "[無回覆]"
    except Exception as e:
        return f"[錯誤] {e}"


def text_to_video(prompt: str, filename: str = "video") -> str:
    """AI影片：文字生成影片。需 RUNWAY_API_KEY。"""
    key = os.environ.get("RUNWAY_API_KEY", "").strip()
    if not key or key.startswith("your-"):
        return "[需設定] RUNWAY_API_KEY (https://runwayml.com/)"
    try:
        r = requests.post(
            "https://api.runwayml.com/v1/text_to_video",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"prompt": prompt[:1000], "duration": 4},
            timeout=30,
        )
        if r.status_code not in (200, 201, 202):
            return f"[錯誤] Runway API: {r.status_code}"
        j = r.json()
        task_id = j.get("id") or j.get("task_id")
        return f"AI 影片任務已提交，task_id: {task_id}。請至 Runway 控制台下載。"
    except Exception as e:
        return f"[錯誤] {e}"


CREATIVE_TOOL_MAP = {
    "text_to_image": lambda args: text_to_image(args[0] if args else "", args[1] if len(args) > 1 else "image.png"),
    "generate_3d": lambda args: generate_3d(args[0] if args else "", args[1] if len(args) > 1 else "model"),
    "image_to_video": lambda args: image_to_video(args[0] if args else "", args[1] if len(args) > 1 else "", args[2] if len(args) > 2 else "video.mp4"),
    "voice_clone": lambda args: voice_clone(args[0] if args else "", args[1] if len(args) > 1 else "default", args[2] if len(args) > 2 else "audio.mp3"),
    "draft_document": lambda args: draft_document(args[0] if args else "", args[1] if len(args) > 1 else "draft.md"),
    "hype_marketing": lambda args: hype_marketing(args[0] if args else "", args[1] if len(args) > 1 else "facebook"),
    "text_to_video": lambda args: text_to_video(args[0] if args else "", args[1] if len(args) > 1 else "video"),
}


def tool_descriptions_extra() -> str:
    """創意工具說明，供 Agent 參考。"""
    return """
創意工具：
- text_to_image: 文字生圖 → TOOL: text_to_image(["提示詞", "檔名.png"])
- generate_3d: 生成3D模型 → TOOL: generate_3d(["提示詞", "檔名"])
- image_to_video: 圖片轉影音 → TOOL: image_to_video(["圖片路徑", "動作描述", "輸出檔名"])
- voice_clone: 聲音克隆/TTS → TOOL: voice_clone(["文字", "voice_id", "輸出檔名"])
- draft_document: 撰寫完案 → TOOL: draft_document(["主題", "輸出路徑"])
- hype_marketing: 炒作人氣 → TOOL: hype_marketing(["產品名", "平台"])
- text_to_video: AI影片 → TOOL: text_to_video(["提示詞", "檔名"])
"""
