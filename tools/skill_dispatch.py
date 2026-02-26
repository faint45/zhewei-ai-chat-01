"""
築未科技 - 技能調度（營建測量／成本／歸檔）
僅使用清單內技能；參數不足回傳 {"error": "缺失參數: [參數名]"}；嚴禁自行複雜計算，委託技能執行。
"""
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

BASE = Path(__file__).parent.resolve()

# 技能清單與必備參數
SKILL_SPEC = {
    "survey_check": {"data": list},      # 檢核測量數據誤差
    "cost_calc": {"items": list},        # 計算營建材料成本
    "file_archive": {"path": str},       # 本地檔案自動歸檔
}


def survey_check(data: list) -> dict:
    """檢核測量數據誤差。data 為數值列表，回傳是否合格與最大偏差。"""
    if not data or not isinstance(data, list):
        return {"error": "缺失參數: data", "valid": False}
    nums = []
    for x in data:
        try:
            nums.append(float(x))
        except (TypeError, ValueError):
            return {"error": "data 須為數值列表", "valid": False}
    if not nums:
        return {"error": "data 不可為空", "valid": False}
    mean = sum(nums) / len(nums)
    deviations = [abs(x - mean) for x in nums]
    max_dev = max(deviations)
    # 營建常用容差 0.01（可依規範調整）
    tolerance = 0.01
    valid = max_dev <= tolerance
    return {
        "valid": valid,
        "mean": round(mean, 6),
        "max_deviation": round(max_dev, 6),
        "tolerance": tolerance,
        "count": len(nums),
    }


def cost_calc(items: list) -> dict:
    """計算營建材料成本。items 為 [{"name": str, "qty": number, "unit_price": number}, ...]。"""
    if not items or not isinstance(items, list):
        return {"error": "缺失參數: items", "total": 0}
    total = 0.0
    breakdown = []
    for i, row in enumerate(items):
        if not isinstance(row, dict):
            return {"error": f"items[{i}] 須為物件", "total": 0}
        name = row.get("name", "")
        try:
            qty = float(row.get("qty", 0))
            unit_price = float(row.get("unit_price", 0))
        except (TypeError, ValueError):
            return {"error": f"items[{i}] qty/unit_price 須為數值", "total": 0}
        subtotal = qty * unit_price
        total += subtotal
        breakdown.append({
            "name": name,
            "qty": qty,
            "unit_price": unit_price,
            "subtotal": round(subtotal, 2),
        })
    return {
        "total": round(total, 2),
        "breakdown": breakdown,
        "count": len(items),
    }


def file_archive(path: str) -> dict:
    """本地檔案自動歸檔：複製到專案內 archive/YYYY-MM-DD/ 目錄。"""
    if not path or not isinstance(path, str):
        return {"error": "缺失參數: path", "archived": False}
    path = path.strip()
    if not path:
        return {"error": "缺失參數: path", "archived": False}
    try:
        src = (BASE / path).resolve()
        if not src.exists():
            return {"error": f"檔案不存在: {path}", "archived": False}
        if not str(src).startswith(str(BASE)):
            return {"error": "禁止歸檔專案外路徑", "archived": False}
        if src.is_dir():
            return {"error": "僅支援檔案歸檔，不支援目錄", "archived": False}
        day = datetime.now().strftime("%Y-%m-%d")
        archive_dir = BASE / "archive" / day
        archive_dir.mkdir(parents=True, exist_ok=True)
        dest = archive_dir / src.name
        if dest.exists():
            base = dest.stem
            ext = dest.suffix
            n = 1
            while dest.exists():
                dest = archive_dir / f"{base}_{n}{ext}"
                n += 1
        shutil.copy2(src, dest)
        return {
            "archived": True,
            "from": path,
            "to": str(dest.relative_to(BASE)),
        }
    except Exception as e:
        return {"error": str(e), "archived": False}


_SKILL_IMPL = {
    "survey_check": survey_check,
    "cost_calc": cost_calc,
    "file_archive": file_archive,
}


def dispatch(payload: dict) -> dict:
    """
    執行準則：
    - 僅使用 SKILL_SPEC 清單中存在的技能。
    - 參數不足時直接回傳 {"error": "缺失參數: [參數名]"}。
    - 嚴禁自行計算複雜數學，委託技能執行。
    輸入範例：{"call": "survey_check", "params": {"data": [0.002, 0.006, 0.001]}}
    """
    if not isinstance(payload, dict):
        return {"error": "payload 須為物件"}
    call = payload.get("call")
    params = payload.get("params")
    if not call:
        return {"error": "缺失參數: call"}
    if call not in SKILL_SPEC:
        return {"error": f"未知技能: {call}，僅可使用: {list(SKILL_SPEC.keys())}"}
    if params is None:
        params = {}
    if not isinstance(params, dict):
        return {"error": "params 須為物件"}
    required = SKILL_SPEC[call]
    missing = [k for k in required if k not in params or params[k] is None]
    if missing:
        return {"error": f"缺失參數: {missing}"}
    for k, typ in required.items():
        v = params.get(k)
        if typ is list and not isinstance(v, list):
            return {"error": f"參數 {k} 須為陣列"}
        if typ is str and not isinstance(v, str):
            return {"error": f"參數 {k} 須為字串"}
    try:
        fn = _SKILL_IMPL[call]
        if call == "survey_check":
            result = fn(params["data"])
        elif call == "cost_calc":
            result = fn(params["items"])
        else:
            result = fn(params["path"])
        return {"result": result} if "error" not in result else result
    except Exception as e:
        return {"error": str(e)}
