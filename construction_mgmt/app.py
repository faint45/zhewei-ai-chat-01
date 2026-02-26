"""
營建自動化管理系統 — FastAPI 主程式
本地運行 port 8020
"""
import os
import sys
import json
import uuid
import shutil
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from database import (init_db, get_db, create_project, get_project, list_projects,
                     update_project, delete_project, add_document, add_personnel, get_stats,
                     import_contract_items, get_contract_items, update_contract_item,
                     add_contract_item, delete_contract_item, get_contract_summary,
                     create_daily_log, get_daily_log, get_daily_log_by_date,
                     list_daily_logs, update_daily_log, delete_daily_log,
                     get_daily_log_stats,
                     import_regulations, list_regulations, get_regulation_articles,
                     create_inspection_checklist, list_inspection_checklists,
                     get_inspection_checklist, update_inspection_checklist, delete_inspection_checklist,
                     create_photo_record, list_photo_records,
                     get_photo_record, update_photo_record, delete_photo_record,
                     import_schedule_tasks, list_schedule_tasks,
                     import_scurve_data, get_scurve_data, update_scurve_actual,
                     list_submittal_control, create_submittal_control, update_submittal_control, delete_submittal_control, import_submittal_control,
                     list_test_control, create_test_control, update_test_control, delete_test_control, import_test_control,
                     list_petty_cash, create_petty_cash, update_petty_cash, delete_petty_cash, get_petty_cash_summary,
                     list_payment_estimates, create_payment_estimate, get_payment_estimate, delete_payment_estimate, import_payment_estimates,
                     list_special_terms, get_special_term, search_special_terms, import_special_terms,
                     list_tech_specs, get_tech_spec, search_tech_specs, import_tech_specs,
                     list_traffic_manual, get_traffic_manual_item, search_traffic_manual, import_traffic_manual,
                     list_project_plans, get_project_plan_item, search_project_plans, import_project_plans,
                     UPLOAD_DIR, ensure_dirs)
from file_parser import parse_uploaded_file, parse_contract_xls

app = FastAPI(
    title="營建自動化管理系統",
    description="Construction Management System - 本地優先，雲端同步",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 靜態檔案
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATE_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ===== 頁面路由 =====

@app.get("/", response_class=HTMLResponse)
async def index_page():
    """主頁面"""
    html_path = os.path.join(TEMPLATE_DIR, "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>營建自動化管理系統</h1><p>模板檔案不存在</p>")


# ===== API: 工程管理 =====

@app.get("/api/projects")
async def api_list_projects(status: Optional[str] = None):
    """列出所有工程"""
    projects = list_projects(status)
    return {"success": True, "data": projects, "count": len(projects)}


@app.post("/api/projects")
async def api_create_project(data: dict):
    """建立新工程"""
    if not data.get("project_name"):
        raise HTTPException(status_code=400, detail="工程名稱為必填")

    project_id = create_project(data)
    return {"success": True, "project_id": project_id, "message": "工程建立成功"}


@app.get("/api/projects/{project_id}")
async def api_get_project(project_id: int):
    """取得單一工程完整資料"""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="工程不存在")
    return {"success": True, "data": project}


@app.put("/api/projects/{project_id}")
async def api_update_project(project_id: int, data: dict):
    """更新工程資料"""
    existing = get_project(project_id)
    if not existing:
        raise HTTPException(status_code=404, detail="工程不存在")

    success = update_project(project_id, data)
    return {"success": success, "message": "工程更新成功" if success else "無變更"}


@app.delete("/api/projects/{project_id}")
async def api_delete_project(project_id: int):
    """刪除工程"""
    success = delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="工程不存在")
    return {"success": True, "message": "工程已刪除"}


# ===== API: 文件上傳與解析 =====

@app.post("/api/projects/{project_id}/upload")
async def api_upload_document(
    project_id: int,
    file: UploadFile = File(...),
    doc_type: str = Form("contract"),
    description: str = Form("")
):
    """上傳文件到指定工程"""
    existing = get_project(project_id)
    if not existing:
        raise HTTPException(status_code=404, detail="工程不存在")

    # 儲存檔案
    ensure_dirs()
    project_upload_dir = os.path.join(UPLOAD_DIR, str(project_id))
    os.makedirs(project_upload_dir, exist_ok=True)

    ext = os.path.splitext(file.filename)[1]
    stored_name = f"{uuid.uuid4().hex}{ext}"
    stored_path = os.path.join(project_upload_dir, stored_name)

    with open(stored_path, "wb") as f:
        content = await file.read()
        f.write(content)

    file_size = len(content)

    # 解析文件
    parsed = parse_uploaded_file(stored_path, file.filename)
    parsed_json = json.dumps(parsed, ensure_ascii=False) if parsed else None

    # 記錄到資料庫
    doc_id = add_document(
        project_id=project_id,
        doc_type=doc_type,
        original_filename=file.filename,
        stored_filename=stored_name,
        file_size=file_size,
        mime_type=file.content_type,
        description=description,
        parsed_data=parsed_json
    )

    return {
        "success": True,
        "document_id": doc_id,
        "filename": file.filename,
        "file_size": file_size,
        "parsed_fields": parsed.get("parsed_fields", {}),
        "raw_text_preview": (parsed.get("raw_text", "")[:500] + "...") if parsed.get("raw_text", "") else "",
        "message": "文件上傳並解析完成"
    }


@app.post("/api/projects/{project_id}/parse-and-fill")
async def api_parse_and_fill(
    project_id: int,
    file: UploadFile = File(...)
):
    """上傳文件 → 解析 → 自動填入工程資料"""
    existing = get_project(project_id)
    if not existing:
        raise HTTPException(status_code=404, detail="工程不存在")

    # 儲存檔案
    ensure_dirs()
    project_upload_dir = os.path.join(UPLOAD_DIR, str(project_id))
    os.makedirs(project_upload_dir, exist_ok=True)

    ext = os.path.splitext(file.filename)[1]
    stored_name = f"{uuid.uuid4().hex}{ext}"
    stored_path = os.path.join(project_upload_dir, stored_name)

    with open(stored_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # 解析
    parsed = parse_uploaded_file(stored_path, file.filename)

    if parsed.get("error"):
        return {"success": False, "error": parsed["error"]}

    fields = parsed.get("parsed_fields", {})

    if fields:
        # 自動填入（只填空白欄位，不覆蓋已有資料）
        update_data = {}
        for key, value in fields.items():
            if key == 'term_definitions':
                if not existing.get('term_definitions'):
                    update_data['term_definitions'] = value
            elif not existing.get(key):
                update_data[key] = value

        if update_data:
            update_project(project_id, update_data)

    # 記錄文件
    add_document(
        project_id=project_id,
        doc_type="contract",
        original_filename=file.filename,
        stored_filename=stored_name,
        file_size=len(content),
        mime_type=file.content_type,
        parsed_data=json.dumps(parsed, ensure_ascii=False)
    )

    return {
        "success": True,
        "parsed_fields": fields,
        "filled_count": len([k for k in fields if k != 'term_definitions']),
        "message": f"已從文件解析出 {len(fields)} 個欄位並自動填入"
    }


# ===== API: 人員管理 =====

@app.post("/api/projects/{project_id}/personnel")
async def api_add_personnel(project_id: int, data: dict):
    """新增工程人員"""
    existing = get_project(project_id)
    if not existing:
        raise HTTPException(status_code=404, detail="工程不存在")

    pid = add_personnel(project_id, data)
    return {"success": True, "personnel_id": pid, "message": "人員新增成功"}


@app.delete("/api/projects/{project_id}/personnel/{personnel_id}")
async def api_delete_personnel(project_id: int, personnel_id: int):
    """刪除工程人員"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM project_personnel WHERE id = ? AND project_id = ?", (personnel_id, project_id))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    if not affected:
        raise HTTPException(status_code=404, detail="人員不存在")
    return {"success": True, "message": "人員已刪除"}


# ===== API: 名詞定義管理 =====

@app.post("/api/projects/{project_id}/terms")
async def api_add_term(project_id: int, data: dict):
    """新增名詞定義"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO term_definitions (project_id, term_number, term_name, term_definition) VALUES (?, ?, ?, ?)",
        (project_id, data.get('term_number'), data.get('term_name', ''), data.get('term_definition', ''))
    )
    term_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"success": True, "term_id": term_id, "message": "名詞定義新增成功"}


@app.put("/api/projects/{project_id}/terms/{term_id}")
async def api_update_term(project_id: int, term_id: int, data: dict):
    """更新名詞定義"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE term_definitions SET term_name = ?, term_definition = ?, updated_at = datetime('now', 'localtime') WHERE id = ? AND project_id = ?",
        (data.get('term_name', ''), data.get('term_definition', ''), term_id, project_id)
    )
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return {"success": affected > 0, "message": "名詞定義已更新" if affected else "未找到"}


@app.delete("/api/projects/{project_id}/terms/{term_id}")
async def api_delete_term(project_id: int, term_id: int):
    """刪除名詞定義"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM term_definitions WHERE id = ? AND project_id = ?", (term_id, project_id))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return {"success": affected > 0, "message": "名詞定義已刪除" if affected else "未找到"}


# ===== API: 自訂欄位 =====

@app.post("/api/projects/{project_id}/custom-fields")
async def api_add_custom_field(project_id: int, data: dict):
    """新增自訂欄位"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO custom_fields (project_id, field_name, field_value, field_order) VALUES (?, ?, ?, ?)",
        (project_id, data.get('field_name', ''), data.get('field_value', ''), data.get('field_order', 0))
    )
    field_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"success": True, "field_id": field_id, "message": "自訂欄位新增成功"}


# ===== API: 契約詳細表 =====

@app.post("/api/projects/{project_id}/contract/upload")
async def api_upload_contract_xls(
    project_id: int,
    file: UploadFile = File(...)
):
    """上傳契約詳細表 Excel (.xls/.xlsx) 並匯入"""
    existing = get_project(project_id)
    if not existing:
        raise HTTPException(status_code=404, detail="工程不存在")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ('.xls', '.xlsx'):
        raise HTTPException(status_code=400, detail="僅支援 .xls 或 .xlsx 格式")

    # 儲存檔案
    ensure_dirs()
    project_upload_dir = os.path.join(UPLOAD_DIR, str(project_id))
    os.makedirs(project_upload_dir, exist_ok=True)

    stored_name = f"contract_{uuid.uuid4().hex[:8]}{ext}"
    stored_path = os.path.join(project_upload_dir, stored_name)

    with open(stored_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # 解析契約詳細表
    result = parse_contract_xls(stored_path)

    if result.get("error"):
        return {"success": False, "error": result["error"]}

    items = result.get("items", [])
    if not items:
        return {"success": False, "error": "未解析到任何契約項目"}

    # 匯入資料庫
    count = import_contract_items(project_id, items)

    # 記錄文件
    add_document(
        project_id=project_id,
        doc_type="contract_detail",
        original_filename=file.filename,
        stored_filename=stored_name,
        file_size=len(content),
        mime_type=file.content_type
    )

    return {
        "success": True,
        "imported_count": count,
        "stats": result.get("stats", {}),
        "message": f"已匯入 {count} 筆契約項目"
    }


@app.get("/api/projects/{project_id}/contract/items")
async def api_get_contract_items(
    project_id: int,
    category: Optional[str] = None
):
    """取得契約詳細表項目"""
    items = get_contract_items(project_id, category)
    return {"success": True, "data": items, "count": len(items)}


@app.get("/api/projects/{project_id}/contract/summary")
async def api_get_contract_summary(project_id: int):
    """取得契約詳細表摘要"""
    summary = get_contract_summary(project_id)
    return {"success": True, "data": summary}


@app.put("/api/projects/{project_id}/contract/items/{item_id}")
async def api_update_contract_item(project_id: int, item_id: int, data: dict):
    """更新單一契約項目（數量、單價等）"""
    # 如果更新了數量或單價，自動重算複價
    if 'quantity' in data and 'unit_price' in data:
        try:
            data['total_price'] = float(data['quantity']) * float(data['unit_price'])
        except (ValueError, TypeError):
            pass
    elif 'quantity' in data or 'unit_price' in data:
        # 取得現有資料來計算
        items = get_contract_items(project_id)
        current = next((i for i in items if i['id'] == item_id), None)
        if current:
            q = float(data.get('quantity', current['quantity'] or 0))
            p = float(data.get('unit_price', current['unit_price'] or 0))
            data['total_price'] = q * p

    success = update_contract_item(item_id, data)
    return {"success": success, "message": "契約項目已更新" if success else "更新失敗"}


@app.post("/api/projects/{project_id}/contract/items")
async def api_add_contract_item(project_id: int, data: dict):
    """新增契約項目"""
    if not data.get('item_name'):
        raise HTTPException(status_code=400, detail="項目名稱為必填")

    # 自動計算複價
    if data.get('quantity') and data.get('unit_price'):
        try:
            data['total_price'] = float(data['quantity']) * float(data['unit_price'])
        except (ValueError, TypeError):
            pass

    item_id = add_contract_item(project_id, data)
    return {"success": True, "item_id": item_id, "message": "契約項目新增成功"}


@app.delete("/api/projects/{project_id}/contract/items/{item_id}")
async def api_delete_contract_item(project_id: int, item_id: int):
    """刪除契約項目"""
    success = delete_contract_item(item_id)
    return {"success": success, "message": "契約項目已刪除" if success else "刪除失敗"}


# ===== API: 施工日誌 =====

@app.get("/api/projects/{project_id}/logs")
async def api_list_logs(
    project_id: int,
    month: Optional[str] = None
):
    """列出施工日誌"""
    logs = list_daily_logs(project_id, month)
    return {"success": True, "data": logs, "count": len(logs)}


@app.get("/api/projects/{project_id}/logs/stats")
async def api_log_stats(project_id: int):
    """施工日誌統計"""
    stats = get_daily_log_stats(project_id)
    return {"success": True, "data": stats}


@app.get("/api/projects/{project_id}/logs/date/{log_date}")
async def api_get_log_by_date(project_id: int, log_date: str):
    """依日期取得施工日誌"""
    log = get_daily_log_by_date(project_id, log_date)
    if not log:
        return {"success": True, "data": None}
    return {"success": True, "data": log}


@app.get("/api/projects/{project_id}/logs/{log_id}")
async def api_get_log(project_id: int, log_id: int):
    """取得單筆施工日誌"""
    log = get_daily_log(log_id)
    if not log:
        raise HTTPException(status_code=404, detail="日誌不存在")
    return {"success": True, "data": log}


@app.post("/api/projects/{project_id}/logs")
async def api_create_log(project_id: int, data: dict):
    """建立施工日誌"""
    existing = get_project(project_id)
    if not existing:
        raise HTTPException(status_code=404, detail="工程不存在")

    if not data.get('log_date'):
        raise HTTPException(status_code=400, detail="日期為必填")

    # 檢查是否已存在
    existing_log = get_daily_log_by_date(project_id, data['log_date'])
    if existing_log:
        raise HTTPException(status_code=409, detail=f"該日期 ({data['log_date']}) 已有日誌記錄")

    try:
        log_id = create_daily_log(project_id, data)
        return {"success": True, "log_id": log_id, "message": "施工日誌建立成功"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/projects/{project_id}/logs/{log_id}")
async def api_update_log(project_id: int, log_id: int, data: dict):
    """更新施工日誌"""
    existing = get_daily_log(log_id)
    if not existing:
        raise HTTPException(status_code=404, detail="日誌不存在")

    success = update_daily_log(log_id, data)
    return {"success": success, "message": "施工日誌已更新"}


@app.delete("/api/projects/{project_id}/logs/{log_id}")
async def api_delete_log(project_id: int, log_id: int):
    """刪除施工日誌"""
    success = delete_daily_log(log_id)
    return {"success": success, "message": "施工日誌已刪除" if success else "刪除失敗"}


# ===== API: 參考法規 =====

@app.get("/api/regulations")
async def api_list_regulations(category: Optional[str] = None):
    """列出所有法規"""
    regs = list_regulations(category)
    return {"success": True, "data": regs, "count": len(regs)}


@app.get("/api/regulations/{reg_code}/articles")
async def api_get_regulation_articles(reg_code: str, keyword: Optional[str] = None):
    """取得法規條文"""
    articles = get_regulation_articles(reg_code, keyword)
    return {"success": True, "data": articles, "count": len(articles)}


@app.post("/api/regulations/import")
async def api_import_regulation(data: dict):
    """匯入法規條文"""
    if not data.get('reg_code') or not data.get('reg_name') or not data.get('articles'):
        raise HTTPException(status_code=400, detail="缺少必要欄位: reg_code, reg_name, articles")

    count = import_regulations(
        data['reg_code'], data['reg_name'], data['articles'],
        data.get('source_file', ''), data.get('effective_date', '')
    )
    return {"success": True, "imported_count": count, "message": f"已匯入 {count} 條條文"}


# ===== API: 自主檢查表 =====

@app.get("/api/projects/{project_id}/inspections")
async def api_list_inspections(project_id: int):
    """列出自主檢查表"""
    rows = list_inspection_checklists(project_id)
    return {"success": True, "data": rows, "count": len(rows)}


@app.post("/api/projects/{project_id}/inspections")
async def api_create_inspection(project_id: int, data: dict):
    """建立自主檢查表"""
    checklist_id = create_inspection_checklist(project_id, data)
    return {"success": True, "id": checklist_id, "message": "自主檢查表已建立"}


@app.get("/api/projects/{project_id}/inspections/{checklist_id}")
async def api_get_inspection(project_id: int, checklist_id: int):
    """取得自主檢查表詳細"""
    checklist = get_inspection_checklist(checklist_id)
    if not checklist:
        raise HTTPException(status_code=404, detail="檢查表不存在")
    return {"success": True, "data": checklist}


@app.put("/api/projects/{project_id}/inspections/{checklist_id}")
async def api_update_inspection(project_id: int, checklist_id: int, data: dict):
    """更新自主檢查表"""
    update_inspection_checklist(checklist_id, data)
    return {"success": True, "message": "自主檢查表已更新"}


@app.delete("/api/projects/{project_id}/inspections/{checklist_id}")
async def api_delete_inspection(project_id: int, checklist_id: int):
    """刪除自主檢查表"""
    delete_inspection_checklist(checklist_id)
    return {"success": True, "message": "已刪除"}


# ===== API: 拍照記錄表 =====

@app.get("/api/projects/{project_id}/photos")
async def api_list_photos(project_id: int):
    """列出拍照記錄表"""
    rows = list_photo_records(project_id)
    return {"success": True, "data": rows, "count": len(rows)}


@app.post("/api/projects/{project_id}/photos")
async def api_create_photo(project_id: int, data: dict):
    """建立拍照記錄表"""
    record_id = create_photo_record(project_id, data)
    return {"success": True, "id": record_id, "message": "拍照記錄表已建立"}


@app.get("/api/projects/{project_id}/photos/{record_id}")
async def api_get_photo(project_id: int, record_id: int):
    """取得拍照記錄表詳細"""
    record = get_photo_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="記錄不存在")
    return {"success": True, "data": record}


@app.put("/api/projects/{project_id}/photos/{record_id}")
async def api_update_photo(project_id: int, record_id: int, data: dict):
    """更新拍照記錄表"""
    update_photo_record(record_id, data)
    return {"success": True, "message": "拍照記錄表已更新"}


@app.delete("/api/projects/{project_id}/photos/{record_id}")
async def api_delete_photo(project_id: int, record_id: int):
    """刪除拍照記錄表"""
    delete_photo_record(record_id)
    return {"success": True, "message": "已刪除"}


# ===== API: 拍照上傳 =====

@app.post("/api/projects/{project_id}/photos/{record_id}/upload")
async def api_upload_photo(project_id: int, record_id: int, file: UploadFile = File(...)):
    """上傳照片"""
    photo_dir = os.path.join(UPLOAD_DIR, str(project_id), "photos")
    os.makedirs(photo_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    filepath = os.path.join(photo_dir, filename)
    with open(filepath, "wb") as f:
        content = await file.read()
        f.write(content)
    return {"success": True, "filename": filename, "path": f"/api/documents/{project_id}/photos/{filename}"}


@app.get("/api/documents/{project_id}/photos/{filename}")
async def api_get_photo_file(project_id: int, filename: str):
    """取得照片檔案"""
    filepath = os.path.join(UPLOAD_DIR, str(project_id), "photos", filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="照片不存在")
    return FileResponse(filepath)


# ===== API: 進度管理 =====

@app.get("/api/projects/{project_id}/schedule")
async def api_list_schedule(project_id: int):
    """列出施工網圖任務"""
    tasks = list_schedule_tasks(project_id)
    return {"success": True, "data": tasks, "count": len(tasks)}


@app.post("/api/projects/{project_id}/schedule/import")
async def api_import_schedule(project_id: int, data: dict):
    """匯入施工網圖任務"""
    tasks = data.get('tasks', [])
    if not tasks:
        raise HTTPException(status_code=400, detail="缺少 tasks 資料")
    count = import_schedule_tasks(project_id, tasks)
    return {"success": True, "imported": count, "message": f"已匯入 {count} 項任務"}


@app.get("/api/projects/{project_id}/scurve")
async def api_get_scurve(project_id: int):
    """取得 S-Curve 資料"""
    data = get_scurve_data(project_id)
    return {"success": True, "data": data}


@app.post("/api/projects/{project_id}/scurve/import")
async def api_import_scurve(project_id: int, data: dict):
    """匯入 S-Curve 資料"""
    items = data.get('items', [])
    monthly = data.get('monthly', [])
    result = import_scurve_data(project_id, items, monthly)
    return {"success": True, "imported": result, "message": f"已匯入 {result['items']} 項工作項目、{result['monthly']} 筆月進度"}


@app.put("/api/projects/{project_id}/scurve/{year_month}")
async def api_update_scurve_actual(project_id: int, year_month: str, data: dict):
    """更新 S-Curve 實際進度"""
    update_scurve_actual(project_id, year_month, data)
    return {"success": True, "message": f"{year_month} 實際進度已更新"}


# ===== API: 送審管制表 =====

@app.get("/api/projects/{project_id}/submittals")
async def api_list_submittals(project_id: int):
    return {"success": True, "data": list_submittal_control(project_id)}

@app.post("/api/projects/{project_id}/submittals")
async def api_create_submittal(project_id: int, data: dict):
    rid = create_submittal_control(project_id, data)
    return {"success": True, "id": rid, "message": "送審項目已新增"}

@app.put("/api/projects/{project_id}/submittals/{item_id}")
async def api_update_submittal(project_id: int, item_id: int, data: dict):
    update_submittal_control(item_id, data)
    return {"success": True, "message": "送審項目已更新"}

@app.delete("/api/projects/{project_id}/submittals/{item_id}")
async def api_delete_submittal(project_id: int, item_id: int):
    delete_submittal_control(item_id)
    return {"success": True, "message": "送審項目已刪除"}

@app.post("/api/projects/{project_id}/submittals/import")
async def api_import_submittals(project_id: int, data: dict):
    count = import_submittal_control(project_id, data.get('items', []))
    return {"success": True, "imported": count, "message": f"已匯入 {count} 項送審管制"}


# ===== API: 檢試驗管制 =====

@app.get("/api/projects/{project_id}/tests")
async def api_list_tests(project_id: int):
    return {"success": True, "data": list_test_control(project_id)}

@app.post("/api/projects/{project_id}/tests")
async def api_create_test(project_id: int, data: dict):
    rid = create_test_control(project_id, data)
    return {"success": True, "id": rid, "message": "檢試驗項目已新增"}

@app.put("/api/projects/{project_id}/tests/{item_id}")
async def api_update_test(project_id: int, item_id: int, data: dict):
    update_test_control(item_id, data)
    return {"success": True, "message": "檢試驗項目已更新"}

@app.delete("/api/projects/{project_id}/tests/{item_id}")
async def api_delete_test(project_id: int, item_id: int):
    delete_test_control(item_id)
    return {"success": True, "message": "檢試驗項目已刪除"}

@app.post("/api/projects/{project_id}/tests/import")
async def api_import_tests(project_id: int, data: dict):
    count = import_test_control(project_id, data.get('items', []))
    return {"success": True, "imported": count, "message": f"已匯入 {count} 項檢試驗管制"}


# ===== API: 零用金 =====

@app.get("/api/projects/{project_id}/petty-cash")
async def api_list_petty_cash(project_id: int):
    items = list_petty_cash(project_id)
    summary = get_petty_cash_summary(project_id)
    return {"success": True, "data": items, "summary": summary}

@app.post("/api/projects/{project_id}/petty-cash")
async def api_create_petty_cash(project_id: int, data: dict):
    rid = create_petty_cash(project_id, data)
    return {"success": True, "id": rid, "message": "零用金項目已新增"}

@app.put("/api/projects/{project_id}/petty-cash/{item_id}")
async def api_update_petty_cash(project_id: int, item_id: int, data: dict):
    update_petty_cash(item_id, data)
    return {"success": True, "message": "零用金項目已更新"}

@app.delete("/api/projects/{project_id}/petty-cash/{item_id}")
async def api_delete_petty_cash(project_id: int, item_id: int):
    delete_petty_cash(item_id)
    return {"success": True, "message": "零用金項目已刪除"}


# ===== API: 工程估驗 =====

@app.get("/api/projects/{project_id}/estimates")
async def api_list_estimates(project_id: int):
    return {"success": True, "data": list_payment_estimates(project_id)}

@app.post("/api/projects/{project_id}/estimates")
async def api_create_estimate(project_id: int, data: dict):
    eid = create_payment_estimate(project_id, data)
    return {"success": True, "id": eid, "message": "估驗期別已新增"}

@app.get("/api/projects/{project_id}/estimates/{estimate_id}")
async def api_get_estimate(project_id: int, estimate_id: int):
    est = get_payment_estimate(estimate_id)
    if not est:
        raise HTTPException(status_code=404, detail="估驗資料不存在")
    return {"success": True, "data": est}

@app.delete("/api/projects/{project_id}/estimates/{estimate_id}")
async def api_delete_estimate(project_id: int, estimate_id: int):
    delete_payment_estimate(estimate_id)
    return {"success": True, "message": "估驗期別已刪除"}

@app.post("/api/projects/{project_id}/estimates/import")
async def api_import_estimates(project_id: int, data: dict):
    count = import_payment_estimates(project_id, data.get('estimates', []))
    return {"success": True, "imported": count, "message": f"已匯入 {count} 期估驗資料"}


# ===== API: 特訂條款 =====

@app.get("/api/projects/{project_id}/special-terms")
async def api_list_special_terms(project_id: int):
    return {"success": True, "data": list_special_terms(project_id)}

@app.get("/api/projects/{project_id}/special-terms/search")
async def api_search_special_terms(project_id: int, q: str = ""):
    if not q or len(q) < 1:
        return {"success": True, "data": []}
    results = search_special_terms(project_id, q)
    return {"success": True, "data": results, "keyword": q, "count": len(results)}

@app.get("/api/projects/{project_id}/special-terms/{term_id}")
async def api_get_special_term(project_id: int, term_id: int):
    term = get_special_term(term_id)
    if not term:
        raise HTTPException(status_code=404, detail="條款不存在")
    return {"success": True, "data": term}

@app.post("/api/projects/{project_id}/special-terms/import")
async def api_import_special_terms(project_id: int, data: dict):
    count = import_special_terms(project_id, data.get('articles', []))
    return {"success": True, "imported": count, "message": f"已匯入 {count} 段特訂條款"}


# ===== API: 施工技術規範 =====

@app.get("/api/projects/{project_id}/tech-specs")
async def api_list_tech_specs(project_id: int):
    return {"success": True, "data": list_tech_specs(project_id)}

@app.get("/api/projects/{project_id}/tech-specs/search")
async def api_search_tech_specs(project_id: int, q: str = ""):
    if not q or len(q) < 1:
        return {"success": True, "data": []}
    results = search_tech_specs(project_id, q)
    return {"success": True, "data": results, "keyword": q, "count": len(results)}

@app.get("/api/projects/{project_id}/tech-specs/{spec_id}")
async def api_get_tech_spec(project_id: int, spec_id: int):
    spec = get_tech_spec(spec_id)
    if not spec:
        raise HTTPException(status_code=404, detail="規範不存在")
    return {"success": True, "data": spec}

@app.post("/api/projects/{project_id}/tech-specs/import")
async def api_import_tech_specs(project_id: int, data: dict):
    count = import_tech_specs(project_id, data.get('articles', []))
    return {"success": True, "imported": count, "message": f"已匯入 {count} 段施工技術規範"}


# ===== API: 交通工程手冊 =====

@app.get("/api/projects/{project_id}/traffic-manual")
async def api_list_traffic_manual(project_id: int):
    return {"success": True, "data": list_traffic_manual(project_id)}

@app.get("/api/projects/{project_id}/traffic-manual/search")
async def api_search_traffic_manual(project_id: int, q: str = ""):
    if not q or len(q) < 1:
        return {"success": True, "data": []}
    results = search_traffic_manual(project_id, q)
    return {"success": True, "data": results, "keyword": q, "count": len(results)}

@app.get("/api/projects/{project_id}/traffic-manual/{item_id}")
async def api_get_traffic_manual(project_id: int, item_id: int):
    item = get_traffic_manual_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="手冊內容不存在")
    return {"success": True, "data": item}

@app.post("/api/projects/{project_id}/traffic-manual/import")
async def api_import_traffic_manual(project_id: int, data: dict):
    count = import_traffic_manual(project_id, data.get('articles', []))
    return {"success": True, "imported": count, "message": f"已匯入 {count} 段交通工程手冊"}


# ===== API: 工程計畫 =====

@app.get("/api/projects/{project_id}/project-plans")
async def api_list_project_plans(project_id: int):
    return {"success": True, "data": list_project_plans(project_id)}

@app.get("/api/projects/{project_id}/project-plans/search")
async def api_search_project_plans(project_id: int, q: str = ""):
    if not q or len(q) < 1:
        return {"success": True, "data": []}
    results = search_project_plans(project_id, q)
    return {"success": True, "data": results, "keyword": q, "count": len(results)}

@app.get("/api/projects/{project_id}/project-plans/{item_id}")
async def api_get_project_plan(project_id: int, item_id: int):
    item = get_project_plan_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="計畫內容不存在")
    return {"success": True, "data": item}

@app.post("/api/projects/{project_id}/project-plans/import")
async def api_import_project_plans(project_id: int, data: dict):
    count = import_project_plans(project_id, data.get('articles', []))
    return {"success": True, "imported": count, "message": f"已匯入 {count} 段工程計畫"}


# ===== API: 語音自動化 =====

@app.post("/api/projects/{project_id}/voice/transcribe")
async def api_voice_transcribe(project_id: int, audio: UploadFile = File(...), mode: str = Form("daily_log"), language: str = Form("auto")):
    """上傳音檔 → Whisper 辨識 → AI 結構化 → 存為草稿"""
    from voice_service import (transcribe_audio, structure_daily_log, structure_inspection,
                               structure_photo_record, structure_material_entry,
                               save_voice_draft, VOICE_UPLOAD_DIR)
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="工程不存在")

    # 儲存音檔
    ext = os.path.splitext(audio.filename)[1] or ".wav"
    fname = f"voice_{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
    fpath = VOICE_UPLOAD_DIR / fname
    with open(fpath, "wb") as f:
        content = await audio.read()
        f.write(content)

    # Whisper 辨識
    result = transcribe_audio(str(fpath), language)
    if not result.get("text"):
        return {"success": False, "message": "語音辨識失敗", "error": result.get("error", "無法辨識")}

    transcript = result["text"]
    project_name = project.get("project_name", "")

    # AI 結構化
    structurers = {
        "daily_log": structure_daily_log,
        "inspection": structure_inspection,
        "photo": structure_photo_record,
        "material": structure_material_entry,
    }
    structurer = structurers.get(mode, structure_daily_log)
    structured = structurer(transcript, project_name)

    # 存為草稿
    draft_id = save_voice_draft(project_id, mode, transcript, structured, fname)

    return {
        "success": True,
        "draft_id": draft_id,
        "transcript": transcript,
        "language": result.get("language", "zh"),
        "duration": result.get("duration", 0),
        "structured_data": structured,
        "mode": mode,
        "message": "語音辨識完成，已建立草稿待檢核"
    }


@app.post("/api/projects/{project_id}/voice/transcribe-text")
async def api_voice_transcribe_text(project_id: int, data: dict):
    """直接輸入文字 → AI 結構化 → 存為草稿（測試用 / 文字輸入模式）"""
    from voice_service import (structure_daily_log, structure_inspection,
                               structure_photo_record, structure_material_entry,
                               save_voice_draft)
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="工程不存在")

    transcript = data.get("text", "").strip()
    mode = data.get("mode", "daily_log")
    if not transcript:
        raise HTTPException(status_code=400, detail="文字內容為空")

    project_name = project.get("project_name", "")
    structurers = {
        "daily_log": structure_daily_log,
        "inspection": structure_inspection,
        "photo": structure_photo_record,
        "material": structure_material_entry,
    }
    structurer = structurers.get(mode, structure_daily_log)
    structured = structurer(transcript, project_name)
    draft_id = save_voice_draft(project_id, mode, transcript, structured, "")

    return {
        "success": True,
        "draft_id": draft_id,
        "transcript": transcript,
        "structured_data": structured,
        "mode": mode,
        "message": "AI 結構化完成，已建立草稿待檢核"
    }


@app.get("/api/projects/{project_id}/voice/drafts")
async def api_list_voice_drafts(project_id: int, status: Optional[str] = None):
    """列出語音草稿"""
    from voice_service import list_voice_drafts
    drafts = list_voice_drafts(project_id, status)
    return {"success": True, "data": drafts, "count": len(drafts)}


@app.get("/api/projects/{project_id}/voice/drafts/{draft_id}")
async def api_get_voice_draft(project_id: int, draft_id: int):
    """取得單筆語音草稿"""
    from voice_service import get_voice_draft
    draft = get_voice_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="草稿不存在")
    return {"success": True, "data": draft}


@app.put("/api/projects/{project_id}/voice/drafts/{draft_id}")
async def api_update_voice_draft(project_id: int, draft_id: int, data: dict):
    """更新語音草稿（檢核修改結構化資料）"""
    from voice_service import update_voice_draft
    structured = data.get("structured_data")
    status = data.get("status")
    success = update_voice_draft(draft_id, structured, status)
    return {"success": success, "message": "草稿已更新" if success else "更新失敗"}


@app.post("/api/projects/{project_id}/voice/drafts/{draft_id}/confirm")
async def api_confirm_voice_draft(project_id: int, draft_id: int):
    """確認語音草稿 → 寫入正式資料表"""
    from voice_service import confirm_voice_draft
    result = confirm_voice_draft(draft_id)
    return result


@app.get("/voice")
async def voice_page():
    """語音錄入 PWA 頁面"""
    voice_html = os.path.join(os.path.dirname(__file__), "templates", "voice.html")
    if os.path.exists(voice_html):
        return HTMLResponse(open(voice_html, encoding="utf-8").read())
    raise HTTPException(status_code=404, detail="語音頁面不存在")


# ===== API: 文件掃描辨識歸檔 =====

@app.post("/api/projects/{project_id}/scanner/scan")
async def api_scan_document(project_id: int, image: UploadFile = File(...)):
    """上傳圖片 → OCR 辨識 → AI 分類 → 自動歸檔"""
    from doc_scanner import ocr_from_image, classify_document, save_scanned_document
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="工程不存在")

    image_data = await image.read()
    if not image_data:
        raise HTTPException(status_code=400, detail="圖片為空")

    # OCR 辨識
    ocr_result = ocr_from_image(image_data)
    if not ocr_result.get("text"):
        return {"success": False, "message": "OCR 無法辨識文字", "ocr": ocr_result}

    # AI 分類
    project_name = project.get("project_name", "")
    classification = classify_document(ocr_result["text"], project_name)

    # 儲存歸檔
    saved = save_scanned_document(project_id, image_data, ocr_result, classification, image.filename)

    return {
        "success": True,
        "message": f"文件已辨識歸檔：[{saved['category_name']}] {saved['title']}",
        "scan_id": saved["scan_id"],
        "doc_id": saved["doc_id"],
        "ocr": {
            "text": ocr_result["text"],
            "line_count": ocr_result["line_count"],
            "avg_confidence": ocr_result["avg_confidence"],
            "duration": ocr_result["duration"]
        },
        "classification": classification
    }


@app.post("/api/projects/{project_id}/scanner/scan-base64")
async def api_scan_document_base64(project_id: int, data: dict):
    """Base64 圖片 → OCR → 分類 → 歸檔（webcam 拍照用）"""
    from doc_scanner import ocr_from_base64, ocr_from_image, classify_document, save_scanned_document
    import base64
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="工程不存在")

    base64_str = data.get("image", "")
    if not base64_str:
        raise HTTPException(status_code=400, detail="圖片資料為空")

    # 解碼圖片
    if ',' in base64_str:
        raw = base64_str.split(',', 1)[1]
    else:
        raw = base64_str
    image_data = base64.b64decode(raw)

    # OCR 辨識
    ocr_result = ocr_from_image(image_data)
    if not ocr_result.get("text"):
        return {"success": False, "message": "OCR 無法辨識文字", "ocr": ocr_result}

    # AI 分類
    project_name = project.get("project_name", "")
    classification = classify_document(ocr_result["text"], project_name)

    # 儲存歸檔
    saved = save_scanned_document(project_id, image_data, ocr_result, classification, "webcam_capture.jpg")

    return {
        "success": True,
        "message": f"文件已辨識歸檔：[{saved['category_name']}] {saved['title']}",
        "scan_id": saved["scan_id"],
        "doc_id": saved["doc_id"],
        "ocr": {
            "text": ocr_result["text"],
            "line_count": ocr_result["line_count"],
            "avg_confidence": ocr_result["avg_confidence"],
            "duration": ocr_result["duration"]
        },
        "classification": classification
    }


@app.post("/api/projects/{project_id}/scanner/ocr-only")
async def api_ocr_only(project_id: int, data: dict):
    """僅 OCR 辨識（不歸檔），用於預覽"""
    from doc_scanner import ocr_from_image
    import base64
    base64_str = data.get("image", "")
    if not base64_str:
        raise HTTPException(status_code=400, detail="圖片資料為空")
    if ',' in base64_str:
        raw = base64_str.split(',', 1)[1]
    else:
        raw = base64_str
    image_data = base64.b64decode(raw)
    ocr_result = ocr_from_image(image_data)
    return {"success": True, "ocr": ocr_result}


@app.get("/api/projects/{project_id}/scanner/list")
async def api_list_scanned(project_id: int, category: Optional[str] = None):
    """列出掃描文件"""
    from doc_scanner import list_scanned_documents
    docs = list_scanned_documents(project_id, category)
    return {"success": True, "data": docs, "count": len(docs)}


@app.get("/api/projects/{project_id}/scanner/{scan_id}")
async def api_get_scanned(project_id: int, scan_id: int):
    """取得單筆掃描文件"""
    from doc_scanner import get_scanned_document
    doc = get_scanned_document(scan_id)
    if not doc:
        raise HTTPException(status_code=404, detail="掃描記錄不存在")
    return {"success": True, "data": doc}


@app.get("/api/projects/{project_id}/scanner/search")
async def api_search_scanned(project_id: int, q: str = ""):
    """搜尋掃描文件（全文搜尋 OCR 文字）"""
    from doc_scanner import search_scanned_documents
    if not q:
        raise HTTPException(status_code=400, detail="搜尋關鍵字為空")
    docs = search_scanned_documents(project_id, q)
    return {"success": True, "data": docs, "count": len(docs)}


@app.get("/api/scanner/categories")
async def api_scanner_categories():
    """取得文件分類列表"""
    from doc_scanner import DOC_CATEGORIES
    return {"success": True, "data": DOC_CATEGORIES}


@app.get("/scanner")
async def scanner_page():
    """文件掃描頁面"""
    scanner_html = os.path.join(os.path.dirname(__file__), "templates", "scanner.html")
    if os.path.exists(scanner_html):
        return HTMLResponse(open(scanner_html, encoding="utf-8").read())
    raise HTTPException(status_code=404, detail="掃描頁面不存在")


@app.get("/api/scanned-image/{filename}")
async def api_scanned_image(filename: str):
    """取得掃描圖片"""
    from doc_scanner import SCAN_UPLOAD_DIR
    filepath = SCAN_UPLOAD_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="圖片不存在")
    return FileResponse(str(filepath))


# ===== API: 文件下載 =====

@app.get("/api/documents/{project_id}/{filename}")
async def api_download_document(project_id: int, filename: str):
    """下載文件"""
    filepath = os.path.join(UPLOAD_DIR, str(project_id), filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="檔案不存在")
    return FileResponse(filepath)


# ===== API: 系統統計 =====

@app.get("/api/stats")
async def api_stats():
    """系統統計"""
    stats = get_stats()
    return {"success": True, "data": stats}


# ===== API: 匯出工程資料（JSON） =====

@app.get("/api/projects/{project_id}/export")
async def api_export_project(project_id: int):
    """匯出工程完整資料為 JSON"""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="工程不存在")

    return JSONResponse(
        content=project,
        headers={
            "Content-Disposition": f'attachment; filename="project_{project_id}.json"'
        }
    )


# ===== 結構計算模擬器 =====

@app.get("/structural-sim", response_class=HTMLResponse)
async def structural_sim():
    """結構計算模擬器 — 擋土牆/梁/基礎 即時互動計算"""
    html_path = os.path.join(os.path.dirname(__file__), "templates", "structural_sim.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


# ===== 健康檢查 =====

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": "營建自動化管理系統",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


# ===== 啟動 =====

if __name__ == "__main__":
    init_db()
    print("=" * 60)
    print("  營建自動化管理系統 v1.0.0")
    print("  http://localhost:8020")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8020)
