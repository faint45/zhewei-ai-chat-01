"""
築未科技大腦 Agent - 工具集
提供：讀檔、寫檔、列表、計算、時間、建置、部署、Git 等
"""
import ast
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

BASE = Path(__file__).parent.resolve()
ALLOWED_BUILTINS = {"abs", "round", "min", "max", "sum", "len", "int", "float", "str"}
_BLOCKED = {".env", ".env.local", ".env.production", "brain_learn.json", "ai_discoveries.json", "chat_history.json"}


def _safe_path(p: str) -> Path:
    path = (BASE / p).resolve()
    if not str(path).startswith(str(BASE)):
        raise ValueError(f"禁止存取專案外: {p}")
    return path


def _blocked(path: Path) -> bool:
    name = path.name
    if name.startswith(".env"):
        return True
    return name in _BLOCKED


def read_file(path: str) -> str:
    """讀取檔案內容。path 為專案內相對路徑。敏感檔已封鎖。"""
    try:
        p = _safe_path(path)
        if _blocked(p):
            return "[拒絕] 該檔案受保護，禁止讀取。"
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"[錯誤] {e}"


def write_file(path: str, content: str) -> str:
    """寫入檔案。path 為專案內相對路徑。敏感檔已封鎖。"""
    try:
        p = _safe_path(path)
        if _blocked(p):
            return "[拒絕] 該檔案受保護，禁止寫入。"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"已寫入: {path}"
    except Exception as e:
        return f"[錯誤] {e}"


def list_dir(path: str = ".") -> str:
    """列出目錄內容。path 為專案內相對路徑。"""
    try:
        p = _safe_path(path)
        if not p.is_dir():
            return f"[錯誤] 非目錄: {path}"
        items = [f"{x.name}/" if x.is_dir() else x.name for x in sorted(p.iterdir())]
        return "\n".join(items) if items else "(空)"
    except Exception as e:
        return f"[錯誤] {e}"


def calc(expr: str) -> str:
    """安全計算數學表達式，僅支援基本運算與內建函式。"""
    try:
        expr = expr.strip().replace("^", "**")
        tree = ast.parse(expr, mode="eval")
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id not in ALLOWED_BUILTINS:
                    return f"[錯誤] 不允許的函式: {node.func.id}"
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                return "[錯誤] 不允許 import"
        return str(eval(expr))
    except Exception as e:
        return f"[錯誤] {e}"


def get_time() -> str:
    """取得目前時間。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z")


def run_build() -> str:
    """執行 npm run build 建置專案。"""
    try:
        r = subprocess.run(
            ["npm", "run", "build"],
            cwd=str(BASE),
            capture_output=True,
            text=True,
            timeout=180,
            shell=(sys.platform == "win32"),
        )
        out = (r.stdout or "") + (r.stderr or "")
        return f"exit={r.returncode}\n{out[-3000:]}" if out else f"exit={r.returncode}"
    except subprocess.TimeoutExpired:
        return "[逾時] build 超過 3 分鐘"
    except Exception as e:
        return f"[錯誤] {e}"


def run_deploy_vercel() -> str:
    """建置並部署到 Vercel。"""
    try:
        r = subprocess.run(
            ["npm", "run", "build"],
            cwd=str(BASE),
            capture_output=True,
            text=True,
            timeout=180,
            shell=sys.platform == "win32",
        )
        if r.returncode != 0:
            return f"建置失敗 exit={r.returncode}\n{(r.stdout or '')+(r.stderr or '')}"[-3000:]
        r2 = subprocess.run(
            ["npx", "vercel", "--prod"],
            cwd=str(BASE),
            capture_output=True,
            text=True,
            timeout=300,
            shell=sys.platform == "win32",
        )
        out = (r2.stdout or "") + (r2.stderr or "")
        return f"部署 exit={r2.returncode}\n{out[-3000:]}" if out else f"exit={r2.returncode}"
    except subprocess.TimeoutExpired:
        return "[逾時] 部署超過 5 分鐘"
    except Exception as e:
        return f"[錯誤] {e}"


def run_self_check() -> str:
    """執行系統自檢 (npm run self-check)。"""
    try:
        r = subprocess.run(
            ["node", "scripts/self-check.js"],
            cwd=str(BASE),
            capture_output=True,
            text=True,
            timeout=60,
        )
        out = (r.stdout or "") + (r.stderr or "")
        return out[-4000:] if out else f"exit={r.returncode}"
    except Exception as e:
        return f"[錯誤] {e}"


def search_github(query: str, max_repos: str = "5") -> str:
    """搜尋 GitHub 並回傳 repo 列表。"""
    try:
        from brain_github_learner import search_repos
        n = int(max_repos) if max_repos.isdigit() else 5
        repos = search_repos(query.strip(), per_page=min(n, 15))
        if not repos:
            return f"搜尋「{query}」無結果"
        lines = [f"找到 {len(repos)} 個 repo："]
        for r in repos:
            lines.append(f"- {r['full_name']} ({r.get('stars',0)}★) {r.get('description','')[:60]}")
        return "\n".join(lines)
    except Exception as e:
        return f"[錯誤] {e}"


def learn_from_github(query: str, max_repos: str = "5") -> str:
    """從 GitHub 主題學習並匯入知識庫。"""
    try:
        from brain_github_learner import search_and_learn
        n = int(max_repos) if max_repos.isdigit() else 5
        return search_and_learn(query.strip(), max_repos=min(n, 10))
    except Exception as e:
        return f"[錯誤] {e}"


def run_self_learn() -> str:
    """執行自動學習：GitHub 主題 + 知識萃取。"""
    try:
        from brain_self_learner import run_scheduled_learn
        return run_scheduled_learn()
    except Exception as e:
        return f"[錯誤] {e}"


RUN_PYTHON_ALLOWED = {"json", "math", "datetime", "re", "collections", "itertools"}
RUN_PYTHON_MAX_CHARS = 8000
RUN_PYTHON_TIMEOUT = 30


def run_python(code: str) -> str:
    """
    安全執行 Python 程式碼（沙盒）。
    允許：json, math, datetime, numpy, pandas, requests（若已安裝）
    禁止：檔案寫入、subprocess、eval/exec 動態碼
    """
    if not code or len(code.strip()) < 3:
        return "[錯誤] 需提供程式碼"
    if len(code) > RUN_PYTHON_MAX_CHARS:
        return f"[錯誤] 程式碼超過 {RUN_PYTHON_MAX_CHARS} 字"
    safe_builtins = {
        "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict, "enumerate": enumerate,
        "filter": filter, "float": float, "int": int, "iter": iter, "len": len, "list": list,
        "map": map, "max": max, "min": min, "print": print, "range": range, "round": round,
        "sorted": sorted, "str": str, "sum": sum, "tuple": tuple, "zip": zip,
        "True": True, "False": False, "None": None,
    }
    g = {"__builtins__": safe_builtins}
    for mod in RUN_PYTHON_ALLOWED:
        try:
            g[mod] = __import__(mod)
        except ImportError:
            pass
    for mod in ("numpy", "pandas", "requests"):
        try:
            g[mod.replace(".", "_")] = __import__(mod)
            if mod == "numpy":
                g["np"] = g["numpy"]
        except ImportError:
            pass
    out = []
    _print = lambda *a, **k: out.append(" ".join(str(x) for x in a))
    g["print"] = _print
    allowed_mods = RUN_PYTHON_ALLOWED | {"numpy", "pandas", "requests", "np"}
    for node in ast.walk(ast.parse(code)):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mod = (node.module or "") if isinstance(node, ast.ImportFrom) else (node.names[0].name if node.names else "")
            if mod and mod.split(".")[0] not in allowed_mods:
                return f"[拒絕] 不允許 import {mod}"
        if isinstance(node, ast.Call) and hasattr(node.func, "id"):
            if getattr(node.func, "id", "") in ("exec", "eval", "compile", "open", "__import__"):
                return f"[拒絕] 不允許呼叫 {node.func.id}"
    try:
        exec(code, g)
        return "\n".join(out) if out else "(無輸出)"
    except Exception as e:
        return f"[執行錯誤] {e}"


def search_graph_rag(query: str, limit: str = "5") -> str:
    """搜尋 Graph RAG（圖表知識）：營建圖、配筋圖、施工大樣等。"""
    try:
        from brain_modules.brain_graph_rag import search_graph_rag_str
        n = min(int(limit), 10) if str(limit).isdigit() else 5
        return search_graph_rag_str(query.strip(), limit=n)
    except Exception as e:
        return f"[錯誤] {e}"


def ingest_graph_rag_pdf(pdf_path: str, source_name: str = "") -> str:
    """將 PDF 匯入 Graph RAG：轉圖 → VLM 描述 → 存入向量庫。"""
    try:
        from brain_modules.brain_graph_rag import ingest_pdf
        p = Path(pdf_path).resolve()
        if not p.exists():
            return "[錯誤] PDF 不存在"
        r = ingest_pdf(p, source_name=source_name or p.stem)
        if r.get("ok"):
            errs = r.get("errors", [])
            return f"已匯入 {r['pages']} 頁。" + (f" 警告：{errs}" if errs else "")
        err_list = r.get("errors", ["未知"])
        return "[錯誤] " + str(err_list)
    except Exception as e:
        return f"[錯誤] {e}"


def web_search(query: str, max_results: str = "5") -> str:
    """網頁搜尋。支援 duckduckgo-search（免 key）或 SERPER_API_KEY、TAVILY_API_KEY。"""
    q = (query or "").strip()
    if not q:
        return "[錯誤] 需搜尋關鍵字"
    n = min(int(max_results), 10) if str(max_results).isdigit() else 5
    try:
        key = os.environ.get("SERPER_API_KEY", "").strip()
        if key and not key.startswith("your-"):
            import requests
            r = requests.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": key, "Content-Type": "application/json"},
                json={"q": q, "num": n},
                timeout=15,
            )
            if r.status_code == 200:
                data = r.json()
                items = data.get("organic", [])[:n]
                lines = [f"【Serper 搜尋】{q}"]
                for i, x in enumerate(items, 1):
                    lines.append(f"{i}. {x.get('title','')}\n   {x.get('link','')}\n   {x.get('snippet','')[:150]}")
                return "\n\n".join(lines)
    except Exception:
        pass
    try:
        key = os.environ.get("TAVILY_API_KEY", "").strip()
        if key and not key.startswith("your-"):
            import requests
            r = requests.post(
                "https://api.tavily.com/search",
                json={"api_key": key, "query": q, "search_depth": "basic", "max_results": n},
                timeout=15,
            )
            if r.status_code == 200:
                data = r.json()
                items = data.get("results", [])[:n]
                lines = [f"【Tavily 搜尋】{q}"]
                for i, x in enumerate(items, 1):
                    lines.append(f"{i}. {x.get('title','')}\n   {x.get('url','')}\n   {x.get('content','')[:150]}")
                return "\n\n".join(lines)
    except Exception:
        pass
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(q, max_results=n))
        lines = [f"【DuckDuckGo 搜尋】{q}"]
        for i, x in enumerate(results[:n], 1):
            lines.append(f"{i}. {x.get('title','')}\n   {x.get('href','')}\n   {x.get('body','')[:150]}")
        return "\n\n".join(lines)
    except ImportError:
        return "[需安裝] pip install duckduckgo-search 或設定 SERPER_API_KEY / TAVILY_API_KEY"
    except Exception as e:
        return f"[錯誤] {e}"


def fetch_url(url: str, max_chars: str = "3000") -> str:
    """抓取網頁內容並回傳摘要（純文字）。"""
    u = (url or "").strip()
    if not u:
        return "[錯誤] 需 URL"
    if not u.startswith(("http://", "https://")):
        u = "https://" + u
    try:
        import requests
        r = requests.get(u, timeout=15, headers={"User-Agent": "ZheWeiTech-Brain/1.0"})
        r.raise_for_status()
        html = r.text
        text = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", html, flags=re.I)
        text = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", text, flags=re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        limit = min(int(max_chars), 8000) if str(max_chars).isdigit() else 3000
        return text[:limit] if text else "(無法擷取文字)"
    except Exception as e:
        return f"[錯誤] {e}"


def search_knowledge(query: str, limit: str = "8") -> str:
    """主動查詢統一知識庫（Jarvis Training ChromaDB 14,600+ 筆語意向量）。"""
    q = (query or "").strip()
    n = min(int(limit), 20) if str(limit).isdigit() else 8
    # 優先使用 Jarvis Training 的語意搜尋
    try:
        sys.path.insert(0, str(Path(__file__).parent / "Jarvis_Training"))
        from local_learning_system import search as jarvis_search
        hits = jarvis_search(q or "最近", top_k=n)
        if hits:
            parts = []
            for i, h in enumerate(hits, 1):
                dist = h.get("distance")
                sim = f"{1-dist:.2f}" if dist is not None else "?"
                parts.append(f"[{i}] ({sim}) {h.get('question','')[:80]}\n{h.get('answer','')[:300]}")
            return "【統一知識庫】\n" + "\n\n".join(parts)
    except Exception:
        pass
    # 回退到 brain_knowledge
    try:
        from brain_knowledge import search
        result = search(q or "最近", limit=n)
        return result if result else "(知識庫無相關內容)"
    except Exception as e:
        return f"[錯誤] {e}"


def diff_files(path_a: str, path_b: str) -> str:
    """比較兩檔案差異（unified diff）。"""
    try:
        import difflib
        a = _safe_path(path_a)
        b = _safe_path(path_b)
        if _blocked(a) or _blocked(b):
            return "[拒絕] 該檔案受保護"
        if not a.exists():
            return f"[錯誤] 找不到: {path_a}"
        if not b.exists():
            return f"[錯誤] 找不到: {path_b}"
        lines_a = a.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
        lines_b = b.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
        diff = difflib.unified_diff(lines_a, lines_b, fromfile=path_a, tofile=path_b, lineterm="")
        out = "".join(diff)
        return out[:5000] if out else "(兩檔案相同)"
    except Exception as e:
        return f"[錯誤] {e}"


def run_git_push(msg: str) -> str:
    """執行 git add . && git commit -m \"訊息\" && git push。msg 為 commit 訊息。"""
    if not msg or len(msg) > 200:
        return "[錯誤] commit 訊息需 1～200 字"
    try:
        r = subprocess.run(["git", "add", "."], cwd=str(BASE), capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            return f"git add 失敗:\n{(r.stdout or '')+(r.stderr or '')}"[-1500:]
        r = subprocess.run(["git", "commit", "-m", msg], cwd=str(BASE), capture_output=True, text=True, timeout=30)
        err = (r.stderr or "").lower()
        if r.returncode != 0 and "nothing to commit" not in err and "working tree clean" not in err:
            return f"git commit 失敗:\n{(r.stdout or '')+(r.stderr or '')}"[-1500:]
        r = subprocess.run(["git", "push"], cwd=str(BASE), capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            return f"git push 失敗:\n{(r.stdout or '')+(r.stderr or '')}"[-1500:]
        return "git add / commit / push 完成"
    except Exception as e:
        return f"[錯誤] {e}"


try:
    from ai_creative_tools import CREATIVE_TOOL_MAP, tool_descriptions_extra
    _CREATIVE_TOOLS = CREATIVE_TOOL_MAP
    _CREATIVE_DESC = tool_descriptions_extra()
except ImportError:
    _CREATIVE_TOOLS = {}
    _CREATIVE_DESC = ""

try:
    from ai_vision_tools import VISION_TOOL_MAP, tool_descriptions_vision
    _VISION_TOOLS = VISION_TOOL_MAP
    _VISION_DESC = tool_descriptions_vision()
except ImportError:
    _VISION_TOOLS = {}
    _VISION_DESC = ""


def tool_descriptions() -> str:
    """供 LLM 參考的工具說明。"""
    base = """
可使用工具，必須嚴格依下列格式輸出（一次一個）：
- read_file: 讀檔 → TOOL: read_file(["路徑"])
- write_file: 寫檔 → TOOL: write_file(["路徑","內容"])
- list_dir: 列目錄 → TOOL: list_dir(["."])
- calc: 計算 → TOOL: calc(["1+2*3"])
- get_time: 時間 → TOOL: get_time([])
- run_build: 建置專案 (npm run build) → TOOL: run_build([])
- run_deploy_vercel: 部署到 Vercel → TOOL: run_deploy_vercel([])
- run_self_check: 系統自檢 → TOOL: run_self_check([])
- run_git_push: Git 提交並推送 → TOOL: run_git_push(["訊息"])
- search_github: 搜尋 GitHub 儲存庫 → TOOL: search_github(["python AI", "3"])
- learn_from_github: 從 GitHub 主題學習並匯入知識庫 → TOOL: learn_from_github(["python AI", "5"])
- run_self_learn: 執行自動學習（GitHub 主題 + 知識萃取）→ TOOL: run_self_learn([])
- run_python: 執行 Python（pandas/numpy/requests）→ TOOL: run_python(["import pandas as pd\\nprint(pd.Series([1,2,3]).sum())"])
- web_search: 網頁搜尋 → TOOL: web_search(["python 教學", "5"])
- fetch_url: 抓取網頁內容 → TOOL: fetch_url(["https://example.com", "3000"])
- search_knowledge: 查詢知識庫 → TOOL: search_knowledge(["ollama", "8"])
- diff_files: 比較兩檔案差異 → TOOL: diff_files(["a.py", "b.py"])
- codebuddy_ask: 呼叫 CodeBuddy AI 執行開發任務 → TOOL: codebuddy_ask(["分析這個專案結構", "false"])
- codebuddy_review: CodeBuddy 程式碼審查 → TOOL: codebuddy_review(["src/App.jsx"])
- codebuddy_fix: CodeBuddy 修復程式碼 → TOOL: codebuddy_fix(["path.py", "錯誤訊息"])
- codebuddy_generate: CodeBuddy 生成程式碼 → TOOL: codebuddy_generate(["建立登入頁面", "src/Login.jsx"])
""" + _CREATIVE_DESC + _VISION_DESC + """
【唯一正確格式】TOOL: 工具名(["參數1","參數2"])
嚴禁輸出 FILE: 或 CONTENT: 當作工具呼叫，參數必須在括號內。
"""
    return base


TOOL_MAP = {
    "read_file": lambda args: read_file(args[0]) if args else "[錯誤] 需 path",
    "write_file": lambda args: write_file(args[0], args[1]) if len(args) >= 2 else "[錯誤] 需 path, content",
    "list_dir": lambda args: list_dir(args[0] if args else "."),
    "calc": lambda args: calc(args[0]) if args else "[錯誤] 需 expr",
    "get_time": lambda args: get_time(),
    "run_build": lambda args: run_build(),
    "run_deploy_vercel": lambda args: run_deploy_vercel(),
    "run_self_check": lambda args: run_self_check(),
    "run_git_push": lambda args: run_git_push(args[0]) if args else "[錯誤] 需 commit 訊息",
    "search_github": lambda args: search_github(args[0], args[1] if len(args) > 1 else "5") if args else "[錯誤] 需 query",
    "learn_from_github": lambda args: learn_from_github(args[0], args[1] if len(args) > 1 else "5") if args else "[錯誤] 需 query",
    "run_self_learn": lambda args: run_self_learn(),
    "run_python": lambda args: run_python(args[0]) if args else "[錯誤] 需 code",
    "web_search": lambda args: web_search(args[0], args[1] if len(args) > 1 else "5") if args else "[錯誤] 需 query",
    "fetch_url": lambda args: fetch_url(args[0], args[1] if len(args) > 1 else "3000") if args else "[錯誤] 需 url",
    "search_knowledge": lambda args: search_knowledge(args[0], args[1] if len(args) > 1 else "8") if args else "[錯誤] 需 query",
    "diff_files": lambda args: diff_files(args[0], args[1]) if len(args) >= 2 else "[錯誤] 需 path_a, path_b",
}
TOOL_MAP.update(_CREATIVE_TOOLS)
TOOL_MAP.update(_VISION_TOOLS)

# CodeBuddy 整合
try:
    from codebuddy_integration import ask as cb_ask, code_review as cb_review, fix_code as cb_fix, generate_code as cb_gen, is_available as cb_ok
    if cb_ok():
        TOOL_MAP.update({
            "codebuddy_ask": lambda args: cb_ask(args[0], skip_permissions=(args[1].lower() == "true" if len(args) > 1 else False))[0] if args else "[錯誤] 需 prompt",
            "codebuddy_review": lambda args: cb_review(args[0])[0] if args else "[錯誤] 需 file_path",
            "codebuddy_fix": lambda args: cb_fix(args[0], args[1] if len(args) > 1 else "")[0] if args else "[錯誤] 需 file_path",
            "codebuddy_generate": lambda args: cb_gen(args[0], args[1] if len(args) > 1 else "")[0] if args else "[錯誤] 需 description",
        })
except ImportError:
    pass


def parse_tool_call(text: str) -> tuple[str, list] | None:
    """
    從 LLM 輸出解析多種格式：
    - TOOL: name(["arg"])
    - TOOL: name
      FILE: path
    - TOOL: name FILE: path
    """
    m = re.search(r"TOOL:\s*(\w+)\s*\(", text, re.IGNORECASE)
    if m:
        name = m.group(1).lower()
        if name not in TOOL_MAP:
            return None
        start = m.end()
        depth, idx = 0, start
        for idx, c in enumerate(text[start:], start):
            if c == "(":
                depth += 1
            elif c == ")":
                if depth == 0:
                    break
                depth -= 1
        args_str = text[start:idx].strip()
        try:
            args = json.loads(args_str) if args_str else []
            if not isinstance(args, list):
                args = [args]
            return name, args
        except json.JSONDecodeError:
            parts = re.findall(r'"([^"]*)"', args_str)
            if parts:
                return name, parts
            return None

    m2 = re.search(r"TOOL:\s*(\w+)(?:\s|$)", text, re.IGNORECASE)
    if m2:
        name = m2.group(1).lower()
        if name not in TOOL_MAP:
            return None
        file_m = re.search(r"FILE:\s*([^\s\n]+)", text, re.IGNORECASE)
        path_m = re.search(r"PATH:\s*([^\s\n]+)", text, re.IGNORECASE)
        content_m = re.search(r"CONTENT:\s*(.+?)(?=\n[A-Z]+:|\n\n|$)", text, re.DOTALL | re.IGNORECASE)
        expr_m = re.search(r"EXPR:\s*([^\n]+)", text, re.IGNORECASE)
        if name == "read_file" and (file_m or path_m):
            return name, [(file_m or path_m).group(1).strip()]
        if name == "write_file" and (file_m or path_m) and content_m:
            return name, [(file_m or path_m).group(1).strip(), content_m.group(1).strip()]
        if name == "list_dir" and (file_m or path_m):
            return name, [(file_m or path_m).group(1).strip()]
        if name == "calc" and expr_m:
            return name, [expr_m.group(1).strip()]
    return None


def run_tool(name: str, args: list) -> str:
    """執行工具，回傳結果字串。"""
    if name not in TOOL_MAP:
        return f"[錯誤] 未知工具: {name}"
    try:
        return str(TOOL_MAP[name](args))
    except Exception as e:
        return f"[錯誤] {e}"


# ---------------------------
# AgentLogic 相容層（TOOL_SCHEMA/TOOLS）
# ---------------------------
Z_ROOT = Path(os.environ.get("ZHEWEI_MEMORY_ROOT", "Z:/Zhewei_Brain"))
REPORT_ROOT = Z_ROOT / "Reports"


def _to_obs(result: Any) -> dict[str, Any]:
    """將舊字串回傳轉成 AgentManager 可讀取的 dict 格式。"""
    if isinstance(result, dict):
        if "ok" not in result and "status" not in result:
            result["ok"] = True
        return result
    text = str(result or "")
    if text.startswith("[錯誤]") or text.startswith("[拒絕]") or text.startswith("[執行錯誤]"):
        return {"ok": False, "status": "error", "content": text, "stderr": text, "error": text}
    return {"ok": True, "status": "ok", "content": text, "stderr": ""}


def run_command(command: str) -> dict[str, Any]:
    cmd = (command or "").strip()
    if not cmd:
        return _to_obs("[錯誤] 需 command")
    try:
        p = subprocess.run(
            cmd,
            cwd=str(BASE),
            shell=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        out = ((p.stdout or "") + (p.stderr or "")).strip()
        return {
            "ok": p.returncode == 0,
            "status": "ok" if p.returncode == 0 else "error",
            "content": out[-5000:] if out else f"exit={p.returncode}",
            "stderr": "" if p.returncode == 0 else (p.stderr or out)[-2000:],
            "exit_code": p.returncode,
        }
    except Exception as e:
        return _to_obs(f"[錯誤] {e}")


def vision_analyze(image_path: str) -> dict[str, Any]:
    try:
        from jarvis_vision_bridge import analyze_image_local
        return _to_obs(analyze_image_local(image_path))
    except Exception as e:
        return _to_obs(f"[錯誤] vision_analyze 失敗: {e}")


def run_vision_engine(image_path: str) -> dict[str, Any]:
    """保留跨環境呼叫入口：目前代理到 vision_analyze。"""
    return vision_analyze(image_path)


def manage_construction_log(content: str) -> dict[str, Any]:
    try:
        REPORT_ROOT.mkdir(parents=True, exist_ok=True)
        log_file = REPORT_ROOT / f"Construction_Log_{datetime.now().strftime('%Y%m%d')}.md"
        line = f"- [{datetime.now().strftime('%H:%M:%S')}] {(content or '').strip()}\n"
        with log_file.open("a", encoding="utf-8") as f:
            f.write(line)
        return _to_obs(f"已寫入施工日誌: {log_file}")
    except Exception as e:
        return _to_obs(f"[錯誤] {e}")


def generate_progress_report(detected: Any) -> dict[str, Any]:
    try:
        from report_generator import generate_progress_report as _gen
        if isinstance(detected, dict):
            payload = detected
        elif isinstance(detected, list):
            payload = {"detected": detected}
        else:
            payload = {"detected": [str(detected)] if detected else []}
        return _to_obs(_gen(payload))
    except Exception as e:
        return _to_obs(f"[錯誤] {e}")


async def generate_voice_report(transcript: str = "", gemini_service=None) -> dict[str, Any]:
    """
    生成語音摘要並寫入 Z 槽 Markdown（語音報表分流）。
    """
    text = (transcript or "").strip()
    if not text:
        return _to_obs("[錯誤] 需 transcript")
    try:
        REPORT_ROOT.mkdir(parents=True, exist_ok=True)
        voice_file = REPORT_ROOT / "Daily_Voice_Logs.md"
        summary = text
        if gemini_service is not None:
            try:
                prompt = f"請將以下逐字稿整理為工地日誌重點（繁中、條列、精簡）:\n{text}"
                summary = await gemini_service.chat([{"role": "user", "content": prompt}])
            except Exception:
                summary = text
        block = (
            f"\n## {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"### 原始逐字稿\n{text}\n\n"
            f"### 整理摘要\n{summary}\n"
        )
        with voice_file.open("a", encoding="utf-8") as f:
            f.write(block)
        return {"ok": True, "status": "ok", "content": f"語音報表已更新: {voice_file}", "path": str(voice_file)}
    except Exception as e:
        return _to_obs(f"[錯誤] {e}")


def generate_media(prompt: str, type: str = "image") -> dict[str, Any]:
    return _to_obs(f"[錯誤] generate_media 尚未接線（type={type}, prompt={prompt[:40] if prompt else ''}）")


def deploy_service(service_name: str) -> dict[str, Any]:
    name = (service_name or "").strip() or "unknown"
    return _to_obs(f"[錯誤] deploy_service 尚未接線（service={name}）")


def update_web_admin(data: Any) -> dict[str, Any]:
    try:
        workspace = Path(os.environ.get("BRAIN_WORKSPACE", "D:/brain_workspace"))
        out_file = workspace / "admin_updates.jsonl"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "timestamp": datetime.now().isoformat(),
            "data": data if isinstance(data, (dict, list)) else str(data),
        }
        with out_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return _to_obs(f"已更新 Web 管理資料: {out_file}")
    except Exception as e:
        return _to_obs(f"[錯誤] {e}")


def _tool_from_map(name: str, *args: Any) -> dict[str, Any]:
    return _to_obs(run_tool(name, list(args)))


# ===== 手機代理人工具包裝 =====

def _phone_task_wrapper(task: str) -> dict[str, Any]:
    """執行手機任務（自然語言指令）"""
    try:
        from phone_agent import phone_task
        result = phone_task(task)
        return _to_obs(json.dumps(result, ensure_ascii=False, default=str))
    except ImportError:
        return _to_obs("[錯誤] phone_agent 模組未找到")
    except Exception as e:
        return _to_obs(f"[錯誤] 手機任務失敗: {e}")


def _phone_screenshot_wrapper() -> dict[str, Any]:
    """手機截圖 + AI 分析"""
    try:
        from phone_agent import phone_screenshot
        result = phone_screenshot()
        return _to_obs(json.dumps(result, ensure_ascii=False, default=str))
    except ImportError:
        return _to_obs("[錯誤] phone_agent 模組未找到")
    except Exception as e:
        return _to_obs(f"[錯誤] 截圖失敗: {e}")


def _line_reply_wrapper(message: str, contact: str = "") -> dict[str, Any]:
    """LINE 回覆訊息"""
    try:
        from phone_agent import line_reply
        result = line_reply(message, contact)
        return _to_obs(json.dumps(result, ensure_ascii=False, default=str))
    except ImportError:
        return _to_obs("[錯誤] phone_agent 模組未找到")
    except Exception as e:
        return _to_obs(f"[錯誤] LINE 回覆失敗: {e}")


def _line_read_wrapper() -> dict[str, Any]:
    """讀取 LINE 最新訊息"""
    try:
        from phone_agent import line_read_latest
        result = line_read_latest()
        return _to_obs(json.dumps(result, ensure_ascii=False, default=str))
    except ImportError:
        return _to_obs("[錯誤] phone_agent 模組未找到")
    except Exception as e:
        return _to_obs(f"[錯誤] LINE 讀取失敗: {e}")


TOOLS: dict[str, Any] = {
    "run_command": lambda command="": run_command(command),
    "read_file": lambda path="": _tool_from_map("read_file", path),
    "write_file": lambda path="", content="": _tool_from_map("write_file", path, content),
    "list_dir": lambda path=".": _tool_from_map("list_dir", path),
    "vision_analyze": lambda image_path="": vision_analyze(image_path),
    "run_vision_engine": lambda image_path="": run_vision_engine(image_path),
    "manage_construction_log": lambda content="": manage_construction_log(content),
    "generate_progress_report": lambda detected=None: generate_progress_report(detected),
    "generate_media": lambda prompt="", type="image": generate_media(prompt, type),
    "deploy_service": lambda service_name="": deploy_service(service_name),
    "update_web_admin": lambda data=None: update_web_admin(data if data is not None else {}),
    "search_graph_rag": lambda query="", limit="5": search_graph_rag(query, limit),
    "ingest_graph_rag_pdf": lambda pdf_path="", source_name="": ingest_graph_rag_pdf(pdf_path, source_name),
    "phone_task": lambda task="": _phone_task_wrapper(task),
    "phone_screenshot": lambda: _phone_screenshot_wrapper(),
    "line_reply": lambda message="", contact="": _line_reply_wrapper(message, contact),
    "line_read": lambda: _line_read_wrapper(),
}

TOOL_SCHEMA: dict[str, Any] = {
    "run_command": {"required": ["command"]},
    "read_file": {"required": ["path"]},
    "write_file": {"required": ["path", "content"]},
    "list_dir": {"required": []},
    "vision_analyze": {"required": ["image_path"]},
    "run_vision_engine": {"required": ["image_path"]},
    "manage_construction_log": {"required": ["content"]},
    "generate_progress_report": {"required": ["detected"]},
    "generate_voice_report": {"required": ["transcript"]},
    "generate_media": {"required": ["prompt", "type"]},
    "deploy_service": {"required": ["service_name"]},
    "update_web_admin": {"required": ["data"]},
    "search_graph_rag": {"required": ["query"], "optional": ["limit"]},
    "ingest_graph_rag_pdf": {"required": ["pdf_path"], "optional": ["source_name"]},
    "phone_task": {"required": ["task"]},
    "phone_screenshot": {"required": []},
    "line_reply": {"required": ["message"], "optional": ["contact"]},
    "line_read": {"required": []},
}
