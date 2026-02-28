# -*- coding: utf-8 -*-
"""
Opus 4 vs 本地模型 Benchmark
測試題：分散式限流器（8/10 難度）
呼叫本地 Ollama qwen3:32b，比較回答品質
"""
import json
import time
import urllib.request
import sys

OLLAMA_BASE = "http://localhost:11460"

CHALLENGE_PROMPT = """你是資深後端架構師。請設計並實作一個「分散式滑動窗口限流器」，要求：

1. **滑動窗口演算法**：不是固定窗口，要精確的滑動窗口（sorted set 或環形緩衝）
2. **Redis 原子操作**：用 Redis LUA script 實現原子性的滑動窗口計算（ZADD + ZREMRANGEBYSCORE + ZCARD）
3. **降級機制**：Redis 掛掉時自動降級為本地記憶體限流，不能讓服務整個掛掉
4. **自動恢復**：Redis 恢復後自動切回分散式模式（需有探針偵測）
5. **多租戶支援**：每個 tenant 根據訂閱方案（free: 60req/min, pro: 600req/min, enterprise: 6000req/min）動態調整限額
6. **FastAPI middleware**：提供可直接掛載的 ASGI middleware
7. **完整型別提示 + async + 錯誤處理 + logging**

請輸出完整可執行的 Python 程式碼（單一檔案），並在最後解釋：
- 為什麼選滑動窗口而非令牌桶？
- 高併發下的競態條件如何避免？
- Redis LUA script 的原子性保證是什麼？"""

def call_ollama(model: str, prompt: str, timeout: int = 300) -> tuple[str, float, float]:
    """呼叫 Ollama API，回傳 (response, elapsed_sec, tok_per_sec)"""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_predict": 8000,
            "num_ctx": 8192,
        },
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_BASE}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    elapsed = time.perf_counter() - t0
    response_text = result.get("response", "")
    eval_count = result.get("eval_count", 0)
    tok_per_sec = eval_count / elapsed if elapsed > 0 else 0
    return response_text, elapsed, tok_per_sec


def check_ollama():
    """檢查 Ollama 是否在線"""
    try:
        req = urllib.request.Request(f"{OLLAMA_BASE}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [m.get("name", "") for m in data.get("models", [])]
            return True, models
    except Exception as e:
        return False, str(e)


def main():
    print("=" * 70)
    print("  Opus 4 vs 本地模型 Benchmark")
    print("  測試題：分散式滑動窗口限流器（難度 8/10）")
    print("=" * 70)

    # 1. 檢查 Ollama
    print("\n[1/4] 檢查 Ollama 狀態...")
    online, models = check_ollama()
    if not online:
        print(f"  ❌ Ollama 未啟動: {models}")
        print(f"  請確認 Ollama 運行在 {OLLAMA_BASE}")
        sys.exit(1)
    print(f"  ✅ Ollama 在線，可用模型: {len(models)} 個")

    # 找到 qwen3:32b 或最大的模型
    target_model = None
    for m in models:
        if "qwen3:32b" in m or "qwen3:latest" in m:
            target_model = m
            break
    if not target_model:
        for m in models:
            if "qwen" in m and ("32" in m or "14" in m):
                target_model = m
                break
    if not target_model:
        # fallback to first available
        target_model = models[0] if models else "qwen3:32b"
    print(f"  🎯 測試模型: {target_model}")

    # 2. 送出挑戰
    print(f"\n[2/4] 送出挑戰題給 {target_model}...")
    print(f"  （預計需要 60-180 秒，請耐心等待...）")

    try:
        response, elapsed, tps = call_ollama(target_model, CHALLENGE_PROMPT, timeout=600)
    except Exception as e:
        print(f"  ❌ 呼叫失敗: {e}")
        sys.exit(1)

    print(f"  ✅ 回答完成！")
    print(f"  ⏱️  耗時: {elapsed:.1f} 秒")
    print(f"  🚀 速度: {tps:.1f} tok/s")
    print(f"  📝 回答長度: {len(response)} 字元")

    # 3. 儲存結果
    print("\n[3/4] 儲存結果...")
    output = {
        "model": target_model,
        "challenge": "分散式滑動窗口限流器（難度 8/10）",
        "elapsed_sec": round(elapsed, 1),
        "tok_per_sec": round(tps, 1),
        "response_length": len(response),
        "response": response,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    out_path = "d:/zhe-wei-tech/scripts/benchmark_result.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"  📄 已儲存: {out_path}")

    # 4. 輸出回答
    print("\n[4/4] 本地模型回答：")
    print("=" * 70)
    print(response)
    print("=" * 70)

    # 摘要
    print(f"\n📊 Benchmark 摘要")
    print(f"  模型: {target_model}")
    print(f"  耗時: {elapsed:.1f}s | 速度: {tps:.1f} tok/s | 長度: {len(response)} 字元")
    print(f"  結果已存: {out_path}")
    print(f"\n  → 接下來由 Opus 4 對比評分")


if __name__ == "__main__":
    main()
