#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VLM 視覺代理（主機端）
- mode=line: 截取 LINE 視窗訊息區並做視覺問答
- mode=screen: 截取全螢幕並做視覺問答
- mode=file: 讀取指定圖片並做視覺問答
優先使用本地 Ollama Vision，失敗可 fallback 到 Claude Vision。
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

import pyautogui


ROOT = Path(__file__).resolve().parent.parent


def _find_line_window():
    try:
        import pygetwindow as gw
    except Exception:
        return None
    try:
        ws = gw.getWindowsWithTitle("LINE")
    except Exception:
        ws = []
    for w in ws:
        try:
            if not w.isMinimized and w.width > 320 and w.height > 320:
                return w
        except Exception:
            continue
    return None


def _capture_line_region() -> tuple[Path | None, str]:
    w = _find_line_window()
    if w is None:
        return None, "找不到 LINE 視窗"
    left = int(w.left + max(180, w.width * 0.26))
    top = int(w.top + max(70, w.height * 0.10))
    width = int(max(220, w.width * 0.68))
    height = int(max(220, w.height * 0.78))
    out_dir = ROOT / "reports" / "vlm"
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"line_vlm_{int(time.time())}.png"
    snap = pyautogui.screenshot(region=(left, top, width, height))
    snap.save(str(p))
    return p, ""


def _capture_screen() -> tuple[Path, str]:
    out_dir = ROOT / "reports" / "vlm"
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"screen_vlm_{int(time.time())}.png"
    pyautogui.screenshot().save(str(p))
    return p, ""


def _image_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _extract_json(text: str) -> dict:
    raw = (text or "").strip()
    if not raw:
        return {}
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        return {}
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _call_ollama_vision(model: str, prompt: str, image_path: Path) -> tuple[bool, str]:
    bases = []
    for raw in [
        os.environ.get("VLM_OLLAMA_BASE_URL", ""),
        os.environ.get("OLLAMA_BASE_URL", ""),
        "http://127.0.0.1:11460",
        "http://localhost:11460",
        "http://127.0.0.1:11434",
        "http://localhost:11434",
    ]:
        s = str(raw or "").strip().rstrip("/")
        if s and s not in bases:
            bases.append(s)
    payload = {
        "model": model,
        "prompt": prompt,
        "images": [_image_b64(image_path)],
        "stream": False,
    }
    errs: list[str] = []
    for base in bases:
        url = base + "/api/generate"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                body = json.loads(r.read().decode("utf-8", errors="ignore"))
                ans = str(body.get("response") or "").strip()
                if ans:
                    return True, ans
                errs.append(f"{base}: empty response")
        except Exception as e:
            errs.append(f"{base}: {e}")
    return False, "Ollama vision failed: " + " | ".join(errs[:3])


def _call_claude_vision(model: str, prompt: str, image_path: Path) -> tuple[bool, str]:
    api_key = (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY") or "").strip()
    if not api_key:
        return False, "未設定 ANTHROPIC_API_KEY / CLAUDE_API_KEY"
    url = "https://api.anthropic.com/v1/messages"
    payload = {
        "model": model,
        "max_tokens": 1024,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": _image_b64(image_path),
                        },
                    },
                ],
            }
        ],
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            body = json.loads(r.read().decode("utf-8", errors="ignore"))
            content = body.get("content", [])
            texts = []
            if isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "text":
                        texts.append(str(c.get("text") or ""))
            ans = "\n".join([t for t in texts if t.strip()]).strip()
            return bool(ans), ans
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8", errors="ignore")
        except Exception:
            detail = str(e)
        return False, f"Claude vision failed: {detail[:800]}"
    except Exception as e:
        return False, f"Claude vision failed: {e}"


def _build_prompt(question: str, keywords: list[str]) -> str:
    keys = [str(k).strip() for k in keywords if str(k).strip()]
    return (
        "你是螢幕視覺助理。請根據圖片內容回答問題，並只輸出 JSON。\n"
        "JSON 格式：\n"
        "{\n"
        '  "last_sender": "",\n'
        '  "last_message": "",\n'
        '  "mentions_keywords": [],\n'
        '  "confidence": 0.0,\n'
        '  "summary": ""\n'
        "}\n"
        f"問題：{question}\n"
        f"關鍵字：{keys}\n"
        "若無法判斷，請在 summary 說明原因並把 confidence 降低。"
    )


def run(mode: str, question: str, keywords: list[str], image: str, provider: str) -> dict:
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05

    img_path: Path | None = None
    err = ""
    if mode == "line":
        img_path, err = _capture_line_region()
    elif mode == "screen":
        img_path, err = _capture_screen()
    else:
        p = Path(image or "")
        if not p.is_absolute():
            p = (ROOT / p).resolve()
        if p.exists():
            img_path = p
        else:
            err = f"找不到圖片：{p}"
    if not img_path:
        return {"ok": False, "error": err or "capture failed"}

    prompt = _build_prompt(question, keywords)
    ollama_model = (os.environ.get("VLM_OLLAMA_MODEL") or "moondream").strip()
    claude_model = (os.environ.get("CLAUDE_COMPUTER_USE_MODEL") or "claude-3-5-sonnet-latest").strip()
    provider_order = ["ollama", "claude"] if provider == "auto" else [provider]

    last_err = ""
    for p in provider_order:
        if p == "ollama":
            ok, text = _call_ollama_vision(ollama_model, prompt, img_path)
        elif p == "claude":
            ok, text = _call_claude_vision(claude_model, prompt, img_path)
        else:
            ok, text = False, f"unsupported provider: {p}"
        if ok:
            obj = _extract_json(text)
            if obj:
                k = [str(x).strip() for x in keywords if str(x).strip()]
                hits = [kw for kw in k if kw in json.dumps(obj, ensure_ascii=False).lower() or kw in json.dumps(obj, ensure_ascii=False)]
                obj["mentions_keywords"] = list(dict.fromkeys((obj.get("mentions_keywords") or []) + hits))
                return {
                    "ok": True,
                    "provider": p,
                    "screenshot": str(img_path),
                    "result": obj,
                }
            return {
                "ok": True,
                "provider": p,
                "screenshot": str(img_path),
                "result": {
                    "summary": text[:2000],
                    "confidence": 0.4,
                    "mentions_keywords": [],
                },
            }
        last_err = text
    # 最後退路：OCR（低信心），避免任務完全失敗
    try:
        import pytesseract
        from PIL import Image

        raw = pytesseract.image_to_string(Image.open(str(img_path)), lang="chi_tra+eng")
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        fallback = {
            "last_sender": "",
            "last_message": (lines[-1] if lines else "")[:200],
            "mentions_keywords": [k for k in keywords if k and any(k.lower() in ln.lower() for ln in lines)],
            "confidence": 0.2,
            "summary": "\n".join(lines[:25])[:1800] or "OCR 無可用文字",
            "warning": "VLM 不可用，已回退 OCR，準確率有限。",
        }
        return {"ok": True, "provider": "ocr_fallback", "screenshot": str(img_path), "result": fallback}
    except Exception:
        return {
            "ok": True,
            "provider": "degraded_fallback",
            "screenshot": str(img_path),
            "result": {
                "last_sender": "",
                "last_message": "",
                "mentions_keywords": [],
                "confidence": 0.0,
                "summary": "VLM 與 OCR 皆不可用，僅回傳截圖路徑供人工確認。",
                "warning": last_err or "all providers failed",
            },
        }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["line", "screen", "file"], required=True)
    ap.add_argument("--question", required=True)
    ap.add_argument("--keywords", default="")
    ap.add_argument("--image", default="")
    ap.add_argument("--provider", choices=["auto", "ollama", "claude"], default="auto")
    args = ap.parse_args()

    keys = [k.strip() for k in (args.keywords or "").split(",") if k.strip()]
    res = run(args.mode, args.question, keys, args.image, args.provider)
    print(json.dumps(res, ensure_ascii=False))
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
