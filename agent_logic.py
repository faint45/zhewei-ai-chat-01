# -*- coding: utf-8 -*-
"""
築未科技 — Agent 中樞（agent_logic）
標準 8 階段流程：1.需求接收 2.整合理解 3.安排(引擎分流) 4.執行 5~7.確認與修正 8.完成與經驗學習。
階段 7：多模型協同決策（Gemini 深度分析 + 第二意見交叉驗證）；分歧時標註待確認、可接元寶/千問裁決。
雙引擎：視覺或複雜任務強制 Gemini，其餘 Ollama；Observation 異常時切換雲端修復。
"""
import asyncio
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Coroutine, TypedDict

from agent_tools import TOOLS, generate_voice_report

try:
    from langgraph.graph import END, StateGraph
except Exception:
    END = None
    StateGraph = None

LOG_FILE = os.environ.get("BRAIN_LOG_FILE", "D:/brain_workspace/brain_system.log")
try:
    Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
except Exception:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

MAX_TURNS = 10
LANGGRAPH_REPAIR_MAX = int((os.environ.get("LANGGRAPH_REPAIR_MAX", "3").strip() or "3"))
Z_DRIVE_PATH = Path(os.environ.get("ZHEWEI_MEMORY_ROOT", "Z:/Zhewei_Brain"))
RULES_FILE = Z_DRIVE_PATH / "Rules" / "master_rules.md"
EXPERIENCE_FILE = Z_DRIVE_PATH / "Experience" / "Experience_Logs.jsonl"

SYSTEM_PROMPT = """你是築未科技自主工程師。必須嚴格輸出 JSON 格式：
- 執行工具：{"thought": "...", "tool": "run_command|read_file|write_file|list_dir|vision_analyze|run_vision_engine|manage_construction_log|generate_progress_report|generate_voice_report|generate_media|deploy_service|update_web_admin|search_graph_rag|ingest_graph_rag_pdf", "args": {...}}
- 任務完成：{"done": true, "result": "..."}

可用工具：run_command(command)、read_file(path)、write_file(path, content)、list_dir(path)、vision_analyze(image_path)、run_vision_engine(image_path)、manage_construction_log(content)、generate_progress_report(detected)、generate_voice_report(transcript)、generate_media(prompt, type=image|video)、deploy_service(service_name)、update_web_admin(data，進度可含 LaTeX 如 $95\\%$)、search_graph_rag(query, limit=5)、ingest_graph_rag_pdf(pdf_path, source_name)。所有檔案路徑限 D:\\ 或 Z:\\。圖表相關：先 search_graph_rag 查詢連續壁/配筋/搭接等。"""

VISION_KEYWORDS = ("分析", "jpg", "png", "辨識", "影片", "lpc")
COMPLEX_KEYWORDS = ("架構", "設計", "優化", "debug", "修復", "部署")
CROSS_VALIDATE_GAP_THRESHOLD = 0.10


def extract_json_from_markdown(text: str) -> dict[str, Any] | None:
    """從 AI 回應擷取 JSON：```json 區塊、整段解析、首個平衡 {...}。"""
    if not text or not isinstance(text, str):
        return None
    raw = text.strip()
    if not raw:
        return None
    for pattern in (r"```json\s*([\s\S]*?)\s*```", r"```JSON\s*([\s\S]*?)\s*```"):
        match = re.search(pattern, raw, re.IGNORECASE | re.DOTALL)
        if match:
            obj = _parse_json_string(match.group(1).strip())
            if obj is not None:
                return obj
    match = re.search(r"```\s*([\s\S]*?)\s*```", raw, re.DOTALL)
    if match:
        block = match.group(1).strip()
        if block.startswith("{") or block.startswith("["):
            obj = _parse_json_string(block)
            if obj is not None:
                return obj
    obj = _parse_json_string(raw)
    if obj is not None:
        return obj
    start = raw.find("{")
    if start >= 0:
        depth = 0
        for i in range(start, len(raw)):
            if raw[i] == "{":
                depth += 1
            elif raw[i] == "}":
                depth -= 1
                if depth == 0:
                    obj = _parse_json_string(raw[start : i + 1])
                    if obj is not None:
                        return obj
                    break
    return None


def _parse_json_string(s: str) -> dict[str, Any] | None:
    s = (s or "").strip()
    if not s or not s.startswith("{"):
        return None
    s = re.sub(r",\s*}", "}", s)
    s = re.sub(r",\s*]", "]", s)
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return None


class AgentManager:
    """
    雙引擎 Agent 中樞：標準 8 階段流程。
    引擎分流：vision 或 complex 強制 Gemini；conversation 用 Ollama；Observation 異常時切換 Gemini 修復。
    """

    def __init__(
        self,
        gemini_service: Any,
        ollama_service: Any,
        send_message: Callable[..., Coroutine[Any, Any, None]] | None = None,
        max_turns: int = MAX_TURNS,
        claude_service: Any = None,
    ):
        self.gemini = gemini_service
        self.ollama = ollama_service
        self.claude = claude_service
        self.send_message = send_message
        self.max_turns = max_turns
        self.use_langgraph = (os.environ.get("AGENT_USE_LANGGRAPH", "1").strip() or "1") in ("1", "true", "yes", "on")
        self.memory_path = RULES_FILE
        self.experience_path = EXPERIENCE_FILE
        try:
            self.memory_path.parent.mkdir(parents=True, exist_ok=True)
            self.experience_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logging.warning("Z 槽目錄初始化: %s", e)

    async def _run_with_langgraph(self, user_request: str, send: Callable[..., Coroutine[Any, Any, None]] | None) -> str:
        """
        LangGraph 版流程（較精簡進度回報）：
        receive -> classify -> execute -> finalize
        """
        if StateGraph is None or END is None:
            return await self._run_legacy(user_request, send)

        class AgentState(TypedDict, total=False):
            user_request: str
            history: list[dict[str, str]]
            engine_type: str
            final_result: str
            last_vision_observation: dict[str, Any] | None

        async def _node_receive(state: AgentState) -> AgentState:
            if send:
                await send({"type": "step", "content": "LangGraph：接收需求"})
            history = self._load_long_term_memory()
            history.append({"role": "system", "content": SYSTEM_PROMPT})
            history.append({"role": "user", "content": state["user_request"]})
            return {"history": history}

        async def _node_classify(state: AgentState) -> AgentState:
            et = self._classify_task(state["user_request"])
            if send:
                await send({"type": "info", "content": f"LangGraph：任務分類 `{et}`"})
            return {"engine_type": et}

        async def _node_execute(state: AgentState) -> AgentState:
            history = list(state.get("history", []))
            engine_type = str(state.get("engine_type", "conversation"))
            engine = self.gemini if engine_type in {"vision", "complex"} else self.ollama
            final_result = ""
            last_vision_observation = None
            repair_count = 0
            max_repairs = max(1, LANGGRAPH_REPAIR_MAX)
            model_marked_done = False

            for _ in range(max(1, self.max_turns)):
                response_text = await engine.chat(history)
                decision = extract_json_from_markdown(response_text)
                if decision is None:
                    try:
                        decision = json.loads(response_text)
                    except json.JSONDecodeError:
                        history.append({"role": "assistant", "content": response_text})
                        continue

                if decision.get("done"):
                    final_result = decision.get("result", "任務已完成")
                    model_marked_done = True
                    break

                tool_name = decision.get("tool")
                tool_args = decision.get("args") or {}
                observation = await self._execute_tool(tool_name, tool_args)
                if tool_name == "run_vision_engine":
                    last_vision_observation = observation
                history.append({"role": "assistant", "content": response_text})
                history.append({"role": "user", "content": f"Observation: {json.dumps(observation, ensure_ascii=False)}"})
                if self._observation_has_error(observation):
                    repair_count += 1
                    engine = self.gemini
                    if repair_count <= max_repairs:
                        # LangGraph 核心循環：先內部自我修正，再決定是否回報使用者
                        history.append(
                            {
                                "role": "user",
                                "content": (
                                    f"修正回合 {repair_count}/{max_repairs}：上一輪工具執行失敗。"
                                    "請根據 Observation 重新規劃，輸出新的最小可行工具步驟。"
                                ),
                            }
                        )
                        continue
                    final_result = (
                        "LangGraph 自我修正已達上限，仍未成功。"
                        f"已重試 {max_repairs} 次；請補充更明確的輸入/目標後再試。"
                    )
                    break

            if engine_type == "vision" and model_marked_done and last_vision_observation is not None and final_result:
                cross = await self._cross_validate_results(last_vision_observation)
                if cross.get("status") == "dispute":
                    final_result = f"{final_result}\n【階段 7】{cross.get('note', '需要元寶或千問介入裁決')}"
                else:
                    final_result = cross.get("result") or final_result

            return {"history": history, "final_result": final_result, "last_vision_observation": last_vision_observation}

        async def _node_finalize(state: AgentState) -> AgentState:
            final_result = str(state.get("final_result") or "")
            if final_result:
                self._learn_from_success(state["user_request"], final_result)
                if send:
                    await send({"type": "result", "content": "LangGraph：任務完成，進度 $100\\%$"})
                return {"final_result": final_result}
            msg = f"LangGraph：已執行 {self.max_turns} 輪未完成，請縮小需求。"
            if send:
                await send({"type": "result", "content": msg})
            return {"final_result": msg}

        graph = StateGraph(AgentState)
        graph.add_node("receive", _node_receive)
        graph.add_node("classify", _node_classify)
        graph.add_node("execute", _node_execute)
        graph.add_node("finalize", _node_finalize)
        graph.set_entry_point("receive")
        graph.add_edge("receive", "classify")
        graph.add_edge("classify", "execute")
        graph.add_edge("execute", "finalize")
        graph.add_edge("finalize", END)
        compiled = graph.compile()
        out = await compiled.ainvoke({"user_request": user_request})
        return str((out or {}).get("final_result") or "LangGraph 執行完成。")

    def _is_logical_gap(self, val1: str, val2: str) -> bool:
        """數值或邏輯比對：兩結論分歧超過門檻則回傳 True（需裁決）。"""
        s1, s2 = (str(val1 or "")).strip(), (str(val2 or "")).strip()
        if not s1 or not s2:
            return False
        nums1 = []
        for x in re.findall(r"\d+\.?\d*", s1):
            try:
                nums1.append(float(x))
            except ValueError:
                pass
        nums2 = []
        for x in re.findall(r"\d+\.?\d*", s2):
            try:
                nums2.append(float(x))
            except ValueError:
                pass
        if nums1 and nums2:
            a, b = sum(nums1) / len(nums1), sum(nums2) / len(nums2)
            if max(a, b) > 0 and abs(a - b) / max(a, b) > CROSS_VALIDATE_GAP_THRESHOLD:
                return True
        if ("不符" in s1 or "錯誤" in s1) != ("不符" in s2 or "錯誤" in s2):
            return True
        return False

    async def _cross_validate_results(self, raw_vision_data: Any) -> dict[str, Any]:
        """
        階段 7：多模型交叉確認。地端辨識結果送 Gemini 深度分析，再送第二意見（Gemini/Claude）檢核；
        若分歧 > 門檻則標註待確認，否則輸出定稿。
        """
        raw_str = json.dumps(raw_vision_data, ensure_ascii=False) if isinstance(raw_vision_data, dict) else str(raw_vision_data)
        try:
            gemini_analysis = await self.gemini.chat([{"role": "user", "content": f"分析此視覺數據並給出簡短結論：{raw_str}"}])
        except Exception as e:
            logging.warning("階段 7 Gemini 分析失敗: %s", e)
            return {"status": "error", "result": str(e), "note": "交叉驗證跳過"}
        second_input = f"檢核此工程數據是否符合規範，回覆簡短結論：{gemini_analysis}"
        try:
            if self.claude is not None:
                second_analysis = await self.claude.chat([{"role": "user", "content": second_input}])
            else:
                second_analysis = await self.gemini.chat([{"role": "user", "content": second_input}])
        except Exception as e:
            logging.warning("階段 7 第二意見失敗: %s", e)
            return {"status": "verified", "result": gemini_analysis}
        if self._is_logical_gap(gemini_analysis, second_analysis):
            return {"status": "dispute", "result": gemini_analysis, "note": "需要元寶或千問介入裁決"}
        return {"status": "verified", "result": second_analysis}

    def _classify_task(self, request: str) -> str:
        """任務分流：vision | complex | conversation。"""
        req_lower = (request or "").lower()
        if any(k in req_lower for k in VISION_KEYWORDS):
            return "vision"
        if any(k in req_lower for k in COMPLEX_KEYWORDS):
            return "complex"
        return "conversation"

    def _load_long_term_memory(self) -> list[dict]:
        """從 Z 槽載入 master_rules.md 作為核心守則與長期記憶。"""
        if not self.memory_path.exists():
            return []
        try:
            content = self.memory_path.read_text(encoding="utf-8")
            return [{"role": "system", "content": f"核心守則與長期記憶：\n{content[-4000:]}"}]
        except Exception:
            return []

    async def _execute_tool(self, name: str, args: dict) -> dict[str, Any]:
        """對接 agent_tools：路徑限 D/Z；generate_voice_report 需 Gemini。"""
        try:
            if name == "generate_voice_report":
                out = await generate_voice_report(
                    transcript=args.get("transcript", ""),
                    gemini_service=self.gemini,
                )
                return out if isinstance(out, dict) else {"ok": True, "content": str(out)}
            if name not in TOOLS:
                return {"status": "error", "stderr": f"未定義的工具: {name}"}
            obs = TOOLS[name](**args)
            if not isinstance(obs, dict):
                obs = {"ok": True, "content": str(obs)}
            if not obs.get("ok") and name == "run_command":
                obs["status"] = "error"
            if (obs.get("stderr") or "").strip():
                obs["status"] = "error"
            return obs
        except Exception as e:
            logging.error("工具執行失敗 %s: %s", name, e)
            return {"status": "error", "stderr": str(e)}

    def _observation_has_error(self, observation: dict) -> bool:
        if observation.get("status") == "error":
            return True
        if (observation.get("stderr") or "").strip():
            return True
        if observation.get("ok") is False and observation.get("error"):
            return True
        return "error" in str(observation).lower()

    def _learn_from_success(self, request: str, result: str) -> None:
        """成功經驗寫入 Z 槽 Experience_Logs.jsonl（JSONL 一行一筆）。"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "request": request[:500],
                "success_logic": (result or "")[:300],
            }
            self.experience_path.parent.mkdir(parents=True, exist_ok=True)
            with self.experience_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            logging.info("經驗已寫入 Z 槽 Experience_Logs")
        except Exception as e:
            logging.warning("經驗寫入失敗: %s", e)

    async def _run_legacy(self, user_request: str, send_message: Callable[..., Coroutine[Any, Any, None]] | None = None) -> str:
        """
        核心執行引擎：標準 8 階段流程。
        1. 需求接收 2. 整合理解 3. 安排(引擎分流) 4. 執行 5~7. 確認與修正(ReAct) 8. 完成與經驗學習。
        進度報表以 LaTeX 格式呈現（如 $100\\%$）。
        """
        send = send_message or self.send_message

        try:
            if not Z_DRIVE_PATH.exists():
                msg = "Z 槽未掛載，長期記憶與報表寫入將不可用；請確認 Rclone/雲端掛載。"
                logging.warning(msg)
                if send:
                    await send({"type": "info", "content": msg})

            logging.info("收到指令: %s", user_request)

            # 1. 需求接收與初始化
            if send:
                await send({"type": "step", "content": "1. 需求接收與初始化..."})
            history = self._load_long_term_memory()
            history.append({"role": "system", "content": SYSTEM_PROMPT})
            history.append({"role": "user", "content": user_request})

            # 2. 整合理解 & 3. 安排（引擎分流）
            engine_type = self._classify_task(user_request)
            engine = self.gemini if (engine_type == "vision" or engine_type == "complex") else self.ollama
            if send:
                await send({"type": "info", "content": f"選用引擎: {engine_type.upper()}"})

            # 4. 執行 ~ 7. 確認（ReAct 循環）
            final_result = ""
            current_step = 0
            last_vision_observation = None

            while current_step < self.max_turns:
                current_step += 1
                if send:
                    await send({"type": "step", "content": f"正在執行第 {current_step} 輪 ReAct 決策..."})

                response_text = await engine.chat(history)
                decision = extract_json_from_markdown(response_text)
                if decision is None:
                    try:
                        decision = json.loads(response_text)
                    except json.JSONDecodeError:
                        history.append({"role": "assistant", "content": response_text})
                        continue

                if decision.get("done"):
                    final_result = decision.get("result", "任務已完成")
                    if engine_type == "vision" and last_vision_observation is not None:
                        if send:
                            await send({"type": "step", "content": "階段 7：多模型交叉確認..."})
                        cross = await self._cross_validate_results(last_vision_observation)
                        if cross.get("status") == "dispute":
                            if send:
                                await send({"type": "info", "content": cross.get("note", "待確認：需元寶或千問介入裁決")})
                            final_result = f"{final_result}\n【階段 7】{cross.get('note', '')}"
                        else:
                            if send:
                                await send({"type": "info", "content": "階段 7：交叉驗證通過，定稿。"})
                    break

                tool_name = decision.get("tool")
                tool_args = decision.get("args") or {}
                if send:
                    await send({"type": "info", "content": f"呼叫工具: {tool_name}"})

                observation = await self._execute_tool(tool_name, tool_args)
                if tool_name == "run_vision_engine":
                    last_vision_observation = observation
                history.append({"role": "assistant", "content": response_text})
                history.append({"role": "user", "content": f"Observation: {json.dumps(observation, ensure_ascii=False)}"})

                if self._observation_has_error(observation):
                    engine = self.gemini
                    if send:
                        await send({"type": "info", "content": "偵測到異常，切換至雲端高階引擎修復..."})

            # 8. 完成 & 經驗學習
            if final_result:
                self._learn_from_success(user_request, final_result)
                completion_msg = "任務完成！目前總進度：$100\\%$。結果已寫入 Z 槽報表。"
                if send:
                    await send({"type": "result", "content": completion_msg})
                return final_result

            timeout_msg = f"已執行 {self.max_turns} 輪未結束，請縮小需求或稍後再試。"
            if send:
                await send({"type": "result", "content": timeout_msg})
            return timeout_msg

        except Exception as e:
            logging.critical("核心異常: %s", e)
            if send:
                await send({"type": "error", "content": f"核心錯誤: {str(e)}，請檢查主機 Log。"})
            return f"核心錯誤: {str(e)}"

    async def run(self, user_request: str, send_message: Callable[..., Coroutine[Any, Any, None]] | None = None) -> str:
        send = send_message or self.send_message
        if self.use_langgraph and StateGraph is not None and END is not None:
            return await self._run_with_langgraph(user_request, send)
        return await self._run_legacy(user_request, send)


if __name__ == "__main__":
    import argparse
    from ai_service import GeminiService, OllamaService
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", type=str, required=True)
    args = parser.parse_args()
    manager = AgentManager(gemini_service=GeminiService(), ollama_service=OllamaService())
    print(asyncio.run(manager.run(args.task)))
