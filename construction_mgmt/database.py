"""
營建自動化管理系統 — 資料庫模型
SQLite 本地優先儲存
"""
import sqlite3
import os
import json
from datetime import datetime

DB_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DB_DIR, "projects.db")
UPLOAD_DIR = os.path.join(DB_DIR, "uploads")


def ensure_dirs():
    """確保資料目錄存在"""
    os.makedirs(DB_DIR, exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_db():
    """取得資料庫連線"""
    ensure_dirs()
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """初始化資料庫表格"""
    conn = get_db()
    cursor = conn.cursor()

    # ===== 工程基本資料主表 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        
        -- (一) 工程名稱
        project_name TEXT NOT NULL,
        
        -- (二) 主辦單位
        owner_agency TEXT,
        
        -- (三) 執行工程處
        execution_office TEXT,
        
        -- (四) 督導工務所
        supervision_office TEXT,
        
        -- (五) 設計單位
        design_unit TEXT,
        
        -- (六) 監造單位
        supervision_unit TEXT,
        
        -- (七) 承攬廠商
        contractor TEXT,
        
        -- (八) 工程地點
        project_location TEXT,
        
        -- (九) 契約金額
        contract_amount TEXT,
        contract_amount_numeric REAL,
        
        -- (十) 工程期限
        construction_period TEXT,
        construction_period_days INTEGER,
        
        -- (十一) 工程範圍
        project_scope TEXT,
        
        -- (十二) 保固期限
        warranty_terms TEXT,
        
        -- 額外管理欄位
        start_date TEXT,
        expected_end_date TEXT,
        actual_end_date TEXT,
        status TEXT DEFAULT 'active',
        notes TEXT,
        
        -- 時間戳記
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        updated_at TEXT DEFAULT (datetime('now', 'localtime'))
    )
    """)

    # ===== 名詞定義表 (十三) =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS term_definitions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        term_number INTEGER,
        term_name TEXT NOT NULL,
        term_definition TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        updated_at TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
    )
    """)

    # ===== 工程人員表 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS project_personnel (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        name TEXT NOT NULL,
        company TEXT,
        license_no TEXT,
        phone TEXT,
        email TEXT,
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
    )
    """)

    # ===== 上傳文件表 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS project_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        doc_type TEXT NOT NULL,
        original_filename TEXT NOT NULL,
        stored_filename TEXT NOT NULL,
        file_size INTEGER,
        mime_type TEXT,
        description TEXT,
        parsed_data TEXT,
        uploaded_at TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
    )
    """)

    # ===== 自訂欄位表（可擴充） =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS custom_fields (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        field_name TEXT NOT NULL,
        field_value TEXT,
        field_order INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
    )
    """)

    # ===== 契約詳細表（契約書工項明細） =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contract_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        row_order INTEGER NOT NULL,
        
        -- 階層結構
        level INTEGER DEFAULT 0,
        parent_code TEXT,
        item_code TEXT,
        
        -- 7 欄位對應 Excel
        item_number TEXT,
        item_name TEXT NOT NULL,
        unit TEXT,
        quantity REAL,
        unit_price REAL,
        total_price REAL,
        remark_code TEXT,
        
        -- 分類標記
        is_category INTEGER DEFAULT 0,
        is_subtotal INTEGER DEFAULT 0,
        
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        updated_at TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
    )
    """)

    # ===== 施工日誌主表 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS construction_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        log_date TEXT NOT NULL,
        
        -- 天氣
        weather_am TEXT,
        weather_pm TEXT,
        temperature_high REAL,
        temperature_low REAL,
        
        -- 施工概況
        work_description TEXT,
        
        -- 安全記錄
        safety_notes TEXT,
        
        -- 品質記錄
        quality_notes TEXT,
        
        -- 備註
        notes TEXT,
        
        -- 施工狀態: working(施工), rain_stop(雨停), holiday(休假), other
        day_status TEXT DEFAULT 'working',
        
        -- 累計工期
        calendar_days INTEGER,
        work_days INTEGER,
        
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        updated_at TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
        UNIQUE(project_id, log_date)
    )
    """)

    # ===== 日誌—人力記錄 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS log_workers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        log_id INTEGER NOT NULL,
        trade TEXT NOT NULL,
        count INTEGER DEFAULT 0,
        company TEXT,
        notes TEXT,
        FOREIGN KEY (log_id) REFERENCES construction_logs(id) ON DELETE CASCADE
    )
    """)

    # ===== 日誌—機具記錄 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS log_equipment (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        log_id INTEGER NOT NULL,
        equipment_name TEXT NOT NULL,
        spec TEXT,
        count INTEGER DEFAULT 1,
        hours REAL,
        notes TEXT,
        FOREIGN KEY (log_id) REFERENCES construction_logs(id) ON DELETE CASCADE
    )
    """)

    # ===== 日誌—材料記錄 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS log_materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        log_id INTEGER NOT NULL,
        material_name TEXT NOT NULL,
        spec TEXT,
        unit TEXT,
        quantity REAL,
        supplier TEXT,
        notes TEXT,
        FOREIGN KEY (log_id) REFERENCES construction_logs(id) ON DELETE CASCADE
    )
    """)

    # ===== 日誌—施工項目記錄 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS log_work_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        log_id INTEGER NOT NULL,
        contract_item_id INTEGER,
        item_name TEXT NOT NULL,
        location TEXT,
        quantity REAL,
        unit TEXT,
        progress_pct REAL,
        notes TEXT,
        FOREIGN KEY (log_id) REFERENCES construction_logs(id) ON DELETE CASCADE,
        FOREIGN KEY (contract_item_id) REFERENCES contract_items(id) ON DELETE SET NULL
    )
    """)

    # ===== 參考法規表 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS regulations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reg_code TEXT NOT NULL,
        reg_name TEXT NOT NULL,
        article_number INTEGER,
        article_title TEXT,
        article_content TEXT NOT NULL,
        source_file TEXT,
        effective_date TEXT,
        category TEXT DEFAULT 'quality',
        created_at TEXT DEFAULT (datetime('now', 'localtime'))
    )
    """)

    # ===== 自主檢查表 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inspection_checklists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        checklist_name TEXT NOT NULL,
        sub_project TEXT,
        inspection_date TEXT,
        contractor TEXT,
        inspection_location TEXT,
        status TEXT DEFAULT 'draft',
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        updated_at TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inspection_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        checklist_id INTEGER NOT NULL,
        sort_order INTEGER DEFAULT 0,
        phase TEXT DEFAULT 'during',
        item_name TEXT NOT NULL,
        check_standard TEXT,
        actual_result TEXT,
        check_result TEXT DEFAULT '',
        FOREIGN KEY (checklist_id) REFERENCES inspection_checklists(id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inspection_safety (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        checklist_id INTEGER NOT NULL,
        phase TEXT DEFAULT 'during',
        description TEXT,
        check_result TEXT DEFAULT '',
        FOREIGN KEY (checklist_id) REFERENCES inspection_checklists(id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inspection_deficiency (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        checklist_id INTEGER NOT NULL,
        phase TEXT DEFAULT 'during',
        is_resolved INTEGER DEFAULT 0,
        tracking_number TEXT,
        notes TEXT,
        FOREIGN KEY (checklist_id) REFERENCES inspection_checklists(id) ON DELETE CASCADE
    )
    """)

    # ===== 拍照記錄表 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS photo_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        record_date TEXT,
        record_title TEXT,
        status TEXT DEFAULT 'draft',
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        updated_at TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS photo_record_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        record_id INTEGER NOT NULL,
        sort_order INTEGER DEFAULT 0,
        photo_date TEXT,
        location TEXT,
        item_name TEXT,
        design_value TEXT,
        measured_value TEXT,
        photo_path TEXT,
        notes TEXT,
        FOREIGN KEY (record_id) REFERENCES photo_records(id) ON DELETE CASCADE
    )
    """)

    # ===== 進度管理：施工網圖任務 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS schedule_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        task_id INTEGER,
        wbs TEXT,
        task_name TEXT NOT NULL,
        duration_days INTEGER,
        early_start TEXT,
        late_start TEXT,
        early_finish TEXT,
        late_finish TEXT,
        predecessors TEXT,
        successors TEXT,
        progress_pct REAL DEFAULT 0,
        is_critical INTEGER DEFAULT 0,
        sort_order INTEGER DEFAULT 0,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """)

    # ===== 進度管理：S-Curve 資料 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scurve_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        item_code TEXT,
        item_name TEXT NOT NULL,
        amount REAL DEFAULT 0,
        weight_pct REAL DEFAULT 0,
        sort_order INTEGER DEFAULT 0,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scurve_monthly (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        year_month TEXT NOT NULL,
        work_days INTEGER DEFAULT 0,
        cumulative_days INTEGER DEFAULT 0,
        cumulative_days_pct REAL DEFAULT 0,
        planned_progress REAL DEFAULT 0,
        planned_cumulative REAL DEFAULT 0,
        actual_progress REAL DEFAULT 0,
        actual_cumulative REAL DEFAULT 0,
        planned_amount REAL DEFAULT 0,
        planned_cumulative_amount REAL DEFAULT 0,
        actual_amount REAL DEFAULT 0,
        actual_cumulative_amount REAL DEFAULT 0,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """)

    # ===== 送審管制表 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS submittal_control (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        seq INTEGER,
        plan_name TEXT NOT NULL,
        submit_date TEXT,
        review_date TEXT,
        approval_date TEXT,
        status TEXT DEFAULT 'pending',
        reviewer TEXT,
        notes TEXT,
        sort_order INTEGER DEFAULT 0,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """)

    # ===== 檢試驗管制總表 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS test_control (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        seq INTEGER,
        material_name TEXT NOT NULL,
        spec_item TEXT,
        planned_date TEXT,
        actual_date TEXT,
        quantity TEXT,
        sample_date TEXT,
        sample_qty TEXT,
        sample_freq TEXT,
        cumulative_qty TEXT,
        cumulative_sample TEXT,
        test_result TEXT,
        inspector TEXT,
        file_ref TEXT,
        notes TEXT,
        sort_order INTEGER DEFAULT 0,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """)

    # ===== 三大管制表（材料送審 + 檢驗 + 三個月滾動） =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS three_control_material (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        seq INTEGER,
        material_name TEXT NOT NULL,
        spec TEXT,
        supplier TEXT,
        submit_date TEXT,
        approval_date TEXT,
        status TEXT DEFAULT 'pending',
        notes TEXT,
        sort_order INTEGER DEFAULT 0,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS three_control_inspection (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        seq INTEGER,
        item_name TEXT NOT NULL,
        inspection_type TEXT,
        planned_date TEXT,
        actual_date TEXT,
        result TEXT,
        inspector TEXT,
        notes TEXT,
        sort_order INTEGER DEFAULT 0,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS three_control_schedule (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        seq INTEGER,
        work_item TEXT NOT NULL,
        month1_plan REAL DEFAULT 0,
        month1_actual REAL DEFAULT 0,
        month2_plan REAL DEFAULT 0,
        month2_actual REAL DEFAULT 0,
        month3_plan REAL DEFAULT 0,
        month3_actual REAL DEFAULT 0,
        notes TEXT,
        sort_order INTEGER DEFAULT 0,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """)

    # ===== 零用金 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS petty_cash (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        expense_date TEXT,
        description TEXT NOT NULL,
        category TEXT,
        amount REAL DEFAULT 0,
        vendor TEXT,
        receipt_no TEXT,
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """)

    # ===== 工程估驗 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payment_estimates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        period_no INTEGER,
        period_start TEXT,
        period_end TEXT,
        contract_amount REAL DEFAULT 0,
        changed_amount REAL DEFAULT 0,
        current_estimate REAL DEFAULT 0,
        cumulative_estimate REAL DEFAULT 0,
        prev_cumulative REAL DEFAULT 0,
        this_period REAL DEFAULT 0,
        retention REAL DEFAULT 0,
        price_adjustment REAL DEFAULT 0,
        deduction REAL DEFAULT 0,
        prepayment_deduct REAL DEFAULT 0,
        payable REAL DEFAULT 0,
        completion_pct REAL DEFAULT 0,
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS estimate_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        estimate_id INTEGER NOT NULL,
        item_code TEXT,
        item_name TEXT NOT NULL,
        contract_amount REAL DEFAULT 0,
        changed_amount REAL DEFAULT 0,
        cumulative_amount REAL DEFAULT 0,
        prev_cumulative REAL DEFAULT 0,
        this_period REAL DEFAULT 0,
        sort_order INTEGER DEFAULT 0,
        FOREIGN KEY (estimate_id) REFERENCES payment_estimates(id) ON DELETE CASCADE
    )
    """)

    # ===== 特訂條款 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS special_terms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        seq INTEGER,
        title TEXT,
        content TEXT NOT NULL,
        page_start INTEGER,
        page_end INTEGER,
        sort_order INTEGER DEFAULT 0,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """)

    # ===== 施工技術規範 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tech_specs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        seq INTEGER,
        title TEXT,
        content TEXT NOT NULL,
        page_start INTEGER,
        page_end INTEGER,
        sort_order INTEGER DEFAULT 0,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """)

    # ===== 交通工程手冊 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS traffic_manual (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        seq INTEGER,
        title TEXT,
        content TEXT NOT NULL,
        page_start INTEGER,
        page_end INTEGER,
        sort_order INTEGER DEFAULT 0,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """)

    # ===== 工程計畫 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS project_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        seq INTEGER,
        title TEXT,
        content TEXT NOT NULL,
        page_start INTEGER,
        page_end INTEGER,
        sort_order INTEGER DEFAULT 0,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """)

    # ===== 語音草稿表 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS voice_drafts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        mode TEXT NOT NULL,
        transcript TEXT,
        structured_data TEXT,
        audio_filename TEXT,
        status TEXT DEFAULT 'pending',
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        updated_at TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """)

    # ===== 掃描文件記錄表 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scanned_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        doc_id INTEGER,
        stored_filename TEXT,
        ocr_text TEXT,
        category TEXT,
        category_name TEXT,
        title TEXT,
        doc_number TEXT,
        doc_date TEXT,
        sender TEXT,
        summary TEXT,
        confidence REAL DEFAULT 0,
        status TEXT DEFAULT 'pending',
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (project_id) REFERENCES projects(id),
        FOREIGN KEY (doc_id) REFERENCES project_documents(id)
    )
    """)

    # ===== 雲端同步記錄表 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sync_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        sync_type TEXT,
        sync_status TEXT,
        sync_detail TEXT,
        synced_at TEXT DEFAULT (datetime('now', 'localtime'))
    )
    """)

    # ===== 施工日誌附表四擴充欄位（ALTER TABLE 安全新增） =====
    alter_cols = [
        ("construction_logs", "scheduled_progress", "REAL"),
        ("construction_logs", "actual_progress", "REAL"),
        ("construction_logs", "sampling_test_notes", "TEXT"),
        ("construction_logs", "subcontractor_notices", "TEXT"),
        ("construction_logs", "important_records", "TEXT"),
        ("construction_logs", "safety_pretask_education", "INTEGER DEFAULT 0"),
        ("construction_logs", "safety_insurance_check", "INTEGER DEFAULT 0"),
        ("construction_logs", "safety_ppe_check", "INTEGER DEFAULT 0"),
        ("construction_logs", "has_technician_required", "INTEGER DEFAULT 0"),
        ("log_workers", "cumulative_count", "INTEGER DEFAULT 0"),
        ("log_materials", "contract_quantity", "REAL"),
        ("log_materials", "cumulative_quantity", "REAL"),
    ]
    for table, col, col_type in alter_cols:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
        except Exception:
            pass  # 欄位已存在

    conn.commit()
    conn.close()
    print(f"[CMS] 資料庫初始化完成: {DB_PATH}")


# ===== CRUD 操作 =====

def create_project(data: dict) -> int:
    """建立新工程"""
    conn = get_db()
    cursor = conn.cursor()

    fields = [
        'project_name', 'owner_agency', 'execution_office', 'supervision_office',
        'design_unit', 'supervision_unit', 'contractor', 'project_location',
        'contract_amount', 'contract_amount_numeric', 'construction_period',
        'construction_period_days', 'project_scope', 'warranty_terms',
        'start_date', 'expected_end_date', 'status', 'notes'
    ]

    insert_fields = []
    values = []
    for f in fields:
        if f in data and data[f] is not None:
            insert_fields.append(f)
            values.append(data[f])

    placeholders = ', '.join(['?'] * len(values))
    field_names = ', '.join(insert_fields)

    cursor.execute(
        f"INSERT INTO projects ({field_names}) VALUES ({placeholders})",
        values
    )
    project_id = cursor.lastrowid

    # 插入名詞定義
    if 'term_definitions' in data and data['term_definitions']:
        for term in data['term_definitions']:
            cursor.execute(
                "INSERT INTO term_definitions (project_id, term_number, term_name, term_definition) VALUES (?, ?, ?, ?)",
                (project_id, term.get('term_number'), term.get('term_name', ''), term.get('term_definition', ''))
            )

    # 插入自訂欄位
    if 'custom_fields' in data and data['custom_fields']:
        for i, cf in enumerate(data['custom_fields']):
            cursor.execute(
                "INSERT INTO custom_fields (project_id, field_name, field_value, field_order) VALUES (?, ?, ?, ?)",
                (project_id, cf.get('field_name', ''), cf.get('field_value', ''), i)
            )

    conn.commit()
    conn.close()
    return project_id


def get_project(project_id: int) -> dict:
    """取得單一工程完整資料"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    project = dict(row)

    # 名詞定義
    cursor.execute(
        "SELECT * FROM term_definitions WHERE project_id = ? ORDER BY term_number",
        (project_id,)
    )
    project['term_definitions'] = [dict(r) for r in cursor.fetchall()]

    # 人員
    cursor.execute(
        "SELECT * FROM project_personnel WHERE project_id = ? ORDER BY role",
        (project_id,)
    )
    project['personnel'] = [dict(r) for r in cursor.fetchall()]

    # 文件
    cursor.execute(
        "SELECT * FROM project_documents WHERE project_id = ? ORDER BY uploaded_at DESC",
        (project_id,)
    )
    project['documents'] = [dict(r) for r in cursor.fetchall()]

    # 自訂欄位
    cursor.execute(
        "SELECT * FROM custom_fields WHERE project_id = ? ORDER BY field_order",
        (project_id,)
    )
    project['custom_fields'] = [dict(r) for r in cursor.fetchall()]

    # 契約詳細表項目數
    cursor.execute(
        "SELECT COUNT(*) FROM contract_items WHERE project_id = ?",
        (project_id,)
    )
    project['contract_items_count'] = cursor.fetchone()[0]

    conn.close()
    return project


def list_projects(status: str = None) -> list:
    """列出所有工程"""
    conn = get_db()
    cursor = conn.cursor()

    if status:
        cursor.execute(
            "SELECT id, project_name, owner_agency, contractor, contract_amount, construction_period, project_location, status, created_at, updated_at FROM projects WHERE status = ? ORDER BY created_at DESC",
            (status,)
        )
    else:
        cursor.execute(
            "SELECT id, project_name, owner_agency, contractor, contract_amount, construction_period, project_location, status, created_at, updated_at FROM projects ORDER BY created_at DESC"
        )

    projects = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return projects


def update_project(project_id: int, data: dict) -> bool:
    """更新工程資料"""
    conn = get_db()
    cursor = conn.cursor()

    fields = [
        'project_name', 'owner_agency', 'execution_office', 'supervision_office',
        'design_unit', 'supervision_unit', 'contractor', 'project_location',
        'contract_amount', 'contract_amount_numeric', 'construction_period',
        'construction_period_days', 'project_scope', 'warranty_terms',
        'start_date', 'expected_end_date', 'actual_end_date', 'status', 'notes'
    ]

    update_parts = []
    values = []
    for f in fields:
        if f in data:
            update_parts.append(f"{f} = ?")
            values.append(data[f])

    if not update_parts:
        conn.close()
        return False

    update_parts.append("updated_at = datetime('now', 'localtime')")
    values.append(project_id)

    cursor.execute(
        f"UPDATE projects SET {', '.join(update_parts)} WHERE id = ?",
        values
    )

    # 更新名詞定義（全部替換）
    if 'term_definitions' in data:
        cursor.execute("DELETE FROM term_definitions WHERE project_id = ?", (project_id,))
        for term in data['term_definitions']:
            cursor.execute(
                "INSERT INTO term_definitions (project_id, term_number, term_name, term_definition) VALUES (?, ?, ?, ?)",
                (project_id, term.get('term_number'), term.get('term_name', ''), term.get('term_definition', ''))
            )

    # 更新自訂欄位（全部替換）
    if 'custom_fields' in data:
        cursor.execute("DELETE FROM custom_fields WHERE project_id = ?", (project_id,))
        for i, cf in enumerate(data['custom_fields']):
            cursor.execute(
                "INSERT INTO custom_fields (project_id, field_name, field_value, field_order) VALUES (?, ?, ?, ?)",
                (project_id, cf.get('field_name', ''), cf.get('field_value', ''), i)
            )

    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def delete_project(project_id: int) -> bool:
    """刪除工程（CASCADE 會自動刪除關聯資料）"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def add_document(project_id: int, doc_type: str, original_filename: str,
                 stored_filename: str, file_size: int, mime_type: str,
                 description: str = None, parsed_data: str = None) -> int:
    """新增文件記錄"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO project_documents 
           (project_id, doc_type, original_filename, stored_filename, file_size, mime_type, description, parsed_data)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (project_id, doc_type, original_filename, stored_filename, file_size, mime_type, description, parsed_data)
    )
    doc_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return doc_id


def add_personnel(project_id: int, data: dict) -> int:
    """新增工程人員"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO project_personnel 
           (project_id, role, name, company, license_no, phone, email, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (project_id, data.get('role', ''), data.get('name', ''),
         data.get('company', ''), data.get('license_no', ''),
         data.get('phone', ''), data.get('email', ''), data.get('notes', ''))
    )
    pid = cursor.lastrowid
    conn.commit()
    conn.close()
    return pid


# ===== 契約詳細表 CRUD =====

def import_contract_items(project_id: int, items: list) -> int:
    """匯入契約詳細表項目（全部替換）"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM contract_items WHERE project_id = ?", (project_id,))

    count = 0
    for item in items:
        cursor.execute(
            """INSERT INTO contract_items 
               (project_id, row_order, level, parent_code, item_code,
                item_number, item_name, unit, quantity, unit_price, total_price,
                remark_code, is_category, is_subtotal)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (project_id, item.get('row_order', count),
             item.get('level', 0), item.get('parent_code', ''),
             item.get('item_code', ''), item.get('item_number', ''),
             item.get('item_name', ''), item.get('unit', ''),
             item.get('quantity'), item.get('unit_price'),
             item.get('total_price'), item.get('remark_code', ''),
             item.get('is_category', 0), item.get('is_subtotal', 0))
        )
        count += 1

    conn.commit()
    conn.close()
    return count


def get_contract_items(project_id: int, category: str = None) -> list:
    """取得契約詳細表項目"""
    conn = get_db()
    cursor = conn.cursor()

    if category:
        cursor.execute(
            "SELECT * FROM contract_items WHERE project_id = ? AND parent_code = ? ORDER BY row_order",
            (project_id, category)
        )
    else:
        cursor.execute(
            "SELECT * FROM contract_items WHERE project_id = ? ORDER BY row_order",
            (project_id,)
        )

    items = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return items


def update_contract_item(item_id: int, data: dict) -> bool:
    """更新單一契約項目"""
    conn = get_db()
    cursor = conn.cursor()

    updatable = ['item_number', 'item_name', 'unit', 'quantity', 'unit_price',
                 'total_price', 'remark_code', 'is_category', 'is_subtotal']
    parts = []
    values = []
    for f in updatable:
        if f in data:
            parts.append(f"{f} = ?")
            values.append(data[f])

    if not parts:
        conn.close()
        return False

    parts.append("updated_at = datetime('now', 'localtime')")
    values.append(item_id)

    cursor.execute(f"UPDATE contract_items SET {', '.join(parts)} WHERE id = ?", values)
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def add_contract_item(project_id: int, data: dict) -> int:
    """新增單一契約項目"""
    conn = get_db()
    cursor = conn.cursor()

    # 取得最大 row_order
    cursor.execute("SELECT MAX(row_order) FROM contract_items WHERE project_id = ?", (project_id,))
    max_order = cursor.fetchone()[0] or 0

    cursor.execute(
        """INSERT INTO contract_items 
           (project_id, row_order, level, parent_code, item_code,
            item_number, item_name, unit, quantity, unit_price, total_price,
            remark_code, is_category, is_subtotal)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (project_id, max_order + 1,
         data.get('level', 0), data.get('parent_code', ''),
         data.get('item_code', ''), data.get('item_number', ''),
         data.get('item_name', ''), data.get('unit', ''),
         data.get('quantity'), data.get('unit_price'),
         data.get('total_price'), data.get('remark_code', ''),
         data.get('is_category', 0), data.get('is_subtotal', 0))
    )
    item_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return item_id


def delete_contract_item(item_id: int) -> bool:
    """刪除單一契約項目"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM contract_items WHERE id = ?", (item_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def get_contract_summary(project_id: int) -> dict:
    """取得契約詳細表摘要統計"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM contract_items WHERE project_id = ?", (project_id,))
    total = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM contract_items WHERE project_id = ? AND is_category = 1",
        (project_id,)
    )
    categories = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM contract_items WHERE project_id = ? AND is_category = 0 AND is_subtotal = 0 AND unit != ''",
        (project_id,)
    )
    work_items = cursor.fetchone()[0]

    # 各大類小計
    cursor.execute(
        "SELECT item_name, total_price FROM contract_items WHERE project_id = ? AND is_subtotal = 1 ORDER BY row_order",
        (project_id,)
    )
    subtotals = [{'name': r[0], 'amount': r[1]} for r in cursor.fetchall()]

    # 總價
    cursor.execute(
        "SELECT total_price FROM contract_items WHERE project_id = ? AND item_name LIKE '%總價%' ORDER BY row_order DESC LIMIT 1",
        (project_id,)
    )
    row = cursor.fetchone()
    grand_total = row[0] if row else None

    conn.close()
    return {
        'total_rows': total,
        'categories': categories,
        'work_items': work_items,
        'subtotals': subtotals,
        'grand_total': grand_total
    }


# ===== 施工日誌 CRUD =====

def create_daily_log(project_id: int, data: dict) -> int:
    """建立施工日誌"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """INSERT INTO construction_logs
           (project_id, log_date, weather_am, weather_pm,
            temperature_high, temperature_low, work_description,
            safety_notes, quality_notes, notes, day_status,
            calendar_days, work_days,
            scheduled_progress, actual_progress,
            sampling_test_notes, subcontractor_notices, important_records,
            safety_pretask_education, safety_insurance_check, safety_ppe_check,
            has_technician_required)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (project_id, data.get('log_date'),
         data.get('weather_am', ''), data.get('weather_pm', ''),
         data.get('temperature_high'), data.get('temperature_low'),
         data.get('work_description', ''),
         data.get('safety_notes', ''), data.get('quality_notes', ''),
         data.get('notes', ''), data.get('day_status', 'working'),
         data.get('calendar_days'), data.get('work_days'),
         data.get('scheduled_progress'), data.get('actual_progress'),
         data.get('sampling_test_notes', ''), data.get('subcontractor_notices', ''),
         data.get('important_records', ''),
         data.get('safety_pretask_education', 0), data.get('safety_insurance_check', 0),
         data.get('safety_ppe_check', 0), data.get('has_technician_required', 0))
    )
    log_id = cursor.lastrowid

    # 插入人力
    for w in data.get('workers', []):
        cursor.execute(
            "INSERT INTO log_workers (log_id, trade, count, cumulative_count, company, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (log_id, w.get('trade', ''), w.get('count', 0), w.get('cumulative_count', 0), w.get('company', ''), w.get('notes', ''))
        )

    # 插入機具
    for eq in data.get('equipment', []):
        cursor.execute(
            "INSERT INTO log_equipment (log_id, equipment_name, spec, count, hours, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (log_id, eq.get('equipment_name', ''), eq.get('spec', ''),
             eq.get('count', 1), eq.get('hours'), eq.get('notes', ''))
        )

    # 插入材料
    for m in data.get('materials', []):
        cursor.execute(
            "INSERT INTO log_materials (log_id, material_name, spec, unit, quantity, contract_quantity, cumulative_quantity, supplier, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (log_id, m.get('material_name', ''), m.get('spec', ''),
             m.get('unit', ''), m.get('quantity'), m.get('contract_quantity'),
             m.get('cumulative_quantity'), m.get('supplier', ''), m.get('notes', ''))
        )

    # 插入施工項目
    for wi in data.get('work_items', []):
        cursor.execute(
            "INSERT INTO log_work_items (log_id, contract_item_id, item_name, location, quantity, unit, progress_pct, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (log_id, wi.get('contract_item_id'), wi.get('item_name', ''),
             wi.get('location', ''), wi.get('quantity'), wi.get('unit', ''),
             wi.get('progress_pct'), wi.get('notes', ''))
        )

    conn.commit()
    conn.close()
    return log_id


def get_daily_log(log_id: int) -> dict:
    """取得單筆施工日誌完整資料"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM construction_logs WHERE id = ?", (log_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    log = dict(row)

    cursor.execute("SELECT * FROM log_workers WHERE log_id = ?", (log_id,))
    log['workers'] = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM log_equipment WHERE log_id = ?", (log_id,))
    log['equipment'] = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM log_materials WHERE log_id = ?", (log_id,))
    log['materials'] = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM log_work_items WHERE log_id = ?", (log_id,))
    log['work_items'] = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return log


def get_daily_log_by_date(project_id: int, log_date: str) -> dict:
    """依日期取得施工日誌"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM construction_logs WHERE project_id = ? AND log_date = ?",
        (project_id, log_date)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return get_daily_log(row[0])
    return None


def list_daily_logs(project_id: int, month: str = None) -> list:
    """列出施工日誌（可按月份篩選）"""
    conn = get_db()
    cursor = conn.cursor()

    if month:
        cursor.execute(
            """SELECT cl.*, 
                (SELECT COUNT(*) FROM log_workers WHERE log_id = cl.id) as worker_types,
                (SELECT SUM(count) FROM log_workers WHERE log_id = cl.id) as total_workers,
                (SELECT COUNT(*) FROM log_equipment WHERE log_id = cl.id) as equipment_count,
                (SELECT COUNT(*) FROM log_work_items WHERE log_id = cl.id) as work_item_count
               FROM construction_logs cl
               WHERE cl.project_id = ? AND cl.log_date LIKE ?
               ORDER BY cl.log_date DESC""",
            (project_id, f"{month}%")
        )
    else:
        cursor.execute(
            """SELECT cl.*,
                (SELECT COUNT(*) FROM log_workers WHERE log_id = cl.id) as worker_types,
                (SELECT SUM(count) FROM log_workers WHERE log_id = cl.id) as total_workers,
                (SELECT COUNT(*) FROM log_equipment WHERE log_id = cl.id) as equipment_count,
                (SELECT COUNT(*) FROM log_work_items WHERE log_id = cl.id) as work_item_count
               FROM construction_logs cl
               WHERE cl.project_id = ?
               ORDER BY cl.log_date DESC""",
            (project_id,)
        )

    logs = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return logs


def update_daily_log(log_id: int, data: dict) -> bool:
    """更新施工日誌"""
    conn = get_db()
    cursor = conn.cursor()

    updatable = ['log_date', 'weather_am', 'weather_pm', 'temperature_high',
                 'temperature_low', 'work_description', 'safety_notes',
                 'quality_notes', 'notes', 'day_status', 'calendar_days', 'work_days',
                 'scheduled_progress', 'actual_progress',
                 'sampling_test_notes', 'subcontractor_notices', 'important_records',
                 'safety_pretask_education', 'safety_insurance_check', 'safety_ppe_check',
                 'has_technician_required']
    parts = []
    values = []
    for f in updatable:
        if f in data:
            parts.append(f"{f} = ?")
            values.append(data[f])

    if parts:
        parts.append("updated_at = datetime('now', 'localtime')")
        values.append(log_id)
        cursor.execute(f"UPDATE construction_logs SET {', '.join(parts)} WHERE id = ?", values)

    # 更新人力（全部替換）
    if 'workers' in data:
        cursor.execute("DELETE FROM log_workers WHERE log_id = ?", (log_id,))
        for w in data['workers']:
            cursor.execute(
                "INSERT INTO log_workers (log_id, trade, count, cumulative_count, company, notes) VALUES (?, ?, ?, ?, ?, ?)",
                (log_id, w.get('trade', ''), w.get('count', 0), w.get('cumulative_count', 0), w.get('company', ''), w.get('notes', ''))
            )

    # 更新機具
    if 'equipment' in data:
        cursor.execute("DELETE FROM log_equipment WHERE log_id = ?", (log_id,))
        for eq in data['equipment']:
            cursor.execute(
                "INSERT INTO log_equipment (log_id, equipment_name, spec, count, hours, notes) VALUES (?, ?, ?, ?, ?, ?)",
                (log_id, eq.get('equipment_name', ''), eq.get('spec', ''),
                 eq.get('count', 1), eq.get('hours'), eq.get('notes', ''))
            )

    # 更新材料
    if 'materials' in data:
        cursor.execute("DELETE FROM log_materials WHERE log_id = ?", (log_id,))
        for m in data['materials']:
            cursor.execute(
                "INSERT INTO log_materials (log_id, material_name, spec, unit, quantity, contract_quantity, cumulative_quantity, supplier, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (log_id, m.get('material_name', ''), m.get('spec', ''),
                 m.get('unit', ''), m.get('quantity'), m.get('contract_quantity'),
                 m.get('cumulative_quantity'), m.get('supplier', ''), m.get('notes', ''))
            )

    # 更新施工項目
    if 'work_items' in data:
        cursor.execute("DELETE FROM log_work_items WHERE log_id = ?", (log_id,))
        for wi in data['work_items']:
            cursor.execute(
                "INSERT INTO log_work_items (log_id, contract_item_id, item_name, location, quantity, unit, progress_pct, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (log_id, wi.get('contract_item_id'), wi.get('item_name', ''),
                 wi.get('location', ''), wi.get('quantity'), wi.get('unit', ''),
                 wi.get('progress_pct'), wi.get('notes', ''))
            )

    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return True


def delete_daily_log(log_id: int) -> bool:
    """刪除施工日誌（CASCADE 自動刪除關聯資料）"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM construction_logs WHERE id = ?", (log_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def get_daily_log_stats(project_id: int) -> dict:
    """取得施工日誌統計"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM construction_logs WHERE project_id = ?", (project_id,))
    total = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM construction_logs WHERE project_id = ? AND day_status = 'working'",
        (project_id,)
    )
    working = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM construction_logs WHERE project_id = ? AND day_status = 'rain_stop'",
        (project_id,)
    )
    rain_stop = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM construction_logs WHERE project_id = ? AND day_status = 'holiday'",
        (project_id,)
    )
    holiday = cursor.fetchone()[0]

    cursor.execute(
        "SELECT MIN(log_date), MAX(log_date) FROM construction_logs WHERE project_id = ?",
        (project_id,)
    )
    row = cursor.fetchone()
    first_date = row[0] if row else None
    last_date = row[1] if row else None

    # 各月日誌數
    cursor.execute(
        """SELECT substr(log_date, 1, 7) as month, COUNT(*) as cnt
           FROM construction_logs WHERE project_id = ?
           GROUP BY month ORDER BY month""",
        (project_id,)
    )
    monthly = [{'month': r[0], 'count': r[1]} for r in cursor.fetchall()]

    # 有日誌的日期列表（用於日曆標記）
    cursor.execute(
        "SELECT log_date, day_status FROM construction_logs WHERE project_id = ? ORDER BY log_date",
        (project_id,)
    )
    dates = [{'date': r[0], 'status': r[1]} for r in cursor.fetchall()]

    conn.close()
    return {
        'total_logs': total,
        'working_days': working,
        'rain_stop_days': rain_stop,
        'holiday_days': holiday,
        'first_date': first_date,
        'last_date': last_date,
        'monthly': monthly,
        'dates': dates
    }


# ===== 參考法規 CRUD =====

def import_regulations(reg_code: str, reg_name: str, articles: list, source_file: str = '', effective_date: str = '') -> int:
    """匯入法規條文（全部替換同一 reg_code）"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM regulations WHERE reg_code = ?", (reg_code,))

    count = 0
    for art in articles:
        cursor.execute(
            """INSERT INTO regulations
               (reg_code, reg_name, article_number, article_title, article_content, source_file, effective_date, category)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (reg_code, reg_name, art.get('number'), art.get('title', ''),
             art.get('content', ''), source_file, effective_date, art.get('category', 'quality'))
        )
        count += 1

    conn.commit()
    conn.close()
    return count


def list_regulations(category: str = None) -> list:
    """列出法規（依類別篩選）"""
    conn = get_db()
    cursor = conn.cursor()
    if category:
        cursor.execute(
            "SELECT DISTINCT reg_code, reg_name, effective_date, category, COUNT(*) as article_count FROM regulations WHERE category = ? GROUP BY reg_code ORDER BY reg_code",
            (category,)
        )
    else:
        cursor.execute(
            "SELECT DISTINCT reg_code, reg_name, effective_date, category, COUNT(*) as article_count FROM regulations GROUP BY reg_code ORDER BY reg_code"
        )
    regs = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return regs


def get_regulation_articles(reg_code: str, keyword: str = None) -> list:
    """取得法規條文（可搜尋）"""
    conn = get_db()
    cursor = conn.cursor()
    if keyword:
        cursor.execute(
            "SELECT * FROM regulations WHERE reg_code = ? AND (article_content LIKE ? OR article_title LIKE ?) ORDER BY article_number",
            (reg_code, f'%{keyword}%', f'%{keyword}%')
        )
    else:
        cursor.execute(
            "SELECT * FROM regulations WHERE reg_code = ? ORDER BY article_number",
            (reg_code,)
        )
    articles = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return articles


# ===== 自主檢查表 CRUD =====

def create_inspection_checklist(project_id: int, data: dict) -> int:
    """建立自主檢查表"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO inspection_checklists
        (project_id, checklist_name, sub_project, inspection_date, contractor, inspection_location, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        project_id,
        data.get('checklist_name', ''),
        data.get('sub_project', ''),
        data.get('inspection_date', ''),
        data.get('contractor', ''),
        data.get('inspection_location', ''),
        data.get('status', 'draft'),
        data.get('notes', '')
    ))
    checklist_id = cursor.lastrowid

    # 檢查項目
    for i, item in enumerate(data.get('items', [])):
        cursor.execute("""
            INSERT INTO inspection_items (checklist_id, sort_order, phase, item_name, check_standard, actual_result, check_result)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (checklist_id, i, item.get('phase', 'during'), item.get('item_name', ''),
              item.get('check_standard', ''), item.get('actual_result', ''), item.get('check_result', '')))

    # 安全衛生查驗
    for s in data.get('safety_items', []):
        cursor.execute("""
            INSERT INTO inspection_safety (checklist_id, phase, description, check_result)
            VALUES (?, ?, ?, ?)
        """, (checklist_id, s.get('phase', 'during'), s.get('description', ''), s.get('check_result', '')))

    # 缺失複查
    for d_item in data.get('deficiencies', []):
        cursor.execute("""
            INSERT INTO inspection_deficiency (checklist_id, phase, is_resolved, tracking_number, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (checklist_id, d_item.get('phase', 'during'), 1 if d_item.get('is_resolved') else 0,
              d_item.get('tracking_number', ''), d_item.get('notes', '')))

    conn.commit()
    conn.close()
    return checklist_id


def list_inspection_checklists(project_id: int) -> list:
    """列出專案的自主檢查表"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ic.*, COUNT(ii.id) as item_count
        FROM inspection_checklists ic
        LEFT JOIN inspection_items ii ON ii.checklist_id = ic.id
        WHERE ic.project_id = ?
        GROUP BY ic.id
        ORDER BY ic.inspection_date DESC, ic.id DESC
    """, (project_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_inspection_checklist(checklist_id: int) -> dict:
    """取得自主檢查表詳細"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM inspection_checklists WHERE id = ?", (checklist_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    checklist = dict(row)

    cursor.execute("SELECT * FROM inspection_items WHERE checklist_id = ? ORDER BY sort_order", (checklist_id,))
    checklist['items'] = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM inspection_safety WHERE checklist_id = ?", (checklist_id,))
    checklist['safety_items'] = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM inspection_deficiency WHERE checklist_id = ?", (checklist_id,))
    checklist['deficiencies'] = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return checklist


def update_inspection_checklist(checklist_id: int, data: dict) -> bool:
    """更新自主檢查表"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE inspection_checklists SET
            checklist_name=?, sub_project=?, inspection_date=?, contractor=?,
            inspection_location=?, status=?, notes=?,
            updated_at=datetime('now','localtime')
        WHERE id=?
    """, (
        data.get('checklist_name', ''), data.get('sub_project', ''),
        data.get('inspection_date', ''), data.get('contractor', ''),
        data.get('inspection_location', ''), data.get('status', 'draft'),
        data.get('notes', ''), checklist_id
    ))

    # 重建子項目
    cursor.execute("DELETE FROM inspection_items WHERE checklist_id=?", (checklist_id,))
    for i, item in enumerate(data.get('items', [])):
        cursor.execute("""
            INSERT INTO inspection_items (checklist_id, sort_order, phase, item_name, check_standard, actual_result, check_result)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (checklist_id, i, item.get('phase', 'during'), item.get('item_name', ''),
              item.get('check_standard', ''), item.get('actual_result', ''), item.get('check_result', '')))

    cursor.execute("DELETE FROM inspection_safety WHERE checklist_id=?", (checklist_id,))
    for s in data.get('safety_items', []):
        cursor.execute("""
            INSERT INTO inspection_safety (checklist_id, phase, description, check_result)
            VALUES (?, ?, ?, ?)
        """, (checklist_id, s.get('phase', 'during'), s.get('description', ''), s.get('check_result', '')))

    cursor.execute("DELETE FROM inspection_deficiency WHERE checklist_id=?", (checklist_id,))
    for d_item in data.get('deficiencies', []):
        cursor.execute("""
            INSERT INTO inspection_deficiency (checklist_id, phase, is_resolved, tracking_number, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (checklist_id, d_item.get('phase', 'during'), 1 if d_item.get('is_resolved') else 0,
              d_item.get('tracking_number', ''), d_item.get('notes', '')))

    conn.commit()
    conn.close()
    return True


def delete_inspection_checklist(checklist_id: int) -> bool:
    """刪除自主檢查表"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM inspection_items WHERE checklist_id=?", (checklist_id,))
    cursor.execute("DELETE FROM inspection_safety WHERE checklist_id=?", (checklist_id,))
    cursor.execute("DELETE FROM inspection_deficiency WHERE checklist_id=?", (checklist_id,))
    cursor.execute("DELETE FROM inspection_checklists WHERE id=?", (checklist_id,))
    conn.commit()
    conn.close()
    return True


# ===== 拍照記錄表 CRUD =====

def create_photo_record(project_id: int, data: dict) -> int:
    """建立拍照記錄表"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO photo_records (project_id, record_date, record_title, status)
        VALUES (?, ?, ?, ?)
    """, (project_id, data.get('record_date', ''), data.get('record_title', ''), data.get('status', 'draft')))
    record_id = cursor.lastrowid

    for i, item in enumerate(data.get('items', [])):
        cursor.execute("""
            INSERT INTO photo_record_items (record_id, sort_order, photo_date, location, item_name, design_value, measured_value, photo_path, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (record_id, i, item.get('photo_date', ''), item.get('location', ''),
              item.get('item_name', ''), item.get('design_value', ''),
              item.get('measured_value', ''), item.get('photo_path', ''), item.get('notes', '')))

    conn.commit()
    conn.close()
    return record_id


def list_photo_records(project_id: int) -> list:
    """列出專案的拍照記錄表"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pr.*, COUNT(pri.id) as item_count
        FROM photo_records pr
        LEFT JOIN photo_record_items pri ON pri.record_id = pr.id
        WHERE pr.project_id = ?
        GROUP BY pr.id
        ORDER BY pr.record_date DESC, pr.id DESC
    """, (project_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_photo_record(record_id: int) -> dict:
    """取得拍照記錄表詳細"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM photo_records WHERE id = ?", (record_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    record = dict(row)
    cursor.execute("SELECT * FROM photo_record_items WHERE record_id = ? ORDER BY sort_order", (record_id,))
    record['items'] = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return record


def update_photo_record(record_id: int, data: dict) -> bool:
    """更新拍照記錄表"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE photo_records SET record_date=?, record_title=?, status=?,
            updated_at=datetime('now','localtime')
        WHERE id=?
    """, (data.get('record_date', ''), data.get('record_title', ''), data.get('status', 'draft'), record_id))

    cursor.execute("DELETE FROM photo_record_items WHERE record_id=?", (record_id,))
    for i, item in enumerate(data.get('items', [])):
        cursor.execute("""
            INSERT INTO photo_record_items (record_id, sort_order, photo_date, location, item_name, design_value, measured_value, photo_path, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (record_id, i, item.get('photo_date', ''), item.get('location', ''),
              item.get('item_name', ''), item.get('design_value', ''),
              item.get('measured_value', ''), item.get('photo_path', ''), item.get('notes', '')))

    conn.commit()
    conn.close()
    return True


def delete_photo_record(record_id: int) -> bool:
    """刪除拍照記錄表"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM photo_record_items WHERE record_id=?", (record_id,))
    cursor.execute("DELETE FROM photo_records WHERE id=?", (record_id,))
    conn.commit()
    conn.close()
    return True


# ===== 進度管理 CRUD =====

def import_schedule_tasks(project_id: int, tasks: list) -> int:
    """批次匯入施工網圖任務"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM schedule_tasks WHERE project_id=?", (project_id,))
    count = 0
    for i, t in enumerate(tasks):
        cursor.execute("""
            INSERT INTO schedule_tasks (project_id, task_id, wbs, task_name, duration_days,
                early_start, late_start, early_finish, late_finish, predecessors, successors, progress_pct, is_critical, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (project_id, t.get('task_id'), t.get('wbs', ''), t.get('task_name', ''),
              t.get('duration_days'), t.get('early_start', ''), t.get('late_start', ''),
              t.get('early_finish', ''), t.get('late_finish', ''),
              t.get('predecessors', ''), t.get('successors', ''),
              t.get('progress_pct', 0), 1 if t.get('is_critical') else 0, i))
        count += 1
    conn.commit()
    conn.close()
    return count


def list_schedule_tasks(project_id: int) -> list:
    """列出施工網圖任務"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM schedule_tasks WHERE project_id=? ORDER BY sort_order", (project_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def import_scurve_data(project_id: int, items: list, monthly: list) -> dict:
    """批次匯入 S-Curve 資料"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM scurve_items WHERE project_id=?", (project_id,))
    cursor.execute("DELETE FROM scurve_monthly WHERE project_id=?", (project_id,))

    item_count = 0
    for i, it in enumerate(items):
        cursor.execute("""
            INSERT INTO scurve_items (project_id, item_code, item_name, amount, weight_pct, sort_order)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (project_id, it.get('item_code', ''), it.get('item_name', ''),
              it.get('amount', 0), it.get('weight_pct', 0), i))
        item_count += 1

    month_count = 0
    for m in monthly:
        cursor.execute("""
            INSERT INTO scurve_monthly (project_id, year_month, work_days, cumulative_days, cumulative_days_pct,
                planned_progress, planned_cumulative, actual_progress, actual_cumulative,
                planned_amount, planned_cumulative_amount, actual_amount, actual_cumulative_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (project_id, m.get('year_month', ''), m.get('work_days', 0),
              m.get('cumulative_days', 0), m.get('cumulative_days_pct', 0),
              m.get('planned_progress', 0), m.get('planned_cumulative', 0),
              m.get('actual_progress', 0), m.get('actual_cumulative', 0),
              m.get('planned_amount', 0), m.get('planned_cumulative_amount', 0),
              m.get('actual_amount', 0), m.get('actual_cumulative_amount', 0)))
        month_count += 1

    conn.commit()
    conn.close()
    return {"items": item_count, "monthly": month_count}


def get_scurve_data(project_id: int) -> dict:
    """取得 S-Curve 資料"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM scurve_items WHERE project_id=? ORDER BY sort_order", (project_id,))
    items = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM scurve_monthly WHERE project_id=? ORDER BY year_month", (project_id,))
    monthly = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"items": items, "monthly": monthly}


def update_scurve_actual(project_id: int, year_month: str, data: dict) -> bool:
    """更新 S-Curve 實際進度"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE scurve_monthly SET actual_progress=?, actual_cumulative=?,
            actual_amount=?, actual_cumulative_amount=?
        WHERE project_id=? AND year_month=?
    """, (data.get('actual_progress', 0), data.get('actual_cumulative', 0),
          data.get('actual_amount', 0), data.get('actual_cumulative_amount', 0),
          project_id, year_month))
    conn.commit()
    conn.close()
    return True


# ===== 送審管制表 CRUD =====

def list_submittal_control(project_id: int) -> list:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM submittal_control WHERE project_id=? ORDER BY sort_order", (project_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def create_submittal_control(project_id: int, data: dict) -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""INSERT INTO submittal_control (project_id, seq, plan_name, submit_date, review_date, approval_date, status, reviewer, notes, sort_order)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (project_id, data.get('seq'), data.get('plan_name',''), data.get('submit_date',''),
         data.get('review_date',''), data.get('approval_date',''), data.get('status','pending'),
         data.get('reviewer',''), data.get('notes',''), data.get('sort_order',0)))
    rid = cursor.lastrowid
    conn.commit(); conn.close()
    return rid

def update_submittal_control(item_id: int, data: dict) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""UPDATE submittal_control SET seq=?, plan_name=?, submit_date=?, review_date=?, approval_date=?, status=?, reviewer=?, notes=? WHERE id=?""",
        (data.get('seq'), data.get('plan_name',''), data.get('submit_date',''),
         data.get('review_date',''), data.get('approval_date',''), data.get('status','pending'),
         data.get('reviewer',''), data.get('notes',''), item_id))
    conn.commit(); conn.close()
    return True

def delete_submittal_control(item_id: int) -> bool:
    conn = get_db()
    conn.execute("DELETE FROM submittal_control WHERE id=?", (item_id,))
    conn.commit(); conn.close()
    return True

def import_submittal_control(project_id: int, items: list) -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM submittal_control WHERE project_id=?", (project_id,))
    for i, d in enumerate(items):
        cursor.execute("""INSERT INTO submittal_control (project_id, seq, plan_name, submit_date, review_date, approval_date, status, reviewer, notes, sort_order)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (project_id, d.get('seq'), d.get('plan_name',''), d.get('submit_date',''),
             d.get('review_date',''), d.get('approval_date',''), d.get('status','pending'),
             d.get('reviewer',''), d.get('notes',''), i))
    conn.commit(); conn.close()
    return len(items)


# ===== 檢試驗管制 CRUD =====

def list_test_control(project_id: int) -> list:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM test_control WHERE project_id=? ORDER BY sort_order", (project_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def create_test_control(project_id: int, data: dict) -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""INSERT INTO test_control (project_id, seq, material_name, spec_item, planned_date, actual_date, quantity, sample_date, sample_qty, sample_freq, cumulative_qty, cumulative_sample, test_result, inspector, file_ref, notes, sort_order)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (project_id, data.get('seq'), data.get('material_name',''), data.get('spec_item',''),
         data.get('planned_date',''), data.get('actual_date',''), data.get('quantity',''),
         data.get('sample_date',''), data.get('sample_qty',''), data.get('sample_freq',''),
         data.get('cumulative_qty',''), data.get('cumulative_sample',''), data.get('test_result',''),
         data.get('inspector',''), data.get('file_ref',''), data.get('notes',''), data.get('sort_order',0)))
    rid = cursor.lastrowid
    conn.commit(); conn.close()
    return rid

def update_test_control(item_id: int, data: dict) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""UPDATE test_control SET seq=?, material_name=?, spec_item=?, planned_date=?, actual_date=?, quantity=?, sample_date=?, sample_qty=?, sample_freq=?, cumulative_qty=?, cumulative_sample=?, test_result=?, inspector=?, file_ref=?, notes=? WHERE id=?""",
        (data.get('seq'), data.get('material_name',''), data.get('spec_item',''),
         data.get('planned_date',''), data.get('actual_date',''), data.get('quantity',''),
         data.get('sample_date',''), data.get('sample_qty',''), data.get('sample_freq',''),
         data.get('cumulative_qty',''), data.get('cumulative_sample',''), data.get('test_result',''),
         data.get('inspector',''), data.get('file_ref',''), data.get('notes',''), item_id))
    conn.commit(); conn.close()
    return True

def delete_test_control(item_id: int) -> bool:
    conn = get_db()
    conn.execute("DELETE FROM test_control WHERE id=?", (item_id,))
    conn.commit(); conn.close()
    return True

def import_test_control(project_id: int, items: list) -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM test_control WHERE project_id=?", (project_id,))
    for i, d in enumerate(items):
        cursor.execute("""INSERT INTO test_control (project_id, seq, material_name, spec_item, planned_date, actual_date, quantity, sample_date, sample_qty, sample_freq, cumulative_qty, cumulative_sample, test_result, inspector, file_ref, notes, sort_order)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (project_id, d.get('seq'), d.get('material_name',''), d.get('spec_item',''),
             d.get('planned_date',''), d.get('actual_date',''), d.get('quantity',''),
             d.get('sample_date',''), d.get('sample_qty',''), d.get('sample_freq',''),
             d.get('cumulative_qty',''), d.get('cumulative_sample',''), d.get('test_result',''),
             d.get('inspector',''), d.get('file_ref',''), d.get('notes',''), i))
    conn.commit(); conn.close()
    return len(items)


# ===== 零用金 CRUD =====

def list_petty_cash(project_id: int) -> list:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM petty_cash WHERE project_id=? ORDER BY expense_date DESC, id DESC", (project_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def create_petty_cash(project_id: int, data: dict) -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""INSERT INTO petty_cash (project_id, expense_date, description, category, amount, vendor, receipt_no, notes)
        VALUES (?,?,?,?,?,?,?,?)""",
        (project_id, data.get('expense_date',''), data.get('description',''), data.get('category',''),
         data.get('amount',0), data.get('vendor',''), data.get('receipt_no',''), data.get('notes','')))
    rid = cursor.lastrowid
    conn.commit(); conn.close()
    return rid

def update_petty_cash(item_id: int, data: dict) -> bool:
    conn = get_db()
    conn.execute("""UPDATE petty_cash SET expense_date=?, description=?, category=?, amount=?, vendor=?, receipt_no=?, notes=? WHERE id=?""",
        (data.get('expense_date',''), data.get('description',''), data.get('category',''),
         data.get('amount',0), data.get('vendor',''), data.get('receipt_no',''), data.get('notes',''), item_id))
    conn.commit(); conn.close()
    return True

def delete_petty_cash(item_id: int) -> bool:
    conn = get_db()
    conn.execute("DELETE FROM petty_cash WHERE id=?", (item_id,))
    conn.commit(); conn.close()
    return True

def get_petty_cash_summary(project_id: int) -> dict:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt, COALESCE(SUM(amount),0) as total FROM petty_cash WHERE project_id=?", (project_id,))
    row = dict(cursor.fetchone())
    conn.close()
    return row


# ===== 工程估驗 CRUD =====

def list_payment_estimates(project_id: int) -> list:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM payment_estimates WHERE project_id=? ORDER BY period_no", (project_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def create_payment_estimate(project_id: int, data: dict) -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""INSERT INTO payment_estimates (project_id, period_no, period_start, period_end,
        contract_amount, changed_amount, current_estimate, cumulative_estimate, prev_cumulative,
        this_period, retention, price_adjustment, deduction, prepayment_deduct, payable, completion_pct, notes)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (project_id, data.get('period_no'), data.get('period_start',''), data.get('period_end',''),
         data.get('contract_amount',0), data.get('changed_amount',0), data.get('current_estimate',0),
         data.get('cumulative_estimate',0), data.get('prev_cumulative',0), data.get('this_period',0),
         data.get('retention',0), data.get('price_adjustment',0), data.get('deduction',0),
         data.get('prepayment_deduct',0), data.get('payable',0), data.get('completion_pct',0),
         data.get('notes','')))
    eid = cursor.lastrowid
    # Insert items
    for i, it in enumerate(data.get('items', [])):
        cursor.execute("""INSERT INTO estimate_items (estimate_id, item_code, item_name, contract_amount, changed_amount, cumulative_amount, prev_cumulative, this_period, sort_order)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (eid, it.get('item_code',''), it.get('item_name',''), it.get('contract_amount',0),
             it.get('changed_amount',0), it.get('cumulative_amount',0), it.get('prev_cumulative',0),
             it.get('this_period',0), i))
    conn.commit(); conn.close()
    return eid

def get_payment_estimate(estimate_id: int) -> dict:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM payment_estimates WHERE id=?", (estimate_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    est = dict(row)
    cursor.execute("SELECT * FROM estimate_items WHERE estimate_id=? ORDER BY sort_order", (estimate_id,))
    est['items'] = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return est

def delete_payment_estimate(estimate_id: int) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM estimate_items WHERE estimate_id=?", (estimate_id,))
    cursor.execute("DELETE FROM payment_estimates WHERE id=?", (estimate_id,))
    conn.commit(); conn.close()
    return True

def import_payment_estimates(project_id: int, estimates: list) -> int:
    conn = get_db()
    cursor = conn.cursor()
    # Delete existing items first
    cursor.execute("SELECT id FROM payment_estimates WHERE project_id=?", (project_id,))
    for row in cursor.fetchall():
        cursor.execute("DELETE FROM estimate_items WHERE estimate_id=?", (row[0],))
    cursor.execute("DELETE FROM payment_estimates WHERE project_id=?", (project_id,))
    count = 0
    for est in estimates:
        cursor.execute("""INSERT INTO payment_estimates (project_id, period_no, period_start, period_end,
            contract_amount, changed_amount, current_estimate, cumulative_estimate, prev_cumulative,
            this_period, retention, price_adjustment, deduction, prepayment_deduct, payable, completion_pct, notes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (project_id, est.get('period_no'), est.get('period_start',''), est.get('period_end',''),
             est.get('contract_amount',0), est.get('changed_amount',0), est.get('current_estimate',0),
             est.get('cumulative_estimate',0), est.get('prev_cumulative',0), est.get('this_period',0),
             est.get('retention',0), est.get('price_adjustment',0), est.get('deduction',0),
             est.get('prepayment_deduct',0), est.get('payable',0), est.get('completion_pct',0),
             est.get('notes','')))
        eid = cursor.lastrowid
        for i, it in enumerate(est.get('items', [])):
            cursor.execute("""INSERT INTO estimate_items (estimate_id, item_code, item_name, contract_amount, changed_amount, cumulative_amount, prev_cumulative, this_period, sort_order)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (eid, it.get('item_code',''), it.get('item_name',''), it.get('contract_amount',0),
                 it.get('changed_amount',0), it.get('cumulative_amount',0), it.get('prev_cumulative',0),
                 it.get('this_period',0), i))
        count += 1
    conn.commit(); conn.close()
    return count


# ===== 特訂條款 CRUD =====

def list_special_terms(project_id: int) -> list:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, seq, title, page_start, page_end, LENGTH(content) as content_len FROM special_terms WHERE project_id=? ORDER BY sort_order", (project_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_special_term(term_id: int) -> dict:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM special_terms WHERE id=?", (term_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def search_special_terms(project_id: int, keyword: str) -> list:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, seq, title, page_start, page_end, content FROM special_terms WHERE project_id=? AND content LIKE ? ORDER BY sort_order",
        (project_id, f'%{keyword}%'))
    results = []
    for r in cursor.fetchall():
        d = dict(r)
        # Extract snippet around keyword
        idx = d['content'].find(keyword)
        start = max(0, idx - 60)
        end = min(len(d['content']), idx + len(keyword) + 60)
        d['snippet'] = ('...' if start > 0 else '') + d['content'][start:end] + ('...' if end < len(d['content']) else '')
        del d['content']
        results.append(d)
    conn.close()
    return results

def import_special_terms(project_id: int, articles: list) -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM special_terms WHERE project_id=?", (project_id,))
    for i, a in enumerate(articles):
        cursor.execute("""INSERT INTO special_terms (project_id, seq, title, content, page_start, page_end, sort_order)
            VALUES (?,?,?,?,?,?,?)""",
            (project_id, a.get('seq', i+1), a.get('title',''), a.get('content',''),
             a.get('page_start'), a.get('page_end'), i))
    conn.commit(); conn.close()
    return len(articles)


# ===== 施工技術規範 CRUD =====

def list_tech_specs(project_id: int) -> list:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, seq, title, page_start, page_end, LENGTH(content) as content_len FROM tech_specs WHERE project_id=? ORDER BY sort_order", (project_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_tech_spec(spec_id: int) -> dict:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tech_specs WHERE id=?", (spec_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def search_tech_specs(project_id: int, keyword: str) -> list:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, seq, title, page_start, page_end, content FROM tech_specs WHERE project_id=? AND content LIKE ? ORDER BY sort_order",
        (project_id, f'%{keyword}%'))
    results = []
    for r in cursor.fetchall():
        d = dict(r)
        idx = d['content'].find(keyword)
        start = max(0, idx - 60)
        end = min(len(d['content']), idx + len(keyword) + 60)
        d['snippet'] = ('...' if start > 0 else '') + d['content'][start:end] + ('...' if end < len(d['content']) else '')
        del d['content']
        results.append(d)
    conn.close()
    return results

def import_tech_specs(project_id: int, articles: list) -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tech_specs WHERE project_id=?", (project_id,))
    for i, a in enumerate(articles):
        cursor.execute("""INSERT INTO tech_specs (project_id, seq, title, content, page_start, page_end, sort_order)
            VALUES (?,?,?,?,?,?,?)""",
            (project_id, a.get('seq', i+1), a.get('title',''), a.get('content',''),
             a.get('page_start'), a.get('page_end'), i))
    conn.commit(); conn.close()
    return len(articles)


# ===== 交通工程手冊 CRUD =====

def list_traffic_manual(project_id: int) -> list:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, seq, title, page_start, page_end, LENGTH(content) as content_len FROM traffic_manual WHERE project_id=? ORDER BY sort_order", (project_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_traffic_manual_item(item_id: int) -> dict:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM traffic_manual WHERE id=?", (item_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def search_traffic_manual(project_id: int, keyword: str) -> list:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, seq, title, page_start, page_end, content FROM traffic_manual WHERE project_id=? AND content LIKE ? ORDER BY sort_order",
        (project_id, f'%{keyword}%'))
    results = []
    for r in cursor.fetchall():
        d = dict(r)
        idx = d['content'].find(keyword)
        start = max(0, idx - 60)
        end = min(len(d['content']), idx + len(keyword) + 60)
        d['snippet'] = ('...' if start > 0 else '') + d['content'][start:end] + ('...' if end < len(d['content']) else '')
        del d['content']
        results.append(d)
    conn.close()
    return results

def import_traffic_manual(project_id: int, articles: list) -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM traffic_manual WHERE project_id=?", (project_id,))
    for i, a in enumerate(articles):
        cursor.execute("""INSERT INTO traffic_manual (project_id, seq, title, content, page_start, page_end, sort_order)
            VALUES (?,?,?,?,?,?,?)""",
            (project_id, a.get('seq', i+1), a.get('title',''), a.get('content',''),
             a.get('page_start'), a.get('page_end'), i))
    conn.commit(); conn.close()
    return len(articles)


# ===== 工程計畫 CRUD =====

def list_project_plans(project_id: int) -> list:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, seq, title, page_start, page_end, LENGTH(content) as content_len FROM project_plans WHERE project_id=? ORDER BY sort_order", (project_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_project_plan_item(item_id: int) -> dict:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM project_plans WHERE id=?", (item_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def search_project_plans(project_id: int, keyword: str) -> list:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, seq, title, page_start, page_end, content FROM project_plans WHERE project_id=? AND content LIKE ? ORDER BY sort_order",
        (project_id, f'%{keyword}%'))
    results = []
    for r in cursor.fetchall():
        d = dict(r)
        idx = d['content'].find(keyword)
        start = max(0, idx - 60)
        end = min(len(d['content']), idx + len(keyword) + 60)
        d['snippet'] = ('...' if start > 0 else '') + d['content'][start:end] + ('...' if end < len(d['content']) else '')
        del d['content']
        results.append(d)
    conn.close()
    return results

def import_project_plans(project_id: int, articles: list) -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM project_plans WHERE project_id=?", (project_id,))
    for i, a in enumerate(articles):
        cursor.execute("""INSERT INTO project_plans (project_id, seq, title, content, page_start, page_end, sort_order)
            VALUES (?,?,?,?,?,?,?)""",
            (project_id, a.get('seq', i+1), a.get('title',''), a.get('content',''),
             a.get('page_start'), a.get('page_end'), i))
    conn.commit(); conn.close()
    return len(articles)


def get_stats() -> dict:
    """取得系統統計"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM projects")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM projects WHERE status = 'active'")
    active = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM project_documents")
    docs = cursor.fetchone()[0]

    conn.close()
    return {
        "total_projects": total,
        "active_projects": active,
        "total_documents": docs
    }


# 初始化
if __name__ == "__main__":
    init_db()
    print("資料庫初始化完成")
