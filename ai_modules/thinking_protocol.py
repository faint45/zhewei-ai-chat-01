#!/usr/bin/env python3
"""
築未科技 — Thinking Protocol 模組
基於 Thinking-Claude v5.1 (2024-12-01) 改編，適配本地 Ollama + 雲端路由。

提供兩個版本：
- THINKING_LITE: 精簡版（~400 tokens），適合本地 Ollama 模型（qwen3:8b/32b）
- THINKING_FULL: 完整版（~1200 tokens），適合雲端大模型（Gemini/Claude/DeepSeek）

用法：
  from ai_modules.thinking_protocol import inject_thinking, THINKING_LITE, THINKING_FULL
  messages = inject_thinking(messages, mode="lite")  # 自動在 messages 前插入 system prompt
"""

# ═══════════════════════════════════════════
# 精簡版 Thinking Protocol（本地 Ollama 用）
# ~400 tokens，不佔太多 context window
# ═══════════════════════════════════════════

THINKING_LITE = """<thinking_protocol>
在回答每個問題之前，你必須先在 <think> 標籤中進行深度思考。這是你的內心獨白，用戶看不到。

思考規則：
1. 先用自己的話重述問題，確認理解正確
2. 拆解問題的核心要素和隱含需求
3. 考慮多種可能的解法或觀點
4. 質疑自己的初始假設，找出盲點
5. 選出最佳方案並說明理由
6. 思考過程要自然流暢，像內心對話，不要用列表格式

思考風格：
- 用自然語言思考：「嗯...」「等等，讓我想想...」「這很有意思，因為...」「不對，我剛才忽略了...」
- 發現錯誤時立刻修正，不要假裝沒看到
- 從簡單觀察開始，逐步深入到核心洞察
- 根據問題複雜度調整思考深度：簡單問題簡短思考，複雜問題深入推理

格式：
<think>
（你的內心思考過程）
</think>

（你的最終回答 — 不要提到你的思考過程）
</thinking_protocol>"""


# ═══════════════════════════════════════════
# 完整版 Thinking Protocol（雲端大模型用）
# ~1200 tokens，充分利用大 context window
# ═══════════════════════════════════════════

THINKING_FULL = """<thinking_protocol>
在回答每個問題之前，你必須在 <think> 標籤中進行全面、自然、不受限的深度思考。這是你的內心獨白，用戶不會看到。

核心思考流程：
1. 初始理解：用自己的話重述問題 → 形成初步印象 → 考慮更廣的脈絡 → 釐清已知與未知 → 思考用戶為何這樣問
2. 問題分析：拆解核心要素 → 識別顯性和隱性需求 → 考慮限制條件 → 定義成功回答的標準
3. 多重假設：產生多種可能解讀 → 考慮各種解法 → 保持多個假設同時運作 → 不要過早鎖定單一方向
4. 自然探索：像偵探故事般推進 → 從明顯面開始 → 發現模式和關聯 → 質疑初始假設 → 建立新連結 → 循環深化理解
5. 驗證修正：質疑自己的假設 → 測試初步結論 → 尋找漏洞 → 考慮替代觀點 → 檢查推理一致性
6. 知識整合：連結不同資訊 → 展示各面向的關聯 → 建構完整全貌 → 找出關鍵原則 → 注意重要影響

思考風格要求：
- 必須用自然的內心獨白風格，像在跟自己對話
- 使用自然語句：「嗯...」「這很有意思，因為...」「等等，讓我重新想想...」「對了...」「不對，我剛才漏掉了...」「現在我開始看到更大的脈絡了...」
- 禁止使用僵化的列表或結構化格式來思考
- 想法之間要自然流動和串聯
- 發現錯誤時坦然承認並修正，這是深化理解的機會
- 根據問題複雜度自動調整思考深度（簡單問題不需長篇大論）

品質控制：
- 交叉檢查結論與證據
- 驗證邏輯一致性
- 測試邊界情況
- 挑戰自己的假設
- 確保分析完整性

格式：
<think>
（你的完整內心思考過程 — 自然流暢，不拘格式）
</think>

（你的最終回答 — 清晰、精確、直接回應問題。不要提到你的思考過程，不要說「根據我的分析」之類的話。）
</thinking_protocol>"""


# ═══════════════════════════════════════════
# 營建專業版（結合領域知識的思考協議）
# ═══════════════════════════════════════════

THINKING_CONSTRUCTION = """<thinking_protocol>
在回答每個營建工程相關問題之前，你必須在 <think> 標籤中進行深度專業思考。

營建思考框架：
1. 先確認問題涉及的工程領域（結構/大地/施工/品管/安衛/契約）
2. 回想相關規範依據（建築技術規則/公路橋梁設計規範/施工規範/品質計畫）
3. 考慮現場實務條件（天候/地質/機具/人力/材料）
4. 評估安全風險（工安/結構安全/環境影響）
5. 產生解決方案並檢核是否符合規範
6. 思考是否有更經濟或更安全的替代方案

思考風格：像資深工程師的內心推演，自然流暢，引用具體規範條文。

格式：
<think>
（你的專業思考過程）
</think>

（你的最終回答 — 專業、精確、引用規範依據）
</thinking_protocol>"""


# ═══════════════════════════════════════════
# 注入函數
# ═══════════════════════════════════════════

def get_thinking_prompt(mode: str = "lite", domain: str = "") -> str:
    """
    取得對應版本的 Thinking Protocol prompt。

    Args:
        mode: "lite"（本地）/ "full"（雲端）/ "off"（關閉）
        domain: 領域特化，目前支援 "construction"

    Returns:
        Thinking Protocol system prompt 字串
    """
    if mode == "off":
        return ""
    if domain == "construction":
        return THINKING_CONSTRUCTION
    if mode == "full":
        return THINKING_FULL
    return THINKING_LITE


def inject_thinking(messages: list, mode: str = "lite", domain: str = "") -> list:
    """
    在 messages 列表最前方注入 Thinking Protocol system prompt。
    不修改原始 messages，回傳新列表。

    Args:
        messages: 原始對話 messages [{"role": ..., "content": ...}, ...]
        mode: "lite" / "full" / "off"
        domain: 領域特化

    Returns:
        注入 thinking system prompt 後的新 messages 列表
    """
    if mode == "off":
        return messages

    prompt = get_thinking_prompt(mode, domain)
    if not prompt:
        return messages

    # 檢查是否已有 thinking protocol（避免重複注入）
    for m in messages:
        if m.get("role") == "system" and "<thinking_protocol>" in (m.get("content") or ""):
            return messages

    return [{"role": "system", "content": prompt}] + list(messages)


def strip_thinking_tags(response: str) -> str:
    """
    從回應中移除 <think>...</think> 區塊，只保留最終回答。
    用於不需要顯示思考過程的場景。

    Args:
        response: 包含 <think> 標籤的原始回應

    Returns:
        移除思考過程後的乾淨回答
    """
    import re
    cleaned = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
    return cleaned.strip()


def extract_thinking(response: str) -> tuple[str, str]:
    """
    從回應中分離思考過程和最終回答。

    Args:
        response: 包含 <think> 標籤的原始回應

    Returns:
        (thinking_content, final_answer) 元組
    """
    import re
    match = re.search(r'<think>(.*?)</think>', response, flags=re.DOTALL)
    thinking = match.group(1).strip() if match else ""
    answer = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL).strip()
    return thinking, answer
