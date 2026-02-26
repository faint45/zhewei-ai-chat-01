# -*- coding: utf-8 -*-
"""
築未科技 — App Builder 模組（構想即系統）
掛載到 Smart Bridge，不修改核心。

用法：在 smart_bridge.py 末尾加一行
  from bridge_app_builder import mount_app_builder; mount_app_builder(app)
"""

import asyncio
import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.responses import StreamingResponse

# ── AI Provider 呼叫 ──────────────────────────────────
OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11460")
GROQ_KEY = os.environ.get("GROQ_API_KEY", "")
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

# 儲存目錄
BUILDS_DIR = Path(__file__).resolve().parent / "bridge_workspace" / "builds"
BUILDS_DIR.mkdir(parents=True, exist_ok=True)


async def _call_groq(messages: list, model: str = "llama-3.3-70b-versatile") -> str:
    """呼叫 Groq API（免費 70B）"""
    import httpx
    async with httpx.AsyncClient(timeout=120.0) as c:
        r = await c.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "max_tokens": 16000, "temperature": 0.7},
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


async def _call_deepseek(messages: list) -> str:
    """呼叫 DeepSeek API"""
    import httpx
    async with httpx.AsyncClient(timeout=120.0) as c:
        r = await c.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "messages": messages, "max_tokens": 16000, "temperature": 0.7},
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


async def _call_gemini(messages: list) -> str:
    """呼叫 Gemini API"""
    import httpx
    # 轉換 messages 為 Gemini 格式
    contents = []
    for m in messages:
        role = "user" if m["role"] in ("user", "system") else "model"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})
    async with httpx.AsyncClient(timeout=120.0) as c:
        r = await c.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}",
            json={"contents": contents, "generationConfig": {"maxOutputTokens": 16000, "temperature": 0.7}},
        )
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]


async def _call_best_available(messages: list) -> tuple[str, str]:
    """依序嘗試可用的大模型，回傳 (content, provider)"""
    providers = []
    if GROQ_KEY:
        providers.append(("groq-70b", _call_groq))
    if DEEPSEEK_KEY:
        providers.append(("deepseek", _call_deepseek))
    if GEMINI_KEY:
        providers.append(("gemini", _call_gemini))

    for name, fn in providers:
        try:
            content = await fn(messages)
            return content, name
        except Exception as e:
            print(f"⚠️ AppBuilder {name} failed: {e}")
            continue

    raise RuntimeError("所有 AI Provider 都不可用，請設定 GROQ_API_KEY / DEEPSEEK_API_KEY / GEMINI_API_KEY")


async def _stream_groq(messages: list, model: str = "llama-3.3-70b-versatile"):
    """Groq SSE 串流生成"""
    import httpx
    async with httpx.AsyncClient(timeout=120.0) as c:
        async with c.stream(
            "POST",
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "max_tokens": 16000, "temperature": 0.7, "stream": True},
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    chunk = line[6:]
                    if chunk.strip() == "[DONE]":
                        break
                    try:
                        d = json.loads(chunk)
                        delta = d["choices"][0].get("delta", {}).get("content", "")
                        if delta:
                            yield delta
                    except Exception:
                        pass


# ── System Prompt ─────────────────────────────────────
SYSTEM_PROMPT = """你是「築未科技 App Builder」，一個能從用戶的構想直接生成完整可運行系統的 AI。

## 你的能力
用戶只需要用一句話描述想法，你就能生成一個**完整的單頁 Web 應用**，包含：
- 完整的 HTML + CSS + JavaScript
- 現代化 UI（使用 TailwindCSS CDN）
- 響應式設計（手機 + 桌面）
- 完整的互動邏輯
- 本地資料儲存（localStorage）

## 輸出規則（嚴格遵守）
1. 只輸出一個完整的 HTML 檔案，從 `<!DOCTYPE html>` 開始到 `</html>` 結束
2. 不要輸出任何解釋、說明、markdown 標記
3. 不要用 ```html 包裹
4. 所有 CSS 和 JS 都內嵌在 HTML 中
5. 使用 TailwindCSS CDN：`<script src="https://cdn.tailwindcss.com"></script>`
6. 使用 Font Awesome CDN：`<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">`
7. 中文介面，繁體中文
8. 深色主題（bg-slate-900 系列）
9. 必須是完整可運行的，打開就能用
10. 加入適當的動畫和過渡效果

## 設計標準
- 專業級 UI，不是玩具
- 完善的錯誤處理
- 流暢的使用者體驗
- 適當的 loading 狀態
- 資料持久化（localStorage）"""


# ── 核心生成函數 ──────────────────────────────────────
async def generate_app(idea: str, refine_prompt: str = "") -> dict:
    """從構想生成完整應用"""
    t0 = time.time()
    build_id = f"build_{uuid.uuid4().hex[:8]}"

    user_msg = idea
    if refine_prompt:
        user_msg = f"原始構想：{idea}\n\n修改要求：{refine_prompt}"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]

    content, provider = await _call_best_available(messages)

    # 清理：提取純 HTML
    html = _extract_html(content)

    duration_ms = int((time.time() - t0) * 1000)

    # 儲存
    meta = {
        "id": build_id,
        "idea": idea,
        "refine_prompt": refine_prompt,
        "provider": provider,
        "duration_ms": duration_ms,
        "created_at": datetime.now().isoformat(),
        "size_bytes": len(html.encode("utf-8")),
    }
    build_dir = BUILDS_DIR / build_id
    build_dir.mkdir(exist_ok=True)
    (build_dir / "index.html").write_text(html, encoding="utf-8")
    (build_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "ok": True,
        "build_id": build_id,
        "html": html,
        "provider": provider,
        "duration_ms": duration_ms,
        "size_bytes": len(html.encode("utf-8")),
    }


def _extract_html(raw: str) -> str:
    """從 AI 回應中提取純 HTML"""
    # 移除 markdown 包裹
    if "```html" in raw:
        start = raw.index("```html") + 7
        end = raw.rindex("```") if raw.count("```") > 1 else len(raw)
        raw = raw[start:end].strip()
    elif "```" in raw:
        start = raw.index("```") + 3
        end = raw.rindex("```") if raw.count("```") > 1 else len(raw)
        raw = raw[start:end].strip()

    # 確保以 <!DOCTYPE 開頭
    if "<!DOCTYPE" in raw:
        raw = raw[raw.index("<!DOCTYPE"):]
    elif "<html" in raw:
        raw = raw[raw.index("<html"):]

    # 確保以 </html> 結尾
    if "</html>" in raw:
        raw = raw[:raw.rindex("</html>") + 7]

    return raw.strip()


def _list_builds() -> list:
    """列出所有已生成的應用"""
    builds = []
    for d in sorted(BUILDS_DIR.iterdir(), reverse=True):
        meta_file = d / "meta.json"
        if meta_file.exists():
            try:
                builds.append(json.loads(meta_file.read_text(encoding="utf-8")))
            except Exception:
                pass
    return builds[:50]


# ── 掛載到 FastAPI ────────────────────────────────────
def mount_app_builder(app):
    """掛載 App Builder 路由到現有 Smart Bridge app"""

    @app.get("/app-builder")
    async def app_builder_page():
        """App Builder 前端頁面"""
        html_path = Path(__file__).resolve().parent / "bridge_workspace" / "static" / "app-builder.html"
        if html_path.exists():
            return HTMLResponse(html_path.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>app-builder.html not found</h1>", status_code=404)

    @app.post("/api/app-builder/generate")
    async def api_generate_app(request: Request):
        """生成應用 API"""
        data = await request.json()
        idea = str(data.get("idea", "")).strip()
        refine = str(data.get("refine", "")).strip()
        if not idea:
            raise HTTPException(400, "請輸入你的構想")
        result = await generate_app(idea, refine)
        return result

    @app.post("/api/app-builder/stream")
    async def api_stream_generate(request: Request):
        """SSE 串流生成應用"""
        data = await request.json()
        idea = str(data.get("idea", "")).strip()
        refine = str(data.get("refine", "")).strip()
        if not idea:
            raise HTTPException(400, "請輸入你的構想")

        user_msg = idea
        if refine:
            user_msg = f"原始構想：{idea}\n\n修改要求：{refine}"
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]

        build_id = f"build_{uuid.uuid4().hex[:8]}"

        async def event_stream():
            t0 = time.time()
            full_content = ""
            provider = "groq-70b"
            try:
                async for chunk in _stream_groq(messages):
                    full_content += chunk
                    yield f"data: {json.dumps({'type':'chunk','content':chunk}, ensure_ascii=False)}\n\n"
            except Exception as e:
                # fallback 到非串流
                try:
                    full_content, provider = await _call_best_available(messages)
                    yield f"data: {json.dumps({'type':'chunk','content':full_content}, ensure_ascii=False)}\n\n"
                except Exception as e2:
                    yield f"data: {json.dumps({'type':'error','message':str(e2)}, ensure_ascii=False)}\n\n"
                    return

            html = _extract_html(full_content)
            duration_ms = int((time.time() - t0) * 1000)

            # 儲存
            meta = {
                "id": build_id, "idea": idea, "refine_prompt": refine,
                "provider": provider, "duration_ms": duration_ms,
                "created_at": datetime.now().isoformat(),
                "size_bytes": len(html.encode("utf-8")),
            }
            bd = BUILDS_DIR / build_id
            bd.mkdir(exist_ok=True)
            (bd / "index.html").write_text(html, encoding="utf-8")
            (bd / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

            yield f"data: {json.dumps({'type':'done','build_id':build_id,'provider':provider,'duration_ms':duration_ms,'size_bytes':len(html.encode('utf-8')),'html':html}, ensure_ascii=False)}\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.get("/api/app-builder/builds")
    async def api_list_builds():
        """列出歷史生成"""
        return {"ok": True, "builds": _list_builds()}

    @app.get("/api/app-builder/builds/{build_id}")
    async def api_get_build(build_id: str):
        """取得特定 build 的 HTML"""
        html_file = BUILDS_DIR / build_id / "index.html"
        if not html_file.exists():
            raise HTTPException(404, "Build not found")
        return HTMLResponse(html_file.read_text(encoding="utf-8"))

    @app.delete("/api/app-builder/builds/{build_id}")
    async def api_delete_build(build_id: str):
        """刪除 build"""
        build_dir = BUILDS_DIR / build_id
        if build_dir.exists():
            import shutil
            shutil.rmtree(build_dir)
            return {"ok": True}
        raise HTTPException(404, "Build not found")

    print("✅ App Builder 模組已掛載 → /app-builder")
