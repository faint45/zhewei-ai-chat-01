"""
商用品質審查 — brain_server Docker 容器全面檢查
"""
import importlib
import sys
import os
import traceback

print("=" * 70)
print("商用品質審查 — brain_server Docker 容器")
print("=" * 70)

# === 1. Module Import Check ===
print("\n[1] 模組匯入檢查")
modules = {
    "fastapi": "Web 框架",
    "uvicorn": "ASGI 伺服器",
    "httpx": "HTTP 客戶端",
    "requests": "HTTP 客戶端 (legacy)",
    "chromadb": "向量資料庫",
    "google.generativeai": "Gemini AI",
    "anthropic": "Claude AI",
    "pydantic": "資料驗證",
    "bcrypt": "密碼雜湊",
    "dotenv": "環境變數",
    "websockets": "WebSocket",
    "PIL": "圖像處理",
    "numpy": "數值計算",
    "onnxruntime": "ONNX 推理",
    "psycopg2": "PostgreSQL",
    "yaml": "YAML 解析",
    "starlette": "ASGI 基礎",
    "orjson": "快速 JSON",
    "cryptography": "加密庫",
}
ok_count = fail_count = 0
for m, desc in modules.items():
    try:
        mod = importlib.import_module(m)
        ver = getattr(mod, "__version__", getattr(mod, "VERSION", "?"))
        print(f"  OK  {m} ({desc}) = {ver}")
        ok_count += 1
    except Exception as e:
        err = str(e).split("\n")[0][:60]
        print(f"  FAIL {m} ({desc}): {err}")
        fail_count += 1
print(f"  >> {ok_count} OK / {fail_count} FAIL")

# === 2. brain_server.py import check ===
print("\n[2] brain_server.py 匯入檢查")
sys.path.insert(0, "/app")
try:
    # Don't actually run the server, just check imports
    import brain_server
    print("  OK  brain_server.py 匯入成功")
except Exception as e:
    print(f"  FAIL brain_server.py: {e}")

# === 3. Internal modules ===
print("\n[3] 內部模組檢查")
internal_modules = [
    "ai_service",
    "ai_modules.ai_providers",
    "ai_modules.ai_creative_tools",
    "ai_modules.ai_cost_tracker",
    "ai_modules.thinking_protocol",
    "ai_modules.multi_agent",
    "brain_modules.brain_knowledge",
    "brain_modules.brain_learner",
    "brain_modules.brain_graph_rag",
    "auth_manager",
    "phone_agent",
    "agent_tools",
]
int_ok = int_fail = 0
for m in internal_modules:
    try:
        mod = importlib.import_module(m)
        print(f"  OK  {m}")
        int_ok += 1
    except Exception as e:
        err = str(e).split("\n")[0][:80]
        print(f"  FAIL {m}: {err}")
        int_fail += 1
print(f"  >> {int_ok} OK / {int_fail} FAIL")

# === 4. API Endpoint Count ===
print("\n[4] API 端點統計")
try:
    from brain_server import app
    routes = []
    for route in app.routes:
        if hasattr(route, "methods") and hasattr(route, "path"):
            for method in route.methods:
                if method in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                    routes.append((method, route.path))
    
    get_count = sum(1 for m, _ in routes if m == "GET")
    post_count = sum(1 for m, _ in routes if m == "POST")
    other = len(routes) - get_count - post_count
    print(f"  總計: {len(routes)} 個端點 (GET={get_count}, POST={post_count}, Other={other})")
    
    # Group by prefix
    prefixes = {}
    for _, path in routes:
        parts = path.strip("/").split("/")
        prefix = "/".join(parts[:2]) if len(parts) >= 2 else parts[0] if parts else "root"
        prefixes[prefix] = prefixes.get(prefix, 0) + 1
    for prefix, count in sorted(prefixes.items(), key=lambda x: -x[1])[:15]:
        print(f"    /{prefix}: {count} 端點")
except Exception as e:
    print(f"  FAIL: {e}")

# === 5. Security Checks ===
print("\n[5] 安全性檢查")
issues = []

# Check for hardcoded secrets
import re
try:
    with open("/app/brain_server.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    # Hardcoded passwords/tokens
    patterns = [
        (r'password\s*=\s*["\'][^"\']{3,}["\']', "硬編碼密碼"),
        (r'secret\s*=\s*["\'][^"\']{8,}["\']', "硬編碼密鑰"),
        (r'api_key\s*=\s*["\'][A-Za-z0-9]{10,}["\']', "硬編碼 API Key"),
        (r'token\s*=\s*["\'][A-Za-z0-9]{20,}["\']', "硬編碼 Token"),
    ]
    for pat, desc in patterns:
        matches = re.findall(pat, content, re.IGNORECASE)
        if matches:
            issues.append(f"CRITICAL: {desc} ({len(matches)} 處)")
    
    # JWT secret check
    if 'JWT_SECRET' in content:
        jwt_lines = [l.strip() for l in content.split("\n") if "JWT_SECRET" in l and "environ" not in l and "#" not in l.split("JWT_SECRET")[0]]
        if jwt_lines:
            issues.append(f"WARN: JWT_SECRET 可能未從環境變數讀取")
    
    # CORS check
    if "CORSMiddleware" not in content:
        issues.append("WARN: 未設定 CORS 中間件")
    
    # Rate limiting
    if "RateLimiter" not in content and "slowapi" not in content and "rate_limit" not in content.lower():
        issues.append("CRITICAL: 無 API 速率限制 (Rate Limiting)")
    
    # Input validation
    if content.count("await request.json()") > 5:
        raw_json_count = content.count("await request.json()")
        pydantic_model_count = len(re.findall(r'class \w+\(BaseModel\)', content))
        if pydantic_model_count < 3:
            issues.append(f"WARN: {raw_json_count} 處直接用 request.json()，僅 {pydantic_model_count} 個 Pydantic 模型驗證")
    
    # Error handling
    bare_except = len(re.findall(r'except\s*:', content))
    broad_except = len(re.findall(r'except\s+Exception', content))
    if bare_except > 5:
        issues.append(f"WARN: {bare_except} 處裸 except: (應指定例外類型)")
    
    # SQL injection check
    if "execute(" in content and "%" in content:
        issues.append("WARN: 可能有 SQL 字串格式化 (應用參數化查詢)")
    
    # File path traversal
    if "request.path" in content or "../" in content:
        issues.append("WARN: 檢查路徑遍歷攻擊防護")

    if not issues:
        print("  OK  未發現明顯安全問題")
    else:
        for issue in issues:
            tag = "CRITICAL" if "CRITICAL" in issue else "WARN"
            icon = "!!" if tag == "CRITICAL" else "⚠"
            print(f"  {icon} {issue}")
        
except Exception as e:
    print(f"  FAIL: {e}")

# === 6. Env Vars ===
print("\n[6] 環境變數檢查")
required_vars = {
    "BRAIN_WORKSPACE": "工作目錄",
    "AI_COST_MODE": "AI 計費模式",
    "OLLAMA_BASE_URL": "Ollama 連線",
    "JWT_SECRET": "JWT 密鑰",
    "GEMINI_API_KEY": "Gemini API",
    "GROQ_API_KEY": "Groq API",
    "DEEPSEEK_API_KEY": "DeepSeek API",
}
for var, desc in required_vars.items():
    val = os.environ.get(var, "")
    if val:
        masked = val[:4] + "***" if len(val) > 8 else ("SET" if val else "EMPTY")
        print(f"  OK  {var} ({desc}) = {masked}")
    else:
        print(f"  MISS {var} ({desc})")

# === 7. Disk & Memory ===
print("\n[7] 容器資源")
try:
    import shutil
    total, used, free = shutil.disk_usage("/app")
    print(f"  磁碟: {used/1e9:.1f}GB used / {total/1e9:.1f}GB total ({used/total*100:.0f}%)")
except:
    pass

try:
    with open("/proc/meminfo") as f:
        lines = f.readlines()
    mem_total = int([l for l in lines if "MemTotal" in l][0].split()[1]) / 1024 / 1024
    mem_free = int([l for l in lines if "MemAvailable" in l][0].split()[1]) / 1024 / 1024
    print(f"  記憶體: {mem_total-mem_free:.1f}GB used / {mem_total:.1f}GB total")
except:
    pass

# === 8. File Structure ===
print("\n[8] 關鍵檔案檢查")
critical_files = [
    "/app/brain_server.py",
    "/app/ai_service.py",
    "/app/auth_manager.py",
    "/app/ai_modules/ai_providers.py",
    "/app/ai_modules/ai_creative_tools.py",
    "/app/brain_modules/brain_knowledge.py",
    "/app/brain_workspace/auth/users.json",
    "/app/.env",
]
for fp in critical_files:
    if os.path.exists(fp):
        size = os.path.getsize(fp)
        print(f"  OK  {fp} ({size:,} bytes)")
    else:
        print(f"  MISS {fp}")

# === 9. Error log scan ===
print("\n[9] brain_server.py 程式碼品質")
try:
    with open("/app/brain_server.py", "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    total_lines = len(lines)
    import_count = sum(1 for l in lines if l.strip().startswith("import ") or l.strip().startswith("from "))
    func_count = sum(1 for l in lines if l.strip().startswith("def ") or l.strip().startswith("async def "))
    class_count = sum(1 for l in lines if l.strip().startswith("class "))
    todo_count = sum(1 for l in lines if "TODO" in l or "FIXME" in l or "HACK" in l)
    bare_except = sum(1 for l in lines if "except:" in l and "#" not in l.split("except:")[0])
    broad_except = sum(1 for l in lines if "except Exception" in l)
    
    print(f"  總行數: {total_lines:,}")
    print(f"  函數: {func_count} | 類別: {class_count} | imports: {import_count}")
    print(f"  TODO/FIXME/HACK: {todo_count}")
    print(f"  裸 except: {bare_except} | 寬 except Exception: {broad_except}")
    
    if total_lines > 4000:
        print(f"  !! brain_server.py 過大 ({total_lines} 行)，應拆分為模組")
    if func_count > 80:
        print(f"  !! 函數過多 ({func_count})，違反單一職責原則")
    if bare_except > 3:
        print(f"  !! 裸 except 過多，會吞掉錯誤")
        
except Exception as e:
    print(f"  FAIL: {e}")

# === Summary ===
print("\n" + "=" * 70)
print("商用品質總評")
print("=" * 70)
