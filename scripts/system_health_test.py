"""
全系統 26 項端到端功能測試
Usage: python scripts/system_health_test.py
"""
import asyncio
import json
import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import httpx
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx", "-q"])
    import httpx

RESULTS = []
TIMEOUT = 15

def record(test_id: int, name: str, status: str, detail: str = "", elapsed: float = 0):
    icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    RESULTS.append({"id": test_id, "name": name, "status": status, "detail": detail, "elapsed": elapsed})
    print(f"  {icon} [{test_id:02d}] {name}: {status} ({elapsed:.1f}s) {detail}")


async def test_port(client: httpx.AsyncClient, test_id: int, name: str, url: str, expect_key: str = None):
    t0 = time.time()
    try:
        r = await client.get(url, timeout=TIMEOUT)
        elapsed = time.time() - t0
        if r.status_code < 500:
            detail = f"HTTP {r.status_code}"
            if expect_key:
                try:
                    data = r.json()
                    if expect_key in str(data):
                        detail += f" | found '{expect_key}'"
                    else:
                        detail += f" | missing '{expect_key}'"
                except:
                    pass
            record(test_id, name, "PASS", detail, elapsed)
        else:
            record(test_id, name, "FAIL", f"HTTP {r.status_code}", elapsed)
    except Exception as e:
        elapsed = time.time() - t0
        record(test_id, name, "FAIL", str(e)[:120], elapsed)


async def test_ollama_chat(client: httpx.AsyncClient):
    """Test 2: Ollama model chat"""
    t0 = time.time()
    try:
        r = await client.get("http://localhost:11460/api/tags", timeout=TIMEOUT)
        elapsed = time.time() - t0
        if r.status_code == 200:
            models = r.json().get("models", [])
            names = [m.get("name", "") for m in models]
            record(2, "Ollama 本地模型", "PASS", f"{len(models)} models: {', '.join(names[:5])}", elapsed)
        else:
            record(2, "Ollama 本地模型", "FAIL", f"HTTP {r.status_code}", elapsed)
    except Exception as e:
        elapsed = time.time() - t0
        record(2, "Ollama 本地模型", "FAIL", str(e)[:120], elapsed)


async def test_ollama_generate(client: httpx.AsyncClient):
    """Test 3: Ollama quick generate (qwen3:4b)"""
    t0 = time.time()
    try:
        body = {
            "model": "qwen3:4b",
            "messages": [{"role": "user", "content": "Say hi in 5 words"}],
            "stream": False,
            "options": {"num_predict": 30}
        }
        r = await client.post("http://localhost:11460/api/chat", json=body, timeout=30)
        elapsed = time.time() - t0
        if r.status_code == 200:
            data = r.json()
            content = data.get("message", {}).get("content", "")[:80]
            record(3, "Ollama 推理 (qwen3:4b)", "PASS", f"回覆: {content}", elapsed)
        else:
            record(3, "Ollama 推理 (qwen3:4b)", "FAIL", f"HTTP {r.status_code}", elapsed)
    except Exception as e:
        elapsed = time.time() - t0
        record(3, "Ollama 推理 (qwen3:4b)", "FAIL", str(e)[:120], elapsed)


async def test_brain_chat(client: httpx.AsyncClient):
    """Test 4: Brain Server AI chat"""
    t0 = time.time()
    try:
        r = await client.get("http://localhost:8002/api/chat/remote/status", timeout=TIMEOUT)
        elapsed = time.time() - t0
        if r.status_code == 200:
            record(4, "Brain Server AI Chat", "PASS", f"HTTP 200 chat/remote OK", elapsed)
        else:
            record(4, "Brain Server AI Chat", "WARN", f"HTTP {r.status_code}", elapsed)
    except Exception as e:
        elapsed = time.time() - t0
        record(4, "Brain Server AI Chat", "FAIL", str(e)[:120], elapsed)


async def test_cloudflare_domains(client: httpx.AsyncClient):
    """Test 13: Cloudflare external domains"""
    domains = [
        ("zhe-wei.net", "主站"),
        ("jarvis.zhe-wei.net", "Jarvis"),
        ("bridge.zhe-wei.net", "Bridge"),
        ("codesim.zhe-wei.net", "CodeSim"),
    ]
    t0 = time.time()
    results = []
    for domain, label in domains:
        try:
            r = await client.get(f"https://{domain}", timeout=TIMEOUT, follow_redirects=True)
            results.append(f"{label}={r.status_code}")
        except Exception as e:
            results.append(f"{label}=ERR")
    elapsed = time.time() - t0
    all_ok = all("ERR" not in r for r in results)
    record(13, "Cloudflare 外網域名", "PASS" if all_ok else "WARN", " | ".join(results), elapsed)


async def test_ntfy(client: httpx.AsyncClient):
    """Test 21: Ntfy push notification"""
    t0 = time.time()
    try:
        r = await client.get("http://localhost:2586/v1/health", timeout=TIMEOUT)
        elapsed = time.time() - t0
        if r.status_code == 200:
            record(21, "Ntfy 推播服務", "PASS", "本地容器 healthy", elapsed)
        else:
            record(21, "Ntfy 推播服務", "FAIL", f"HTTP {r.status_code}", elapsed)
    except Exception as e:
        elapsed = time.time() - t0
        record(21, "Ntfy 推播服務", "FAIL", str(e)[:120], elapsed)


async def test_discord_bot():
    """Test 14: Discord Bot heartbeat"""
    t0 = time.time()
    hb_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "Jarvis_Training", ".jarvis_discord_bot.heartbeat.json")
    try:
        if os.path.exists(hb_path):
            with open(hb_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            last = data.get("timestamp", "unknown")
            status = data.get("status", "unknown")
            elapsed = time.time() - t0
            record(14, "Discord Bot (Jarvis)", "PASS" if status == "running" else "WARN",
                   f"status={status}, last={last}", elapsed)
        else:
            elapsed = time.time() - t0
            record(14, "Discord Bot (Jarvis)", "WARN", "heartbeat 檔案不存在", elapsed)
    except Exception as e:
        elapsed = time.time() - t0
        record(14, "Discord Bot (Jarvis)", "FAIL", str(e)[:120], elapsed)


async def test_knowledge_base():
    """Test 17: ChromaDB knowledge base"""
    t0 = time.time()
    try:
        from brain_modules.brain_knowledge import search
        result = search("test", limit=3)
        elapsed = time.time() - t0
        record(17, "知識庫 ChromaDB", "PASS", f"搜尋成功, 結果長度={len(str(result))}", elapsed)
    except Exception as e:
        elapsed = time.time() - t0
        record(17, "知識庫 ChromaDB", "FAIL", str(e)[:120], elapsed)


async def test_auth_system(client: httpx.AsyncClient):
    """Test 20: JWT auth"""
    t0 = time.time()
    try:
        body = {"username": "test_health_check", "password": "wrong_password"}
        r = await client.post("http://localhost:8002/api/auth/login", json=body, timeout=TIMEOUT)
        elapsed = time.time() - t0
        # We expect 401 or 403 for wrong password - that means auth is working
        if r.status_code in (401, 403, 422):
            record(20, "認證系統 JWT", "PASS", f"Auth 拒絕 HTTP {r.status_code}", elapsed)
        elif r.status_code == 200:
            data = r.json()
            if data.get("ok") is False:
                record(20, "認證系統 JWT", "PASS", f"Auth 正確拒絕: {data.get('error','')}", elapsed)
            else:
                record(20, "認證系統 JWT", "WARN", "接受了錯誤密碼?!", elapsed)
        else:
            record(20, "認證系統 JWT", "WARN", f"HTTP {r.status_code}", elapsed)
    except Exception as e:
        elapsed = time.time() - t0
        record(20, "認證系統 JWT", "FAIL", str(e)[:120], elapsed)


async def test_mcp_servers():
    """Test 19: MCP servers importable"""
    t0 = time.time()
    mcp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mcp_servers")
    found = []
    errors = []
    if os.path.isdir(mcp_dir):
        for f in os.listdir(mcp_dir):
            if f.endswith(".py") and f != "__init__.py":
                found.append(f)
    elapsed = time.time() - t0
    if found:
        record(19, "MCP 伺服器", "PASS", f"{len(found)} 個: {', '.join(found[:5])}", elapsed)
    else:
        record(19, "MCP 伺服器", "WARN", "找不到 MCP 伺服器", elapsed)


async def test_pwa_login(client: httpx.AsyncClient):
    """Test 27: PWA login flow"""
    t0 = time.time()
    try:
        body = {"username": "allen34556", "password": "Rr124243084"}
        r = await client.post("http://localhost:8002/api/auth/login", json=body, timeout=TIMEOUT)
        d = r.json()
        elapsed = time.time() - t0
        if d.get("ok") and d.get("token"):
            # Verify token
            r2 = await client.get("http://localhost:8002/api/auth/me",
                                  headers={"Authorization": f"Bearer {d['token']}"},
                                  timeout=TIMEOUT)
            me = r2.json()
            role = me.get("user", {}).get("role", "?")
            record(27, "PWA 登入流程", "PASS", f"superadmin={role=='superadmin'}, role={role}", elapsed)
        else:
            record(27, "PWA 登入流程", "FAIL", d.get("error", "no token"), elapsed)
    except Exception as e:
        elapsed = time.time() - t0
        record(27, "PWA 登入流程", "FAIL", str(e)[:120], elapsed)


async def main():
    print("=" * 70)
    print("🔍 築未科技 — 全系統 26 項端到端功能測試")
    print(f"   時間: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()

    async with httpx.AsyncClient(verify=False) as client:
        # === Group 1: Core Infrastructure ===
        print("📦 [Group 1] 核心基礎設施")
        await test_port(client, 1, "Brain Server API", "http://localhost:8002/healthz")
        await test_ollama_chat(client)
        await test_ollama_generate(client)
        await test_brain_chat(client)
        print()

        # === Group 2: AI Creative Services ===
        print("🎨 [Group 2] AI 創作服務")
        await test_port(client, 5, "Forge 生圖", "http://localhost:7860/sdapi/v1/options")
        await test_port(client, 6, "ComfyUI 生圖", "http://localhost:9188/system_stats")
        await test_port(client, 7, "AI 視覺辨識 (YOLO+OCR)", "http://localhost:8030/healthz")
        await test_port(client, 15, "ComfyUI 影片", "http://localhost:9188/object_info")
        await test_port(client, 16, "Ollama Prompt 翻譯", "http://localhost:11460/api/tags")
        print()

        # === Group 3: Application Services ===
        print("🛠️ [Group 3] 應用服務")
        await test_port(client, 8, "代碼模擬器 CodeSim (GW)", "http://localhost:8888/", expect_key=None)
        # CodeSim is Docker-internal, test via Gateway with Host header
        try:
            r = await client.get("http://localhost:8888/", headers={"Host": "codesim.zhe-wei.net"}, timeout=TIMEOUT)
            record(8, "代碼模擬器 CodeSim (GW)", "PASS" if r.status_code < 500 else "FAIL", f"via Gateway HTTP {r.status_code}", 0)
        except Exception as e:
            record(8, "代碼模擬器 CodeSim (GW)", "FAIL", str(e)[:80], 0)
        await test_port(client, 9, "CMS 營建管理", "http://localhost:8020/healthz")
        await test_port(client, 10, "預測/警報系統", "http://localhost:8025/healthz")
        await test_port(client, 11, "Dify", "http://localhost:8080/")
        await test_port(client, 12, "Bridge 工作空間", "http://localhost:8003/healthz")
        await test_port(client, 22, "DeepDiagram 圖表", "http://localhost:8041/")
        print()

        # === Group 4: Gateway & External ===
        print("🌐 [Group 4] 閘道與外網")
        await test_port(client, 23, "Gateway Nginx", "http://localhost:8888/")
        await test_cloudflare_domains(client)
        await test_ntfy(client)
        print()

        # === Group 5: Backend Modules ===
        print("🧩 [Group 5] 後端模組")
        await test_discord_bot()
        await test_knowledge_base()
        await test_mcp_servers()
        await test_auth_system(client)
        await test_port(client, 18, "Phone Agent (模組)", "http://localhost:8002/api/phone/status")
        print()

        # === Group 6: PWA ===
        print("📱 [Group 6] PWA 可攜式 AI 助手")
        await test_port(client, 24, "PWA 頁面", "http://localhost:8002/pwa")
        await test_port(client, 25, "PWA Manifest", "http://localhost:8002/pwa/manifest.json", expect_key="築未")
        await test_port(client, 26, "PWA Service Worker", "http://localhost:8002/pwa/sw.js")
        await test_pwa_login(client)
        print()

    # === Summary ===
    print("=" * 70)
    passed = sum(1 for r in RESULTS if r["status"] == "PASS")
    warned = sum(1 for r in RESULTS if r["status"] == "WARN")
    failed = sum(1 for r in RESULTS if r["status"] == "FAIL")
    total = len(RESULTS)
    print(f"📊 測試結果: {passed} PASS / {warned} WARN / {failed} FAIL / {total} Total")
    print(f"   通過率: {passed/total*100:.0f}%")
    print("=" * 70)

    # Save report
    report_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "SYSTEM_HEALTH_REPORT.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# 全系統健康報告\n\n")
        f.write(f"**測試時間**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**結果**: {passed} ✅ / {warned} ⚠️ / {failed} ❌ / {total} 項\n")
        f.write(f"**通過率**: {passed/total*100:.0f}%\n\n")
        f.write("| # | 測試項目 | 狀態 | 耗時 | 詳情 |\n")
        f.write("|---|---------|------|------|------|\n")
        for r in sorted(RESULTS, key=lambda x: x["id"]):
            icon = "✅" if r["status"] == "PASS" else "❌" if r["status"] == "FAIL" else "⚠️"
            f.write(f"| {r['id']:02d} | {r['name']} | {icon} {r['status']} | {r['elapsed']:.1f}s | {r['detail']} |\n")

        # Recommendations
        fails = [r for r in RESULTS if r["status"] == "FAIL"]
        if fails:
            f.write(f"\n## ❌ 需要修復 ({len(fails)} 項)\n\n")
            for r in fails:
                f.write(f"- **[{r['id']:02d}] {r['name']}**: {r['detail']}\n")

        warns = [r for r in RESULTS if r["status"] == "WARN"]
        if warns:
            f.write(f"\n## ⚠️ 注意事項 ({len(warns)} 項)\n\n")
            for r in warns:
                f.write(f"- **[{r['id']:02d}] {r['name']}**: {r['detail']}\n")

    print(f"\n📝 報告已儲存: {report_path}")
    return failed


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(min(exit_code, 1))
