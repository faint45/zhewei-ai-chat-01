"""
築未科技 - 多 AI 串聯（本地優先、成本最低）
AI_COST_MODE: local_only | local_first | free_only | all
"""
import os
from typing import Optional

try:
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv()
    _user_env = Path.home() / ".openclaw" / ".env"
    if _user_env.exists():
        load_dotenv(_user_env, override=True)
except ImportError:
    pass

import requests

TIMEOUT = 45
OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11460").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:32b")
OLLAMA_CODER_MODEL = os.environ.get("OLLAMA_CODER_MODEL", "qwen3:32b")
COST_MODE = os.environ.get("AI_COST_MODE", "local_only").lower()
USE_ENSEMBLE = os.environ.get("AI_USE_ENSEMBLE", "1").strip().lower() in ("1", "true", "yes")


def _ollama(prompt: str, model: str = "") -> Optional[str]:
    m = model or OLLAMA_MODEL
    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": m, "prompt": prompt, "stream": False},
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            return r.json().get("response", "").strip()
    except Exception:
        pass
    return None


def _qwen(prompt: str) -> Optional[str]:
    key = os.environ.get("DASHSCOPE_API_KEY")
    if not key:
        return None
    try:
        r = requests.post(
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": "qwen-plus",
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        pass
    return None


def _gemini(prompt: str) -> Optional[str]:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key or key.startswith("your-"):
        return None
    model = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash").strip() or "gemini-1.5-flash"
    try:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            j = r.json()
            return j.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
    except Exception:
        pass
    return None


def _groq(prompt: str, system: str = "", use_coder: bool = False) -> Optional[str]:
    """Groq 免費 70B 模型優先；程式任務可用 CODER 模型"""
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None
    model = os.environ.get("GROQ_CODER_MODEL", "llama-3.1-8b-instant") if use_coder else os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    try:
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model, "messages": msgs},
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        pass
    return None


def _openrouter(prompt: str) -> Optional[str]:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return None
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": "deepseek/deepseek-chat-v3-0324:free",
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        pass
    return None


def _deepseek(prompt: str) -> Optional[str]:
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        return None
    try:
        r = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}]},
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        pass
    return None


def _mistral(prompt: str) -> Optional[str]:
    key = os.environ.get("MISTRAL_API_KEY")
    if not key:
        return None
    try:
        r = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": "mistral-small-latest", "messages": [{"role": "user", "content": prompt}]},
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        pass
    return None


def _grok(prompt: str) -> Optional[str]:
    """xAI Grok - https://x.ai/api"""
    key = os.environ.get("XAI_API_KEY")
    if not key:
        return None
    try:
        model = os.environ.get("XAI_MODEL", "grok-2-latest")
        r = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        pass
    return None


def _hunyuan(prompt: str) -> Optional[str]:
    """騰訊混元 Hunyuan - https://cloud.tencent.com/product/hunyuan"""
    key = os.environ.get("HUNYUAN_API_KEY")
    if not key:
        return None
    try:
        model = os.environ.get("HUNYUAN_MODEL", "hunyuan-lite")
        r = requests.post(
            "https://api.hunyuan.cloud.tencent.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        pass
    return None


def _doubao(prompt: str) -> Optional[str]:
    """字節跳動豆包 Doubao - https://www.volcengine.com/product/doubao"""
    key = os.environ.get("DOUBAO_API_KEY")
    if not key:
        return None
    try:
        ep_id = os.environ.get("DOUBAO_ENDPOINT_ID", "")
        model = os.environ.get("DOUBAO_MODEL", ep_id or "doubao-lite-32k")
        r = requests.post(
            "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        pass
    return None


ALL_PROVIDERS = [
    (_groq, "Groq"),               # 免費 70B 優先
    (_ollama, "Ollama"),           # 本地備援
    (_gemini, "Gemini"),           # 免費額度
    (_openrouter, "OpenRouter"),   # free 模型
    (_grok, "Grok"),               # xAI Grok
    (_deepseek, "DeepSeek"),       # 低價
    (_mistral, "Mistral"),         # 免費額度
    (_hunyuan, "混元"),             # 騰訊混元
    (_doubao, "豆包"),              # 字節豆包
    (_qwen, "千尋"),               # 阿里通義千問
]

FREE_ONLY = [p for p in ALL_PROVIDERS if p[1] in ("Ollama", "Groq", "Gemini", "OpenRouter", "Mistral")]

# 若設 GEMINI_API_KEY 且有效，大腦優先使用 Gemini（像 Gemini 一樣聰明）
def _gemini_first(providers: list) -> list:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key or key.startswith("your-"):
        return providers
    gemini = next((p for p in providers if p[1] == "Gemini"), None)
    if not gemini:
        return providers
    rest = [p for p in providers if p[1] != "Gemini"]
    return [gemini] + rest


def _providers() -> list:
    if COST_MODE == "local_only":
        return [(_ollama, "Ollama")]
    if COST_MODE == "local_first":
        rest = [p for p in FREE_ONLY if p[1] != "Ollama"]
        return [(_ollama, "Ollama")] + rest
    base = FREE_ONLY if COST_MODE == "free_only" else ALL_PROVIDERS
    base = _gemini_first(base)
    # 當月預算已達上限（預設 1000 元新台幣）時，僅使用免費提供者
    try:
        from ai_cost_tracker import is_budget_exceeded
        if is_budget_exceeded():
            base = [p for p in base if p[1] in ("Ollama", "Groq", "Gemini", "OpenRouter", "Mistral")]
    except Exception:
        pass
    return base


def ask(prompt: str, use_image: bool = False, system_prompt: str = "", use_coder_model: bool = False) -> tuple[str, str]:
    """依序嘗試，回傳 (回應, 提供者)。use_coder_model 時程式任務優先 Coder 模型。"""
    for fn, name in _providers():
        if name == "Ollama" and use_image:
            continue
        try:
            if name == "Groq":
                r = fn(prompt, system=system_prompt, use_coder=use_coder_model)
            elif name == "Ollama":
                m = OLLAMA_CODER_MODEL if use_coder_model else OLLAMA_MODEL
                r = fn(prompt, model=m)
            else:
                full = f"{system_prompt}\n\n---\n\n{prompt}" if system_prompt else prompt
                r = fn(full)
            if r:
                return r, name
        except TypeError:
            full = f"{system_prompt}\n\n---\n\n{prompt}" if system_prompt else prompt
            try:
                r = fn(full) if name != "Groq" else fn(prompt, system=system_prompt)
                if r:
                    return r, name
            except Exception:
                continue
        except Exception:
            continue
    try:
        from ai_cost_tracker import is_budget_exceeded
        if is_budget_exceeded():
            return "【本月預算已達上限】僅使用免費 AI；若仍失敗請設定任一免費 API Key (見 .env.example)。", "無"
    except Exception:
        pass
    return "【連線失敗】請設定任一 API Key (見 .env.example)", "無"


def ask_ensemble(prompt: str, use_image: bool = False, max_providers: int = 3, system_prompt: str = "") -> tuple[str, str]:
    """
    多 AI 一起思考：蒐集多個免費 AI 的回應後合併。
    回傳 (合併後回應, 提供者列表)
    """
    providers = [p for p in _providers() if p[1] in ("Ollama", "Groq", "Gemini", "OpenRouter", "Mistral")][:max_providers]
    results = []
    for fn, name in providers:
        if name == "Ollama" and use_image:
            continue
        try:
            if name == "Groq":
                r = fn(prompt, system=system_prompt)
            else:
                full = f"{system_prompt}\n\n---\n\n{prompt}" if system_prompt else prompt
                r = fn(full)
            if r and "連線失敗" not in r:
                results.append((name, r))
                if len(results) >= 2:  # 至少 2 個不同觀點即可
                    break
        except Exception:
            continue

    if not results:
        return ask(prompt, use_image, system_prompt)

    if len(results) == 1:
        return results[0][1], results[0][0]

    parts = [f"【{name}】\n{r}" for name, r in results]
    merged = "【多 AI 共同分析】\n\n" + "\n\n---\n\n".join(parts)
    names = " + ".join(n for n, _ in results)
    return merged, names


def ask_sync(prompt: str, images=None, ensemble: bool = None, system_prompt: str = "", use_coder_model: bool = False) -> tuple[str, str]:
    use_ens = USE_ENSEMBLE if ensemble is None else ensemble
    if use_ens:
        return ask_ensemble(prompt, use_image=bool(images), system_prompt=system_prompt)
    return ask(prompt, use_image=bool(images), system_prompt=system_prompt, use_coder_model=use_coder_model)


def get_available() -> list[str]:
    keys = {"Groq": "GROQ_API_KEY", "Gemini": "GEMINI_API_KEY", "OpenRouter": "OPENROUTER_API_KEY",
            "Grok": "XAI_API_KEY", "DeepSeek": "DEEPSEEK_API_KEY", "Mistral": "MISTRAL_API_KEY",
            "混元": "HUNYUAN_API_KEY", "豆包": "DOUBAO_API_KEY", "千尋": "DASHSCOPE_API_KEY"}
    out = []
    for _, name in _providers():
        if name == "Ollama":
            out.append("Ollama")
        elif name in keys and os.environ.get(keys[name]) and (not os.environ.get(keys[name], "").startswith("your-")):
            out.append(name)
    return out or ["Ollama"]
