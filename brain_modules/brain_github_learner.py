"""
築未科技大腦 - GitHub 資源搜尋與學習
搜尋 GitHub、取得 README/文件、匯入知識庫
支援 GITHUB_TOKEN 提升 rate limit（無 token 也可用，每分鐘約 10 次）
"""
import os
import re
import time
from pathlib import Path
from typing import Optional
from urllib.parse import quote

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import requests

BASE = Path(__file__).parent
GITHUB_API = "https://api.github.com"
GITHUB_RAW = "https://raw.githubusercontent.com"
RATE_DELAY = 6.5  # 無 token 時每分鐘 10 次 ≈ 每 6 秒一次
_last_call = 0.0


def _rate_limit():
    """避免超過 GitHub rate limit"""
    global _last_call
    now = time.time()
    elapsed = now - _last_call
    if elapsed < RATE_DELAY:
        time.sleep(RATE_DELAY - elapsed)
    _last_call = time.time()


def _headers() -> dict:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    h = {"Accept": "application/vnd.github.v3+json", "User-Agent": "ZheWeiTech-Brain"}
    if token and not token.startswith("your-"):
        h["Authorization"] = f"Bearer {token}"
    return h


def search_repos(query: str, language: str = "", sort: str = "stars", per_page: int = 10) -> list[dict]:
    """
    搜尋 GitHub 儲存庫。
    query: 搜尋關鍵字（如 python AI、react hooks）
    language: 篩選語言（python, javascript, typescript 等）
    sort: stars | updated | forks
    回傳 [{full_name, description, html_url, stars, language}, ...]
    """
    _rate_limit()
    q = query.strip()
    if language:
        q = f"{q} language:{language}"
    try:
        r = requests.get(
            f"{GITHUB_API}/search/repositories",
            headers=_headers(),
            params={"q": q, "sort": sort, "per_page": min(per_page, 30), "page": 1},
            timeout=15,
        )
        if r.status_code != 200:
            return []
        data = r.json()
        items = data.get("items", [])
        return [
            {
                "full_name": x.get("full_name", ""),
                "description": x.get("description") or "",
                "html_url": x.get("html_url", ""),
                "stars": x.get("stargazers_count", 0),
                "language": x.get("language") or "",
            }
            for x in items
        ]
    except Exception:
        return []


def fetch_readme(full_name: str) -> Optional[str]:
    """取得 repo 的 README 內容（優先 .md）"""
    _rate_limit()
    try:
        r = requests.get(
            f"{GITHUB_API}/repos/{full_name}/readme",
            headers=_headers(),
            timeout=10,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        content_b64 = data.get("content", "")
        if not content_b64:
            return None
        import base64
        raw = base64.b64decode(content_b64).decode("utf-8", errors="replace")
        # 移除過多 markdown 裝飾，保留可讀內容
        raw = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", raw)
        raw = re.sub(r"#{1,6}\s*", "", raw)
        return raw.strip()[:8000]
    except Exception:
        return None


def fetch_file_raw(full_name: str, path: str, branch: str = "main") -> Optional[str]:
    """從 repo 取得單一檔案純文字（如 docs/xxx.md）"""
    _rate_limit()
    try:
        url = f"{GITHUB_RAW}/{full_name}/{branch}/{path}"
        r = requests.get(url, headers=_headers(), timeout=10)
        if r.status_code != 200:
            url_alt = f"{GITHUB_RAW}/{full_name}/master/{path}"
            r = requests.get(url_alt, headers=_headers(), timeout=10)
        if r.status_code != 200:
            return None
        return r.text.strip()[:8000]
    except Exception:
        return None


def learn_from_repo(full_name: str, add_to_knowledge: bool = True) -> str:
    """
    從單一 repo 取得 README 並匯入知識庫。
    回傳摘要字串。
    """
    readme = fetch_readme(full_name)
    if not readme or len(readme.strip()) < 50:
        return f"[無 README] {full_name}"
    if add_to_knowledge:
        try:
            from brain_knowledge import add
            add(
                f"【GitHub:{full_name}】\n{readme}",
                source=f"GitHub:{full_name}",
                metadata={"type": "github", "repo": full_name},
            )
        except Exception as e:
            return f"[匯入失敗] {full_name}: {e}"
    return f"已學習：{full_name}（{len(readme)} 字）"


def search_and_learn(
    query: str,
    language: str = "",
    max_repos: int = 5,
) -> str:
    """
    搜尋 GitHub、取 README、匯入知識庫。
    回傳多行摘要。
    """
    repos = search_repos(query, language=language, per_page=max_repos)
    if not repos:
        return f"搜尋「{query}」無結果"
    lines = [f"找到 {len(repos)} 個 repo，開始學習..."]
    for r in repos:
        name = r.get("full_name", "")
        desc = (r.get("description") or "")[:80]
        lines.append(f"- {name} ({r.get('stars', 0)}★) {desc}")
        result = learn_from_repo(name, add_to_knowledge=True)
        lines.append(f"  → {result}")
    return "\n".join(lines)


def get_topic_repos(topic: str, per_page: int = 5) -> list[dict]:
    """依 topic 搜尋（如 python-machine-learning、react）"""
    return search_repos(f"topic:{topic}", per_page=per_page)


def run_auto_learn_topics(topics: list[str] = None, per_topic: int = 3) -> str:
    """
    依預設或指定 topics 自動學習。
    預設：python AI、react、typescript、ollama、llm
    """
    if topics is None:
        topics = ["python AI", "react hooks", "ollama", "llm agent", "sentence-transformers"]
    lines = ["【自動學習 GitHub 資源】"]
    for t in topics:
        lines.append(f"\n--- {t} ---")
        lines.append(search_and_learn(t, max_repos=per_topic))
    return "\n".join(lines)
