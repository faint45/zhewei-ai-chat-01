# -*- coding: utf-8 -*-
"""
營建自動化 — 語音辨識 + AI 結構化服務
支援：國語 / 閩南語 → Whisper 本地辨識 → LLM 結構化 → 日報表/檢查表/拍照/材料
"""
import json
import logging
import os
import tempfile
import time
from datetime import date
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# ===== 設定 =====
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "large-v3")
WHISPER_DEVICE = os.environ.get("WHISPER_DEVICE", "cuda")  # "cuda" or "cpu"
WHISPER_DEVICE_INDEX = int(os.environ.get("WHISPER_DEVICE_INDEX", "1"))  # GPU1=4060Ti for Whisper
WHISPER_COMPUTE_TYPE = os.environ.get("WHISPER_COMPUTE_TYPE", "float16")  # float16/int8
OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11460")
OLLAMA_MODEL = os.environ.get("VOICE_LLM_MODEL", "qwen3:32b")
VOICE_UPLOAD_DIR = Path(__file__).parent / "data" / "voice_uploads"
VOICE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_whisper_model = None


def get_whisper_model():
    """延遲載入 faster-whisper 模型（CTranslate2 加速，速度 x2-4）"""
    global _whisper_model
    if _whisper_model is None:
        try:
            from faster_whisper import WhisperModel
            log.info(f"載入 faster-whisper 模型: {WHISPER_MODEL} on {WHISPER_DEVICE}:{WHISPER_DEVICE_INDEX} ({WHISPER_COMPUTE_TYPE})")
            _whisper_model = WhisperModel(
                WHISPER_MODEL,
                device=WHISPER_DEVICE,
                device_index=WHISPER_DEVICE_INDEX,
                compute_type=WHISPER_COMPUTE_TYPE,
            )
            log.info("faster-whisper 模型載入完成")
        except ImportError:
            log.error("faster-whisper 未安裝，請執行: pip install faster-whisper")
            raise
    return _whisper_model


def transcribe_audio(audio_path: str, language: str = "auto") -> dict:
    """
    語音辨識核心（faster-whisper，CTranslate2 加速，速度 x2-4）
    language: "zh"(國語), "nan"(閩南語用Google), "auto"(自動偵測)
    回傳: { text, language, duration, segments }
    """
    start = time.time()
    path = Path(audio_path)

    if not path.exists():
        return {"text": "", "language": "unknown", "duration": 0, "error": "檔案不存在"}

    # faster-whisper 本地辨識
    try:
        model = get_whisper_model()
        kwargs = {"beam_size": 5, "vad_filter": True}
        if language and language not in ("auto", "nan"):
            kwargs["language"] = language

        segs_iter, info = model.transcribe(str(path), **kwargs)
        segments = []
        texts = []
        for seg in segs_iter:
            texts.append(seg.text.strip())
            segments.append({
                "start": round(seg.start, 1),
                "end": round(seg.end, 1),
                "text": seg.text.strip()
            })

        text = " ".join(texts)
        detected_lang = info.language or "zh"
        elapsed = round(time.time() - start, 2)
        log.info(f"faster-whisper 辨識完成: {len(text)} chars, {detected_lang}, {elapsed}s")

        return {
            "text": text,
            "language": detected_lang,
            "duration": elapsed,
            "segments": segments
        }
    except Exception as e:
        log.error(f"faster-whisper 辨識失敗: {e}")
        return {"text": "", "language": "unknown", "duration": 0, "error": str(e)}


def _call_ollama(prompt: str, system_prompt: str = "") -> str:
    """呼叫本地 Ollama LLM"""
    import urllib.request
    url = f"{OLLAMA_BASE}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 2000}
    }
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("response", "")
    except Exception as e:
        log.error(f"Ollama 呼叫失敗: {e}")
        return ""


def _extract_json(text: str) -> dict:
    """從 LLM 回覆中提取 JSON"""
    # 嘗試找 ```json ... ``` 區塊
    import re
    m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # 嘗試直接解析
    try:
        start = text.index('{')
        end = text.rindex('}') + 1
        return json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        pass
    return {}


# ===== AI 結構化引擎 =====

def _regex_parse_daily_log(transcript: str) -> dict:
    """
    正則表達式 fallback 解析器 — 從中文口述直接提取結構化欄位。
    不依賴 LLM，確保基本欄位一定能提取。
    """
    import re
    today = date.today().isoformat()
    t = transcript

    # 天氣
    weather_map = {"晴": "晴", "陰": "陰", "多雲": "多雲", "雨": "雨", "大雨": "大雨",
                   "小雨": "小雨", "陣雨": "陣雨", "颱風": "颱風", "霧": "霧"}
    weather = ""
    for k in weather_map:
        if k in t:
            weather = weather_map[k]
            break

    # 狀態
    day_status = "working"
    if any(k in t for k in ("停工", "雨停", "停止施工")):
        day_status = "rain_stop"
    elif any(k in t for k in ("休假", "放假", "國定假日")):
        day_status = "holiday"

    # 人力：「鋼筋工5人」「模板工3人」「小工2名」
    workers = []
    for m in re.finditer(r'([\u4e00-\u9fff]{1,6}(?:工|師|手|員|匠))\s*(\d+)\s*(?:人|名|位)', t):
        workers.append({"trade": m.group(1), "count": int(m.group(2)), "company": ""})

    # 機具：「挖土機1台」「吊車2部」「壓路機1台」
    equipment = []
    for m in re.finditer(r'([\u4e00-\u9fff]{1,8}(?:機|車|泵|鑽|吊|壓路機|發電機|抽水機))\s*(\d+)\s*(?:台|部|輛|組)', t):
        equipment.append({"equipment_name": m.group(1), "spec": "", "count": int(m.group(2)), "hours": 0})

    # 材料：「鋼筋SD420 2噸」「混凝土 5立方」「模板 30坪」
    materials = []
    for m in re.finditer(r'([\u4e00-\u9fffA-Za-z0-9]{1,12})\s+(\d+(?:\.\d+)?)\s*(噸|公噸|立方|m3|坪|才|包|袋|支|根|片|塊|組|車|公斤|kg|公升|L)', t):
        materials.append({"material_name": m.group(1).strip(), "spec": "", "unit": m.group(3), "quantity": float(m.group(2)), "supplier": ""})

    # 安全/品質
    safety = ""
    quality = ""
    for seg in re.split(r'[，。、；]', t):
        seg = seg.strip()
        if any(k in seg for k in ("安全", "安衛", "防護", "墜落", "護欄", "安全帽")):
            safety += seg + "；"
        if any(k in seg for k in ("品質", "品管", "試驗", "檢測", "合格", "不合格", "缺失")):
            quality += seg + "；"

    return {
        "log_date": today,
        "weather_am": weather,
        "weather_pm": weather,
        "temperature_high": None,
        "temperature_low": None,
        "day_status": day_status,
        "work_description": transcript,
        "safety_notes": safety.rstrip("；"),
        "quality_notes": quality.rstrip("；"),
        "notes": "",
        "workers": workers,
        "equipment": equipment,
        "materials": materials,
        "work_items": []
    }


def _merge_daily_log(llm_result: dict, regex_result: dict) -> dict:
    """合併 LLM 和 regex 結果 — LLM 優先，regex 補漏"""
    merged = {**regex_result}
    for key in ("log_date", "weather_am", "weather_pm", "temperature_high", "temperature_low",
                "day_status", "work_description", "safety_notes", "quality_notes", "notes"):
        llm_val = llm_result.get(key)
        if llm_val and llm_val != "" and llm_val is not None:
            merged[key] = llm_val
    for arr_key in ("workers", "equipment", "materials", "work_items"):
        llm_arr = llm_result.get(arr_key, [])
        regex_arr = regex_result.get(arr_key, [])
        merged[arr_key] = llm_arr if len(llm_arr) >= len(regex_arr) else regex_arr
    return merged


def structure_combined(transcript: str, project_name: str = "") -> dict:
    """
    統一 prompt：單次 LLM 呼叫同時完成「事件抽取 + 日報生成 + 工安判斷 + 品質檢查」
    相比分開呼叫 3 次 LLM，速度提升約 2-3x。
    回傳: { daily_log: {...}, safety_alerts: [...], quality_checks: [...], events: [...] }
    """
    today = date.today().isoformat()

    system = f"""你是營建工程 AI 助手。工程名稱：{project_name}。
請一次完成以下 4 項任務，全部放在同一個 JSON 裡回傳：
1. daily_log — 施工日誌結構化
2. safety_alerts — 工安風險判斷（列出所有潛在風險與嚴重等級 high/medium/low）
3. quality_checks — 品質檢查項目（列出應檢項目與合格判定）
4. events — 關鍵事件列表（異常/里程碑/變更）

規則：
- 日期預設 {today}，天氣用「晴/陰/雨」
- day_status: working/rain_stop/holiday/other
- safety severity: high(立即停工)/medium(需改善)/low(提醒)
- 若口述中未提及某欄位，留空或空陣列
- 只回傳 JSON，不要其他文字。"""

    prompt = f"""口述內容：「{transcript}」

回傳 JSON（嚴格遵循以下結構）：
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

    raw = _call_ollama(prompt, system)

    # 嘗試解析外層 JSON
    import re
    llm_result = _extract_json(raw)

    # 如果 LLM 回傳了統一結構
    if llm_result and "daily_log" in llm_result:
        regex_result = _regex_parse_daily_log(transcript)
        llm_result["daily_log"] = _merge_daily_log(llm_result["daily_log"], regex_result)
        return llm_result

    # fallback: 當作舊格式的 daily_log
    regex_result = _regex_parse_daily_log(transcript)
    if llm_result:
        merged = _merge_daily_log(llm_result, regex_result)
    else:
        merged = regex_result
    return {
        "daily_log": merged,
        "safety_alerts": [],
        "quality_checks": [],
        "events": []
    }


def structure_daily_log(transcript: str, project_name: str = "") -> dict:
    """
    將語音文字結構化為施工日誌欄位
    策略：LLM 結構化 + regex fallback，取兩者最佳結果合併
    現在內部使用 structure_combined() 統一呼叫，一次完成所有任務。
    """
    combined = structure_combined(transcript, project_name)
    return combined.get("daily_log", combined)


def structure_inspection(transcript: str, project_name: str = "") -> dict:
    """
    將語音文字結構化為自主檢查表
    回傳: { checklist_name, sub_project, inspection_date, inspection_location,
            items: [{item_name, check_standard, actual_result, check_result}],
            safety: [{description, check_result}],
            deficiency: [{notes}] }
    """
    today = date.today().isoformat()
    system = f"""你是營建工程自主檢查 AI 助手。工程名稱：{project_name}。
請將現場人員的口述內容，結構化為自主檢查表 JSON。
check_result 用 "V"(合格)、"X"(不合格)、""(未檢查)。"""

    prompt = f"""請將以下口述內容轉為自主檢查表 JSON：

口述內容：「{transcript}」

請回傳以下格式的 JSON：
```json
{{
  "checklist_name": "檢查表名稱",
  "sub_project": "分項工程",
  "inspection_date": "{today}",
  "inspection_location": "",
  "items": [{{"item_name": "檢查項目", "check_standard": "檢查標準", "actual_result": "實際結果", "check_result": "V"}}],
  "safety": [{{"description": "安全衛生項目", "check_result": "V"}}],
  "deficiency": [{{"notes": "缺失說明"}}]
}}
```"""

    raw = _call_ollama(prompt, system)
    result = _extract_json(raw)
    if not result:
        result = {
            "checklist_name": "語音檢查記錄",
            "inspection_date": today,
            "items": [{"item_name": transcript, "check_standard": "", "actual_result": "", "check_result": ""}],
            "safety": [], "deficiency": []
        }
    return result


def structure_photo_record(transcript: str, project_name: str = "") -> dict:
    """
    將語音描述結構化為拍照記錄
    回傳: { record_date, record_title,
            items: [{photo_date, location, item_name, design_value, measured_value, notes}] }
    """
    today = date.today().isoformat()
    system = f"""你是營建工程拍照記錄 AI 助手。工程名稱：{project_name}。
請將現場人員的口述照片描述，結構化為拍照記錄 JSON。"""

    prompt = f"""請將以下口述內容轉為拍照記錄 JSON：

口述內容：「{transcript}」

請回傳以下格式的 JSON：
```json
{{
  "record_date": "{today}",
  "record_title": "記錄標題",
  "items": [{{
    "photo_date": "{today}",
    "location": "拍攝位置",
    "item_name": "工項名稱",
    "design_value": "設計值",
    "measured_value": "實測值",
    "notes": "照片說明"
  }}]
}}
```"""

    raw = _call_ollama(prompt, system)
    result = _extract_json(raw)
    if not result:
        result = {
            "record_date": today,
            "record_title": "語音拍照記錄",
            "items": [{"photo_date": today, "location": "", "item_name": "", "notes": transcript}]
        }
    return result


def structure_material_entry(transcript: str, project_name: str = "") -> dict:
    """
    將語音描述結構化為材料進場記錄
    回傳: { entry_date, materials: [{material_name, spec, unit, quantity, supplier, notes}] }
    """
    today = date.today().isoformat()
    system = f"""你是營建工程材料管理 AI 助手。工程名稱：{project_name}。
請將現場人員的口述材料進場內容，結構化為材料記錄 JSON。"""

    prompt = f"""請將以下口述內容轉為材料進場記錄 JSON：

口述內容：「{transcript}」

請回傳以下格式的 JSON：
```json
{{
  "entry_date": "{today}",
  "materials": [{{
    "material_name": "材料名稱",
    "spec": "規格",
    "unit": "單位",
    "quantity": 0,
    "supplier": "供應商",
    "notes": ""
  }}]
}}
```"""

    raw = _call_ollama(prompt, system)
    result = _extract_json(raw)
    if not result:
        result = {
            "entry_date": today,
            "materials": [{"material_name": transcript, "spec": "", "unit": "", "quantity": 0, "supplier": ""}]
        }
    return result


# ===== 語音草稿管理 =====

def save_voice_draft(project_id: int, mode: str, transcript: str,
                     structured_data: dict, audio_filename: str = "") -> int:
    """儲存語音草稿到資料庫，回傳 draft_id"""
    from database import get_db
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO voice_drafts (project_id, mode, transcript, structured_data, audio_filename, status)
        VALUES (?, ?, ?, ?, ?, 'pending')
    """, (project_id, mode, transcript, json.dumps(structured_data, ensure_ascii=False), audio_filename))
    conn.commit()
    draft_id = cursor.lastrowid
    conn.close()
    return draft_id


def list_voice_drafts(project_id: int, status: str = None) -> list:
    """列出語音草稿"""
    from database import get_db
    conn = get_db()
    cursor = conn.cursor()
    if status:
        cursor.execute("SELECT * FROM voice_drafts WHERE project_id=? AND status=? ORDER BY created_at DESC", (project_id, status))
    else:
        cursor.execute("SELECT * FROM voice_drafts WHERE project_id=? ORDER BY created_at DESC", (project_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    for r in rows:
        if r.get('structured_data'):
            try:
                r['structured_data'] = json.loads(r['structured_data'])
            except:
                pass
    return rows


def get_voice_draft(draft_id: int) -> dict:
    """取得單筆語音草稿"""
    from database import get_db
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM voice_drafts WHERE id=?", (draft_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        d = dict(row)
        if d.get('structured_data'):
            try:
                d['structured_data'] = json.loads(d['structured_data'])
            except:
                pass
        return d
    return None


def update_voice_draft(draft_id: int, structured_data: dict = None, status: str = None) -> bool:
    """更新語音草稿（檢核後修改結構化資料或狀態）"""
    from database import get_db
    conn = get_db()
    cursor = conn.cursor()
    updates = []
    params = []
    if structured_data is not None:
        updates.append("structured_data = ?")
        params.append(json.dumps(structured_data, ensure_ascii=False))
    if status:
        updates.append("status = ?")
        params.append(status)
    if not updates:
        conn.close()
        return False
    params.append(draft_id)
    cursor.execute(f"UPDATE voice_drafts SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def confirm_voice_draft(draft_id: int) -> dict:
    """
    確認語音草稿 → 寫入正式資料表
    回傳: { success, message, target_id }
    """
    from database import (create_daily_log, create_inspection_checklist,
                          create_photo_record)

    draft = get_voice_draft(draft_id)
    if not draft:
        return {"success": False, "message": "草稿不存在"}
    if draft['status'] == 'confirmed':
        return {"success": False, "message": "草稿已確認過"}

    mode = draft['mode']
    data = draft['structured_data']
    project_id = draft['project_id']

    try:
        if mode == 'daily_log':
            log_id = create_daily_log(project_id, data)
            update_voice_draft(draft_id, status='confirmed')
            return {"success": True, "message": f"施工日誌已建立 (ID: {log_id})", "target_id": log_id}

        elif mode == 'inspection':
            checklist_id = create_inspection_checklist(project_id, data)
            update_voice_draft(draft_id, status='confirmed')
            return {"success": True, "message": f"自主檢查表已建立 (ID: {checklist_id})", "target_id": checklist_id}

        elif mode == 'photo':
            record_id = create_photo_record(project_id, data)
            update_voice_draft(draft_id, status='confirmed')
            return {"success": True, "message": f"拍照記錄已建立 (ID: {record_id})", "target_id": record_id}

        elif mode == 'material':
            # 材料進場寫入日誌附表
            update_voice_draft(draft_id, status='confirmed')
            return {"success": True, "message": "材料進場記錄已確認（需手動關聯到日誌）"}

        else:
            return {"success": False, "message": f"未知模式: {mode}"}

    except Exception as e:
        log.error(f"確認草稿失敗: {e}")
        return {"success": False, "message": str(e)}
