# -*- coding: utf-8 -*-
"""
築未科技 — StuckDetector 卡住偵測
借鑑 OpenHands StuckDetector，自動偵測 AI Agent 是否陷入重複迴圈

偵測模式：
1. 完全重複 — 連續 N 次相同的 action/response
2. 語法錯誤迴圈 — 重複產生語法錯誤的程式碼
3. 空回應迴圈 — 連續空回應或拒絕回答
4. 震盪迴圈 — A→B→A→B 交替模式
5. 無進展 — 連續 N 次 action 但 observation 無變化

用法：
    from ai_modules.stuck_detector import StuckDetector

    detector = StuckDetector()

    # 每次 agent 步驟後檢查
    detector.add_step(action="edit file", observation="syntax error")
    if detector.is_stuck():
        print(f"Agent 卡住了: {detector.stuck_reason}")
        detector.suggest_recovery()
"""
import hashlib
import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

log = logging.getLogger("ai_modules.stuck_detector")


@dataclass
class AgentStep:
    """Agent 的一個步驟"""
    action: str               # 動作描述或類型
    observation: str = ""     # 結果/觀察
    action_hash: str = ""     # action 的 hash（用於比較）
    observation_hash: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    success: bool = True
    error_type: str = ""      # syntax_error / runtime_error / empty / timeout

    def __post_init__(self):
        if not self.action_hash:
            self.action_hash = hashlib.md5(self.action.encode()).hexdigest()[:8]
        if not self.observation_hash:
            self.observation_hash = hashlib.md5(self.observation.encode()).hexdigest()[:8]


@dataclass
class StuckAnalysis:
    """卡住分析結果"""
    is_stuck: bool = False
    stuck_type: str = ""          # exact_repeat / syntax_loop / empty_loop / oscillation / no_progress
    repeat_count: int = 0
    confidence: float = 0.0       # 0-1
    reason: str = ""
    suggestions: List[str] = field(default_factory=list)


class StuckDetector:
    """
    Agent 卡住偵測器

    配置：
    - max_history: 保留最近 N 步歷史
    - repeat_threshold: 連續重複 N 次視為卡住
    - oscillation_window: 震盪偵測視窗大小
    """

    SYNTAX_ERROR_PATTERNS = [
        "SyntaxError",
        "IndentationError",
        "TypeError",
        "NameError",
        "unterminated string",
        "invalid syntax",
        "unexpected token",
        "unexpected EOF",
    ]

    EMPTY_PATTERNS = [
        "I cannot",
        "I'm unable",
        "I don't know",
        "抱歉",
        "無法",
        "不確定",
    ]

    def __init__(self, max_history: int = 30, repeat_threshold: int = 3,
                 oscillation_window: int = 8):
        self.max_history = max_history
        self.repeat_threshold = repeat_threshold
        self.oscillation_window = oscillation_window
        self._history: List[AgentStep] = []
        self._last_analysis: Optional[StuckAnalysis] = None

    def add_step(self, action: str, observation: str = "",
                 success: bool = True, error_type: str = ""):
        """記錄一個步驟"""
        # 自動偵測 error_type
        if not error_type and not success:
            for pattern in self.SYNTAX_ERROR_PATTERNS:
                if pattern.lower() in observation.lower():
                    error_type = "syntax_error"
                    break

        step = AgentStep(
            action=action, observation=observation,
            success=success, error_type=error_type,
        )
        self._history.append(step)

        # 維持歷史大小
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history:]

        # 重新分析
        self._last_analysis = None

    def is_stuck(self) -> bool:
        """檢查是否卡住"""
        analysis = self.analyze()
        return analysis.is_stuck

    @property
    def stuck_reason(self) -> str:
        """取得卡住原因"""
        analysis = self.analyze()
        return analysis.reason

    def analyze(self) -> StuckAnalysis:
        """完整分析"""
        if self._last_analysis is not None:
            return self._last_analysis

        if len(self._history) < self.repeat_threshold:
            self._last_analysis = StuckAnalysis()
            return self._last_analysis

        # 按優先級檢查各種卡住模式
        checks = [
            self._check_exact_repeat,
            self._check_syntax_loop,
            self._check_empty_loop,
            self._check_oscillation,
            self._check_no_progress,
        ]

        for check in checks:
            result = check()
            if result.is_stuck:
                self._last_analysis = result
                log.warning(f"Agent 卡住偵測: {result.stuck_type} — {result.reason}")
                return result

        self._last_analysis = StuckAnalysis()
        return self._last_analysis

    def suggest_recovery(self) -> List[str]:
        """建議恢復策略"""
        analysis = self.analyze()
        return analysis.suggestions

    def reset(self):
        """重設歷史"""
        self._history.clear()
        self._last_analysis = None

    def get_history_summary(self) -> dict:
        """取得歷史摘要"""
        if not self._history:
            return {"steps": 0}

        action_counts = Counter(s.action_hash for s in self._history)
        error_counts = Counter(s.error_type for s in self._history if s.error_type)
        success_rate = sum(1 for s in self._history if s.success) / len(self._history)

        return {
            "steps": len(self._history),
            "unique_actions": len(action_counts),
            "most_common_action": action_counts.most_common(1)[0] if action_counts else None,
            "error_types": dict(error_counts),
            "success_rate": round(success_rate, 2),
            "is_stuck": self.is_stuck(),
        }

    # ===== 偵測方法 =====

    def _check_exact_repeat(self) -> StuckAnalysis:
        """偵測完全重複"""
        recent = self._history[-self.repeat_threshold:]
        if len(recent) < self.repeat_threshold:
            return StuckAnalysis()

        # 檢查 action hash 是否全部相同
        hashes = [s.action_hash for s in recent]
        if len(set(hashes)) == 1:
            return StuckAnalysis(
                is_stuck=True,
                stuck_type="exact_repeat",
                repeat_count=self.repeat_threshold,
                confidence=0.95,
                reason=f"連續 {self.repeat_threshold} 次完全相同的動作",
                suggestions=[
                    "嘗試不同的方法或策略",
                    "檢查前置條件是否正確",
                    "請求用戶釐清需求",
                    "切換到其他 Agent 處理",
                ],
            )
        return StuckAnalysis()

    def _check_syntax_loop(self) -> StuckAnalysis:
        """偵測語法錯誤迴圈"""
        recent = self._history[-5:]
        syntax_errors = [s for s in recent if s.error_type == "syntax_error"]

        if len(syntax_errors) >= 3:
            return StuckAnalysis(
                is_stuck=True,
                stuck_type="syntax_loop",
                repeat_count=len(syntax_errors),
                confidence=0.9,
                reason=f"最近 5 步中有 {len(syntax_errors)} 次語法錯誤",
                suggestions=[
                    "停止修改，重新閱讀完整檔案",
                    "使用更小的修改範圍",
                    "檢查縮排和括號配對",
                    "回退到最後正確的版本",
                ],
            )
        return StuckAnalysis()

    def _check_empty_loop(self) -> StuckAnalysis:
        """偵測空回應/拒絕迴圈"""
        recent = self._history[-4:]
        empty_count = 0

        for step in recent:
            obs = step.observation.lower()
            if not step.observation.strip():
                empty_count += 1
            elif any(p.lower() in obs for p in self.EMPTY_PATTERNS):
                empty_count += 1

        if empty_count >= 3:
            return StuckAnalysis(
                is_stuck=True,
                stuck_type="empty_loop",
                repeat_count=empty_count,
                confidence=0.85,
                reason=f"連續 {empty_count} 次空回應或拒絕",
                suggestions=[
                    "重新組織 prompt，提供更多上下文",
                    "拆解任務為更小的步驟",
                    "切換模型（本地 → 雲端或反之）",
                    "檢查是否觸發了安全過濾",
                ],
            )
        return StuckAnalysis()

    def _check_oscillation(self) -> StuckAnalysis:
        """偵測 A→B→A→B 震盪"""
        window = self._history[-self.oscillation_window:]
        if len(window) < 4:
            return StuckAnalysis()

        hashes = [s.action_hash for s in window]

        # 檢查 ABAB 模式
        for i in range(len(hashes) - 3):
            if (hashes[i] == hashes[i + 2] and
                    hashes[i + 1] == hashes[i + 3] and
                    hashes[i] != hashes[i + 1]):
                return StuckAnalysis(
                    is_stuck=True,
                    stuck_type="oscillation",
                    repeat_count=2,
                    confidence=0.8,
                    reason="偵測到 A↔B 交替震盪模式",
                    suggestions=[
                        "引入第三種策略打破震盪",
                        "增加約束條件",
                        "重新評估任務目標",
                        "回退到震盪開始前的狀態",
                    ],
                )
        return StuckAnalysis()

    def _check_no_progress(self) -> StuckAnalysis:
        """偵測無進展（action 不同但 observation 都一樣）"""
        recent = self._history[-5:]
        if len(recent) < 4:
            return StuckAnalysis()

        obs_hashes = [s.observation_hash for s in recent]
        action_hashes = [s.action_hash for s in recent]

        # action 不同但 observation 全部相同
        if len(set(obs_hashes)) == 1 and len(set(action_hashes)) > 1:
            return StuckAnalysis(
                is_stuck=True,
                stuck_type="no_progress",
                repeat_count=len(recent),
                confidence=0.75,
                reason="多次不同嘗試但結果完全相同，無進展",
                suggestions=[
                    "根本原因可能在其他地方",
                    "檢查環境/依賴是否正確",
                    "嘗試完全不同的方法",
                    "諮詢用戶是否有遺漏的上下文",
                ],
            )
        return StuckAnalysis()
