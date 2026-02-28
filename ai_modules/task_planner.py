# -*- coding: utf-8 -*-
"""
築未科技 — TaskPlanner 任務指派引擎
從「二分法(think/execute)」升級為「多維度精準指派」

設計理念：像老闆管理員工
┌────────────────────────────────────────────────┐
│  客戶說「你好」     → 實習生(4b) 秒回           │
│  客戶問「鋼筋搭接」 → 專才(brain-v3) 做專事     │
│  客戶要「設計報告」 → 主管(32b) 起草+品檢        │
│  客戶要「法規分析」 → 主管(32b)+知識庫+雲端覆核  │
└────────────────────────────────────────────────┘

五層任務分級：
  L0 greeting  — 問候/閒聊      → 4b 秒回（0 成本）
  L1 quick     — 簡單問答/翻譯   → 4b 或 8b
  L2 domain    — 領域專業問題    → zhewei-brain-v3 專才
  L3 complex   — 分析/報告/程式  → 32b + QualityGate
  L4 expert    — 法規/跨域/長文  → 32b + RAG + 雲端覆核
"""

import os
import re
import json
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

log = logging.getLogger("ai_modules.task_planner")


# ═══════════════════════════════════════════════════
# 1. 任務分級定義
# ═══════════════════════════════════════════════════

@dataclass
class TaskPlan:
    """一份完整的任務執行計畫 — 交代清楚再開工"""
    level: str                          # L0-L4
    label: str                          # greeting/quick/domain/complex/expert
    model_chain: List[str]              # 依序嘗試的模型 key
    system_prompt: str = ""             # 任務專用 system prompt
    rag_query: str = ""                 # RAG 檢索用的 query（空=不檢索）
    rag_collections: List[str] = field(default_factory=list)  # 指定知識庫
    output_format: str = ""             # 期望輸出格式描述
    quality_gate: bool = False          # 是否啟用品質門檻
    quality_min_score: float = 6.0      # 最低品質分數
    escalation: bool = False            # 品質不足是否自動升級
    max_retries: int = 0               # 重試次數
    temperature: float = 0.7            # 模型溫度
    domain: str = ""                    # 領域標籤（construction/payment/ai/general）
    thinking: bool = False              # 是否注入 thinking protocol
    log_for_training: bool = False      # 是否記錄到訓練日誌（頻繁任務自動微調用）


# ═══════════════════════════════════════════════════
# 2. 領域偵測器
# ═══════════════════════════════════════════════════

class DomainDetector:
    """偵測任務所屬領域 — 決定派哪個專才"""

    DOMAINS = {
        "construction": {
            "keywords": [
                "鋼筋", "搭接", "混凝土", "模板", "施工", "品管", "品質",
                "監造", "S-curve", "S曲線", "進度", "工安", "安衛",
                "營建", "工程", "建築", "結構", "大地", "基礎",
                "日報", "估驗", "計價", "合約", "變更設計",
                "預算", "工項", "PCCES", "公共工程",
                "混凝土強度", "抗壓", "試體", "養護",
                "鷹架", "模板支撐", "開挖", "回填",
            ],
            "model": "brain",   # zhewei-brain-v3 專才
            "rag_collections": ["construction_kb"],
            "system_prompt": (
                "你是築未科技的資深營建工程顧問。\n"
                "具備土木技師專業，熟悉台灣公共工程品質管理規範。\n"
                "回答時引用具體規範條文，給出可操作的專業建議。"
            ),
        },
        "payment": {
            "keywords": [
                "金流", "ECPay", "綠界", "付款", "訂閱", "退款",
                "支付", "JKoPay", "街口", "Alipay", "支付寶",
                "CheckMacValue", "回調", "callback", "訂單",
            ],
            "model": "brain",
            "rag_collections": ["payment_kb"],
            "system_prompt": (
                "你是金流整合專家，熟悉 ECPay/JKoPay/Alipay API。\n"
                "回答時注意安全性（CheckMacValue 驗證、HTTPS、防重放）。"
            ),
        },
        "ai_system": {
            "keywords": [
                "RAG", "Agent", "向量", "embedding", "知識庫",
                "Ollama", "ComfyUI", "Forge", "微調", "蒸餾",
                "LoRA", "GGUF", "模型路由", "thinking protocol",
                "Microagent", "prompt", "LLM", "token",
            ],
            "model": "brain",
            "rag_collections": ["ai_kb"],
            "system_prompt": (
                "你是 AI 系統架構師，擅長本地 LLM 部署、RAG、Agent 設計。\n"
                "回答時提供可執行的程式碼和架構建議。"
            ),
        },
        "water_alert": {
            "keywords": [
                "水位", "洪水", "預警", "雷達", "LoRa",
                "觀測站", "水情", "降雨", "河川", "防汛",
            ],
            "model": "ollama",
            "rag_collections": ["water_alert_kb"],
            "system_prompt": "你是水情預警系統專家，熟悉 FMCW 雷達水位計和 LoRa 通訊。",
        },
        "legal": {
            "keywords": [
                "法規", "法律", "合約", "契約", "條款",
                "個資法", "營造業法", "建築法", "採購法",
                "仲裁", "訴訟", "賠償", "責任", "保固",
            ],
            "model": "ollama",   # 32b 起草
            "rag_collections": ["legal_kb"],
            "system_prompt": (
                "你是工程法律顧問，熟悉台灣營造業相關法規。\n"
                "回答時務必引用法條編號，區分確定事實和法律意見。"
            ),
            "needs_escalation": True,  # 品質不足時升級到雲端
        },
    }

    @classmethod
    def detect(cls, text: str) -> Tuple[str, float]:
        """
        偵測文本所屬領域和信心度。
        Returns: (domain_name, confidence)
        """
        lower = text.lower()
        scores = {}
        for domain, cfg in cls.DOMAINS.items():
            hits = sum(1 for kw in cfg["keywords"] if kw.lower() in lower)
            if hits > 0:
                scores[domain] = hits
        if not scores:
            return ("general", 0.0)
        best = max(scores, key=scores.get)
        confidence = min(scores[best] / 3.0, 1.0)
        return (best, confidence)


# ═══════════════════════════════════════════════════
# 3. TaskPlanner 主引擎
# ═══════════════════════════════════════════════════

class TaskPlanner:
    """
    任務指派引擎 — 精準分類 + 完整執行計畫

    升級自 SmartAIService._classify_task()：
    - 舊：二分法（think/execute）
    - 新：五層分級 + 領域路由 + Pre-Planning
    """

    # L0: 問候/閒聊
    _GREETING_PATTERNS = [
        r"^(你好|hello|hi|嗨|hey|哈囉|早安|午安|晚安|good\s*morning|good\s*night)[\s!！。？?]*$",
        r"^(謝謝|感謝|thank|thanks|ok|好的|了解|收到|掰掰|bye)[\s!！。？?]*$",
        r"^(嗯|哦|喔|噢|是|對|沒錯)[\s!！。？?]*$",
    ]

    # L1: 簡單問答
    _QUICK_KEYWORDS = [
        "翻譯", "translate", "幾點", "天氣", "日期",
        "是什麼", "what is", "define", "意思",
        "列出", "list", "幫我查", "簡單",
    ]

    # L3: 複雜任務
    _COMPLEX_KEYWORDS = [
        "分析", "報告", "設計", "架構", "規劃", "策略",
        "完整", "全面", "詳細", "深入", "evaluate",
        "比較", "compare", "研究", "review", "audit",
        "程式", "code", "python", "function", "class",
        "debug", "修復", "fix", "優化", "refactor",
    ]

    # L4: 專家級
    _EXPERT_KEYWORDS = [
        "法規分析", "合約審查", "結構計算", "預算編列",
        "完整報告", "deep analysis", "施工規範", "品質計畫",
        "風險評估", "工程估驗", "安全衛生計畫",
    ]

    def __init__(self):
        self.domain_detector = DomainDetector()
        self._task_log_path = Path(os.environ.get(
            "TASK_LOG_DIR",
            os.path.join(os.path.dirname(__file__), "..", "brain_workspace", "task_logs")
        ))
        self._task_log_path.mkdir(parents=True, exist_ok=True)

    def plan(self, messages: list) -> TaskPlan:
        """
        分析 messages，產出完整的 TaskPlan。

        流程：
        1. 提取最後一條使用者訊息
        2. 判斷任務等級（L0-L4）
        3. 偵測領域
        4. 組合執行計畫（模型鏈、SOP、RAG、品質門檻）
        """
        last_user = ""
        total_len = 0
        for m in messages:
            total_len += len(m.get("content") or "")
            if m.get("role") == "user":
                last_user = (m.get("content") or "").strip()

        lower = last_user.lower()

        # ── Step 1: L0 問候偵測 ──
        for pat in self._GREETING_PATTERNS:
            if re.match(pat, last_user, re.IGNORECASE):
                return TaskPlan(
                    level="L0", label="greeting",
                    model_chain=["ollama_fast"],
                    system_prompt="你是友善的 AI 助手，簡短回應問候。",
                    temperature=0.9,
                )

        # ── Step 2: 領域偵測 ──
        domain, domain_conf = self.domain_detector.detect(last_user)
        domain_cfg = DomainDetector.DOMAINS.get(domain, {})

        # ── Step 3: 任務等級判定 ──
        expert_score = sum(1 for kw in self._EXPERT_KEYWORDS if kw.lower() in lower)
        complex_score = sum(1 for kw in self._COMPLEX_KEYWORDS if kw.lower() in lower)
        quick_score = sum(1 for kw in self._QUICK_KEYWORDS if kw.lower() in lower)

        # L4: 專家級
        if expert_score >= 1 or (domain in ("legal",) and complex_score >= 1):
            return self._plan_expert(last_user, domain, domain_cfg)

        # L3: 複雜任務
        if complex_score >= 2 or len(last_user) > 300 or total_len > 2000:
            return self._plan_complex(last_user, domain, domain_cfg)

        # L2: 領域專業（有明確領域 + 中等信心）
        if domain != "general" and domain_conf >= 0.3:
            return self._plan_domain(last_user, domain, domain_cfg)

        # L1: 簡單問答
        if quick_score >= 1 or len(last_user) < 50:
            return TaskPlan(
                level="L1", label="quick",
                model_chain=["ollama_fast", "ollama"],
                temperature=0.5,
                domain="general",
            )

        # 預設: L2 通用（交給 32b）
        return TaskPlan(
            level="L2", label="domain",
            model_chain=["ollama", "ollama_fast"],
            thinking=True,
            temperature=0.5,
            domain="general",
        )

    def _plan_domain(self, query: str, domain: str, cfg: dict) -> TaskPlan:
        """L2 領域專業計畫"""
        model_key = cfg.get("model", "ollama")
        if model_key == "brain":
            chain = ["brain", "ollama", "ollama_fast"]
        else:
            chain = ["ollama", "brain", "ollama_fast"]

        return TaskPlan(
            level="L2", label="domain",
            model_chain=chain,
            system_prompt=cfg.get("system_prompt", ""),
            rag_query=query,
            rag_collections=cfg.get("rag_collections", []),
            quality_gate=False,
            temperature=0.3,
            domain=domain,
            thinking=True,
            log_for_training=True,
        )

    def _plan_complex(self, query: str, domain: str, cfg: dict) -> TaskPlan:
        """L3 複雜任務計畫 — 32b 起草 + 品質檢查"""
        chain = ["ollama", "brain", "deepseek", "minimax", "claude"]

        return TaskPlan(
            level="L3", label="complex",
            model_chain=chain,
            system_prompt=cfg.get("system_prompt", ""),
            rag_query=query if cfg.get("rag_collections") else "",
            rag_collections=cfg.get("rag_collections", []),
            output_format="結構化回答：先概述，再分點詳述，最後總結。",
            quality_gate=True,
            quality_min_score=6.5,
            max_retries=1,
            temperature=0.2,
            domain=domain,
            thinking=True,
            log_for_training=True,
        )

    def _plan_expert(self, query: str, domain: str, cfg: dict) -> TaskPlan:
        """L4 專家級計畫 — 32b + RAG + 品檢 + 雲端覆核"""
        chain = ["ollama", "deepseek", "minimax", "claude"]

        sys_prompt = cfg.get("system_prompt", "")
        if not sys_prompt:
            sys_prompt = (
                "你是跨領域資深顧問。回答時：\n"
                "1. 引用具體法規條文或技術規範\n"
                "2. 區分確定事實和專業意見\n"
                "3. 提供可操作的具體建議\n"
                "4. 標明需要進一步確認的項目"
            )

        return TaskPlan(
            level="L4", label="expert",
            model_chain=chain,
            system_prompt=sys_prompt,
            rag_query=query,
            rag_collections=cfg.get("rag_collections", []),
            output_format="專業報告格式：背景→分析→結論→建議→參考依據",
            quality_gate=True,
            quality_min_score=7.0,
            escalation=True,
            max_retries=1,
            temperature=0.1,
            domain=domain,
            thinking=True,
            log_for_training=True,
        )

    def log_task(self, plan: TaskPlan, query: str, response: str,
                 model_used: str, duration_ms: int):
        """
        記錄任務到訓練日誌 — 供 Auto-Training Pipeline 分析。

        頻繁出現的 domain+level 組合 → 自動產生微調資料集。
        """
        if not plan.log_for_training:
            return
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "level": plan.level,
            "label": plan.label,
            "domain": plan.domain,
            "model_used": model_used,
            "duration_ms": duration_ms,
            "query_preview": query[:200],
            "response_preview": response[:200],
            "quality_gate": plan.quality_gate,
        }
        try:
            log_file = self._task_log_path / f"tasks_{time.strftime('%Y%m')}.jsonl"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            log.warning(f"Failed to log task: {e}")


# ═══════════════════════════════════════════════════
# 4. Pre-Planning — 執行前準備
# ═══════════════════════════════════════════════════

class PrePlanner:
    """
    任務執行前的準備工作 — 不是丟一句「去做」

    職責：
    1. 注入 system prompt（角色定位）
    2. 注入 RAG 知識（參考資料）
    3. 注入 output format（輸出模板）
    4. 設定 QualityGate（品質標準）
    """

    @staticmethod
    def prepare_messages(plan: TaskPlan, original_messages: list,
                         rag_context: str = "") -> list:
        """
        根據 TaskPlan 準備完整的 messages。

        原始 messages + system prompt + RAG context + output hints
        """
        prepared = list(original_messages)

        # 1. 注入 system prompt
        if plan.system_prompt:
            # 檢查是否已有 system message
            has_system = any(m.get("role") == "system" for m in prepared)
            if has_system:
                # 追加到現有 system prompt
                for i, m in enumerate(prepared):
                    if m.get("role") == "system":
                        prepared[i] = {
                            "role": "system",
                            "content": m["content"] + "\n\n" + plan.system_prompt
                        }
                        break
            else:
                prepared.insert(0, {"role": "system", "content": plan.system_prompt})

        # 2. 注入 RAG 知識
        if rag_context:
            rag_msg = (
                "以下是從知識庫檢索到的相關資料，請優先參考：\n"
                "---\n" + rag_context + "\n---\n"
                "如果資料不足，請依據專業知識補充，但需標明哪些是知識庫資料、哪些是推論。"
            )
            # 插入到 system 之後、user 之前
            insert_idx = 1 if prepared and prepared[0].get("role") == "system" else 0
            prepared.insert(insert_idx, {"role": "system", "content": rag_msg})

        # 3. 注入 output format hint
        if plan.output_format:
            # 在最後一條 user message 後面追加格式提示
            for i in range(len(prepared) - 1, -1, -1):
                if prepared[i].get("role") == "user":
                    prepared[i] = {
                        "role": "user",
                        "content": (
                            prepared[i]["content"] + "\n\n"
                            f"【輸出格式要求】{plan.output_format}"
                        )
                    }
                    break

        # 4. Thinking Protocol 注入
        if plan.thinking:
            try:
                from ai_modules.thinking_protocol import inject_thinking
                mode = "lite" if plan.level in ("L2", "L3") else "full"
                domain_param = plan.domain if plan.domain != "general" else None
                prepared = inject_thinking(prepared, mode=mode, domain=domain_param)
            except ImportError:
                pass

        return prepared


# ═══════════════════════════════════════════════════
# 5. Auto-Training Analyzer — 頻繁任務自動發現
# ═══════════════════════════════════════════════════

class TrainingAnalyzer:
    """
    分析任務日誌，找出適合微調的高頻任務類型。

    原則：
    - 某個 domain 任務量 > 50 筆/月 → 建議微調專用模型
    - 品質門檻通過率 < 80% → 需要加強該領域訓練資料
    - 回應時間 > 5 秒的高頻任務 → 應該用更小的專用模型
    """

    def __init__(self, log_dir: str = ""):
        self.log_dir = Path(log_dir) if log_dir else Path(
            os.environ.get("TASK_LOG_DIR",
                           os.path.join(os.path.dirname(__file__), "..", "brain_workspace", "task_logs"))
        )

    def analyze(self) -> Dict[str, Any]:
        """分析最近的任務日誌，產出訓練建議。"""
        entries = []
        for f in sorted(self.log_dir.glob("tasks_*.jsonl")):
            try:
                with open(f, encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if line:
                            entries.append(json.loads(line))
            except Exception:
                continue

        if not entries:
            return {"total": 0, "suggestions": [], "domains": {}}

        # 按 domain 統計
        domain_stats = {}
        for e in entries:
            d = e.get("domain", "general")
            if d not in domain_stats:
                domain_stats[d] = {"count": 0, "avg_duration_ms": 0, "models": {}}
            domain_stats[d]["count"] += 1
            domain_stats[d]["avg_duration_ms"] += e.get("duration_ms", 0)
            model = e.get("model_used", "unknown")
            domain_stats[d]["models"][model] = domain_stats[d]["models"].get(model, 0) + 1

        for d in domain_stats:
            c = domain_stats[d]["count"]
            domain_stats[d]["avg_duration_ms"] = round(domain_stats[d]["avg_duration_ms"] / c) if c else 0

        # 產出建議
        suggestions = []
        for d, stats in domain_stats.items():
            if stats["count"] >= 50:
                suggestions.append({
                    "domain": d,
                    "action": "finetune",
                    "reason": f"{d} 已累積 {stats['count']} 筆任務，建議微調專用模型",
                    "priority": "high" if stats["count"] >= 100 else "medium",
                })
            if stats["avg_duration_ms"] > 5000 and stats["count"] >= 20:
                suggestions.append({
                    "domain": d,
                    "action": "optimize",
                    "reason": f"{d} 平均回應 {stats['avg_duration_ms']}ms，建議用更小專用模型",
                    "priority": "high",
                })

        return {
            "total": len(entries),
            "domains": domain_stats,
            "suggestions": suggestions,
        }


# ═══════════════════════════════════════════════════
# 6. 便捷實例
# ═══════════════════════════════════════════════════

planner = TaskPlanner()
pre_planner = PrePlanner()
training_analyzer = TrainingAnalyzer()
