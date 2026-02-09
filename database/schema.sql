-- 築未科技動態表單系統 — Supabase/PostgreSQL

-- 1. 模板定義表
CREATE TABLE templates (
    template_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    schema_json JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. 表單提交數據表
CREATE TABLE form_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id TEXT REFERENCES templates(template_id),
    submission_data JSONB NOT NULL,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. GIN 索引（大數據量時優化 JSONB 搜尋）
CREATE INDEX idx_form_data ON form_submissions USING GIN (submission_data);
CREATE INDEX idx_template_schema ON templates USING GIN (schema_json);

-- 4. 預存拍照表模板
INSERT INTO templates (template_id, title, schema_json) VALUES (
    'const_photo_record_001',
    '工程拍照記錄表',
    '{"template_id":"const_photo_record_001","title":"工程拍照記錄表","columns":[{"id":"item","label":"工程項目","type":"text"},{"id":"location","label":"拍攝位置","type":"text"},{"id":"photo","label":"照片 (URL)","type":"image"},{"id":"note","label":"說明","type":"textarea"}],"default_rows":[{"item":"範例項目","location":"一樓大廳","photo":"https://via.placeholder.com/150","note":"初步勘查記錄"}]}'
);
