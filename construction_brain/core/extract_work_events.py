# -*- coding: utf-8 -*-
"""
營建自動化大腦 — 事件抽取引擎
語音/文字 → JSON 結構化事件列表

複用：
  - construction_mgmt/voice_service.py: structure_combined()
  - ai_service.py: Ollama 智慧路由
"""
import json
import logging
import os
import re
from datetime import date
from typing import Optional

log = logging.getLogger("construction_brain.extract")

OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11460").rstrip("/")
OLLAMA_MODEL = os.environ.get("CB_LLM_MODEL", "qwen3:32b")


def _call_llm(prompt: str, system: str = "", temperature: float = 0.1, max_tokens: int = 3000) -> str:
    """呼叫本地 Ollama LLM"""
    import urllib.request
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }
    try:
        req = urllib.request.Request(
            f"{OLLAMA_BASE}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("response", "")
    except Exception as e:
        log.error(f"LLM 呼叫失敗: {e}")
        return ""


def _extract_json(text: str) -> dict:
    """從 LLM 回覆中提取 JSON"""
    m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    try:
        start = text.index('{')
        end = text.rindex('}') + 1
        return json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        pass
    return {}


def extract_events(transcript: str, project_name: str = "", context: str = "") -> dict:
    """
    統一事件抽取：單次 LLM 呼叫同時完成
    1. daily_log — 施工日誌結構化
    2. safety_alerts — 工安風險判斷
    3. quality_checks — 品質檢查項目
    4. events — 關鍵事件列表

    Args:
        transcript: 語音辨識文字或手動輸入
        project_name: 工程名稱
        context: 額外上下文（如 YOLO 偵測結果、照片描述）

    Returns:
        {
            "daily_log": {...},
            "safety_alerts": [...],
            "quality_checks": [...],
            "events": [...]
        }
    """
    today = date.today().isoformat()

    system = f"""你是營建工程 AI 助手。工程名稱：{project_name}。
請一次完成以下 4 項任務，全部放在同一個 JSON 裡回傳：
1. daily_log — 施工日誌結構化（人力/機具/材料/工項）
2. safety_alerts — 工安風險判斷（severity: high/medium/low）
3. quality_checks — 品質檢查項目（result: V/X/空）
4. events — 關鍵事件列表（type: anomaly/milestone/change）

規則：
- 日期預設 {today}，天氣用「晴/陰/雨」
- day_status: working/rain_stop/holiday/other
- safety severity: high(立即停工)/medium(需改善)/low(提醒)
- 若口述中未提及某欄位，留空或空陣列
- 只回傳 JSON，不要其他文字。"""

    prompt = f"""口述內容：「{transcript}」"""
    if context:
        prompt += f"\n\n額外資訊：{context}"

    prompt += f"""

回傳 JSON：
```json
{{
  "daily_log": {{
    "log_date": "", "weather_am": "", "weather_pm": "",
    "temperature_high": null, "temperature_low": null,
    "day_status": "working", "work_description": "",
    "safety_notes": "", "quality_notes": "", "notes": "",
    "workers": [{{"trade": "", "count": 0, "company": ""}}],
    "equipment": [{{"equipment_name": "", "spec": "", "count": 1, "hours": 0}}],
    "materials": [{{"material_name": "", "spec": "", "unit": "", "quantity": 0, "supplier": ""}}],
    "work_items": [{{"item_name": "", "location": "", "quantity": 0, "unit": "", "progress_pct": 0}}]
  }},
  "safety_alerts": [
    {{"risk": "風險描述", "severity": "high", "action": "建議措施"}}
  ],
  "quality_checks": [
    {{"item": "檢查項目", "standard": "檢查標準", "result": "V", "notes": ""}}
  ],
  "events": [
    {{"type": "anomaly", "description": "事件描述", "priority": "high"}}
  ]
}}
```"""

    raw = _call_llm(prompt, system)
    result = _extract_json(raw)

    if result and "daily_log" in result:
        # 確保所有 key 存在
        for key in ("safety_alerts", "quality_checks", "events"):
            if key not in result:
                result[key] = []
        return result

    # fallback: 空結構
    return {
        "daily_log": {
            "log_date": today,
            "weather_am": "", "weather_pm": "",
            "day_status": "working",
            "work_description": transcript,
            "safety_notes": "", "quality_notes": "", "notes": "",
            "workers": [], "equipment": [], "materials": [], "work_items": [],
        },
        "safety_alerts": [],
        "quality_checks": [],
        "events": [],
    }


def extract_events_from_photo(
    image_description: str,
    yolo_detections: list = None,
    project_name: str = "",
) -> dict:
    """
    從照片分析結果抽取事件（搭配 YOLO + VLM 結果）

    Args:
        image_description: VLM 圖片描述
        yolo_detections: YOLO 偵測結果列表
        project_name: 工程名稱
    """
    context = ""
    if yolo_detections:
        det_summary = ", ".join([f"{d['class']}({d.get('confidence', 0):.0%})" for d in yolo_detections[:15]])
        context = f"YOLO 偵測到：{det_summary}"

    return extract_events(image_description, project_name=project_name, context=context)
