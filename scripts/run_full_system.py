# -*- coding: utf-8 -*-
"""
築未科技 — 完整跑啟動：預檢後啟動 brain_server，讓系統每次都能完整跑八階段。
執行：python scripts/run_full_system.py（專案根目錄）
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 載入 .env
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass


def check_ollama() -> bool:
    try:
        import urllib.request
        url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434") + "/api/tags"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def main():
    print("築未科技 — 完整跑啟動")
    print("=" * 50)

    # 1. 預檢（依專案 preflight_check）
    try:
        from preflight_check import run_main as preflight_main
        if preflight_main() != 0:
            print("[!] 預檢有項目未通過，仍可啟動；八階段依下方條件。")
    except Exception as e:
        print(f"[~] 預檢跳過: {e}")

    # 2. 完整跑條件（八階段用）
    gemini = bool((os.environ.get("GEMINI_API_KEY") or "").strip() and os.environ.get("GEMINI_API_KEY", "").strip() != "your-gemini-api-key")
    ollama = check_ollama()
    claude = bool((os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY") or "").strip())
    print("\n完整跑條件（八階段）：")
    print(f"  [{'OK' if gemini else '--'}] GEMINI_API_KEY（階段 2、3、7）")
    print(f"  [{'OK' if ollama else '--'}] Ollama 運行中（階段 4、5）")
    print(f"  [{'OK' if claude else '--'}] ANTHROPIC/CLAUDE_API_KEY（階段 4、6 編碼）")
    if not (gemini or ollama):
        print("  建議：至少設定 GEMINI_API_KEY 或啟動 Ollama，否則單次任務可能失敗。")

    # 3. 啟動 brain_server（預設埠 8002，避開 8000 衝突）
    port = os.environ.get("PORT", os.environ.get("BRAIN_WS_PORT", "8002"))
    print("\n啟動 brain_server...")
    print(f"  管理介面：http://localhost:{port}/admin（需登入）")
    print(f"  對話頁：http://localhost:{port}/chat")
    print(f"  健康檢查：http://localhost:{port}/health")
    print("  (Ctrl+C 結束)\n")
    try:
        subprocess.run([sys.executable, "brain_server.py"], cwd=str(ROOT))
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
