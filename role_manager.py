# -*- coding: utf-8 -*-
"""
築未科技 — 角色管理模組
─────────────────────────────
將大智庫依專業領域切分，每個角色擁有：
1. 專屬 ChromaDB Collection（角色知識庫）
2. 專屬系統提示詞（回答風格與專業視角）
3. 專屬學習關鍵字（自動分類入庫）
4. 可存取共用大智庫（jarvis_training）作為通識知識

角色列表：
  construction_engineer  — 營建工程師
  drafting_engineer      — 繪圖工程師
  project_manager        — 專案管理人
  accounting_admin       — 會計行政工程師
  civil_engineer         — 土木技師
  structural_engineer    — 結構技師
  enterprise_owner       — 企業老闆
  subcontractor_owner    — 分包商老闆
  small_contractor       — 小包商老闆
"""
import json
import os
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
ROLES_FILE = ROOT / "brain_workspace" / "auth" / "role_definitions.json"

# ═══════════════════════════════════════════
# 角色定義
# ═══════════════════════════════════════════

ROLES: dict[str, dict[str, Any]] = {
    "construction_engineer": {
        "name": "營建工程師",
        "icon": "🏗️",
        "collection": "jarvis_role_construction",
        "description": "負責工地現場施工管理、品質管控、進度追蹤、安全衛生",
        "system_prompt": (
            "你是資深營建工程師助理。回答時以工地現場實務為主，"
            "注重施工規範、品質查驗、安全管理、進度控制。"
            "引用法規時標明條號，建議需可直接在工地執行。"
        ),
        "keywords": [
            "施工", "混凝土", "鋼筋", "模板", "鷹架", "開挖", "回填",
            "品質", "查驗", "工地", "安全帽", "墜落", "工安", "職安",
            "進度", "趕工", "工班", "澆置", "養護", "試體", "強度",
        ],
        "categories": ["施工技術", "工安職安"],
    },
    "drafting_engineer": {
        "name": "繪圖工程師",
        "icon": "📐",
        "collection": "jarvis_role_drafting",
        "description": "負責設計圖面繪製、BIM 建模、圖面審查、設計變更",
        "system_prompt": (
            "你是專業繪圖工程師助理。回答時以設計圖面、BIM、CAD 為核心，"
            "注重圖面規範、尺寸標註、圖層管理、設計變更流程。"
            "提供的建議需符合 CNS 製圖標準。"
        ),
        "keywords": [
            "圖面", "設計", "BIM", "CAD", "Revit", "AutoCAD", "圖層",
            "標註", "尺寸", "剖面", "平面", "立面", "大樣", "配筋圖",
            "設計變更", "送審", "竣工圖", "IFC", "點雲",
        ],
        "categories": ["施工技術"],
    },
    "project_manager": {
        "name": "專案管理人",
        "icon": "📋",
        "collection": "jarvis_role_pm",
        "description": "負責專案整體規劃、進度管控、成本控制、風險管理、跨部門協調",
        "system_prompt": (
            "你是資深專案管理顧問。回答時以專案管理五大流程群組為框架，"
            "注重範疇、時程、成本、品質、風險管理。"
            "建議需包含可量化指標和具體行動方案。"
        ),
        "keywords": [
            "專案", "進度", "里程碑", "甘特圖", "WBS", "成本", "預算",
            "風險", "協調", "會議", "報告", "KPI", "管理", "規劃",
            "排程", "資源", "變更管理", "利害關係人",
        ],
        "categories": ["管理協調"],
    },
    "accounting_admin": {
        "name": "會計行政工程師",
        "icon": "💰",
        "collection": "jarvis_role_accounting",
        "description": "負責工程計價、估驗、請款、發票管理、行政庶務",
        "system_prompt": (
            "你是工程會計行政專家。回答時以計價、估驗、請款流程為核心，"
            "注重金額精確、法規依據、稅務處理、文件管理。"
            "建議需符合營造業會計實務。"
        ),
        "keywords": [
            "計價", "估驗", "請款", "發票", "稅", "保留款", "保固金",
            "物價指數", "物調", "預算", "決算", "結算", "會計",
            "行政", "文件", "歸檔", "合約金額",
        ],
        "categories": ["採購履約"],
    },
    "civil_engineer": {
        "name": "土木技師",
        "icon": "🔧",
        "collection": "jarvis_role_civil",
        "description": "負責土木工程設計、地質調查、基礎工程、道路橋梁",
        "system_prompt": (
            "你是執業土木技師助理。回答時以土木工程專業為核心，"
            "注重結構安全、地質條件、設計規範、簽證責任。"
            "引用規範需標明版本與條文。"
        ),
        "keywords": [
            "土木", "基礎", "地質", "鑽探", "地下水", "擋土", "邊坡",
            "道路", "橋梁", "隧道", "排水", "管線", "測量", "水準",
            "技師簽證", "設計規範",
        ],
        "categories": ["施工技術"],
    },
    "structural_engineer": {
        "name": "結構技師",
        "icon": "🏛️",
        "collection": "jarvis_role_structural",
        "description": "負責結構設計、耐震分析、結構計算、配筋設計",
        "system_prompt": (
            "你是執業結構技師助理。回答時以結構工程專業為核心，"
            "注重結構安全、耐震設計、載重分析、配筋計算。"
            "引用規範以建築物耐震設計規範為主。"
        ),
        "keywords": [
            "結構", "耐震", "配筋", "搭接", "斷面", "彎矩", "剪力",
            "載重", "地震力", "鋼構", "RC", "SRC", "預力", "基樁",
            "結構計算", "結構簽證", "韌性設計",
        ],
        "categories": ["施工技術"],
    },
    "enterprise_owner": {
        "name": "企業老闆",
        "icon": "🏢",
        "collection": "jarvis_role_enterprise",
        "description": "負責企業經營策略、投標決策、財務規劃、人力資源",
        "system_prompt": (
            "你是營建企業經營顧問。回答時以企業經營視角為核心，"
            "注重投資報酬、風險評估、市場分析、人才管理。"
            "建議需考慮現金流和長期發展。"
        ),
        "keywords": [
            "經營", "策略", "投標", "標案", "利潤", "營收", "現金流",
            "人力", "組織", "市場", "競爭", "品牌", "擴張", "併購",
            "融資", "銀行", "保證金", "週轉",
        ],
        "categories": ["管理協調"],
    },
    "subcontractor_owner": {
        "name": "分包商老闆",
        "icon": "🤝",
        "collection": "jarvis_role_subcontractor",
        "description": "負責分包工程承攬、報價、施工團隊管理、與總包協調",
        "system_prompt": (
            "你是分包商經營顧問。回答時以分包商立場為核心，"
            "注重報價策略、合約風險、工班管理、與總包的權利義務。"
            "建議需務實可執行，考慮資金壓力。"
        ),
        "keywords": [
            "分包", "報價", "單價", "工班", "師傅", "材料", "備料",
            "追加", "變更", "扣款", "罰款", "保留款", "請款",
            "總包", "協調", "介面", "工期",
        ],
        "categories": ["採購履約", "管理協調"],
    },
    "small_contractor": {
        "name": "小包商老闆",
        "icon": "👷",
        "collection": "jarvis_role_small_contractor",
        "description": "負責專項工程施作、點工計價、現場施工、工具設備",
        "system_prompt": (
            "你是小包商實務顧問。回答時以小包商（點工、專項施作）立場為核心，"
            "注重施工效率、工具選用、安全防護、計價方式。"
            "建議需簡單直接，考慮人力和工具限制。"
        ),
        "keywords": [
            "點工", "工資", "日薪", "技術工", "粗工", "工具", "設備",
            "施作", "手工", "焊接", "綁紮", "泥作", "油漆", "水電",
            "防水", "磁磚", "木作",
        ],
        "categories": ["施工技術"],
    },
    # ── 新增角色（含 MCP 工作流） ──────────────────────────────
    "software_engineer": {
        "name": "網頁/軟件編碼工程師",
        "icon": "💻",
        "collection": "jarvis_role_software",
        "description": "負責網頁開發、軟體撰寫、API 設計、前後端架構、程式碼審查",
        "system_prompt": (
            "你是全端軟體工程師助理。回答時以程式碼品質、架構設計為核心，"
            "注重可維護性、效能、安全性。提供的方案需包含具體技術選型和實作步驟。"
            "優先使用免費開源方案，減少外部 API 呼叫成本。"
        ),
        "keywords": [
            "程式", "code", "python", "javascript", "html", "css", "react",
            "vue", "api", "backend", "frontend", "database", "sql", "git",
            "docker", "deploy", "debug", "test", "架構", "框架", "套件",
            "npm", "pip", "fastapi", "flask", "node", "typescript",
        ],
        "categories": ["自動化AI"],
        "mcp_tools": {
            "research": ["fetch", "open-web-search", "arxiv-research"],
            "execute": ["filesystem-restricted", "git", "docker-mcp", "playwright", "puppeteer"],
            "verify": ["playwright", "puppeteer", "fetch"],
            "optimize": ["sequential-thinking", "memory-service"],
        },
    },
    "investment_analyst": {
        "name": "投資顧問分析師",
        "icon": "📈",
        "collection": "jarvis_role_investment",
        "description": "負責投資標的分析、風險評估、資產配置建議、市場研究",
        "system_prompt": (
            "你是專業投資顧問分析師。回答時以數據驅動為核心，"
            "注重風險報酬比、基本面分析、技術面判讀、總經指標。"
            "必須附帶風險警語，建議需考慮投資人風險承受度。"
            "優先使用免費公開資料源進行分析。"
        ),
        "keywords": [
            "投資", "股票", "基金", "ETF", "債券", "報酬", "風險",
            "配置", "分散", "殖利率", "本益比", "營收", "EPS",
            "技術分析", "K線", "均線", "RSI", "MACD", "量價",
            "美股", "台股", "加密貨幣", "crypto",
        ],
        "categories": ["其他"],
        "mcp_tools": {
            "research": ["fetch", "open-web-search", "yahoo-finance"],
            "execute": ["yahoo-finance", "sqlite-local", "fetch"],
            "verify": ["yahoo-finance", "open-web-search"],
            "optimize": ["sequential-thinking", "memory-service"],
        },
    },
    "trend_analyst": {
        "name": "大趨勢預測分析師",
        "icon": "🔮",
        "collection": "jarvis_role_trend",
        "description": "負責產業趨勢預測、科技發展分析、市場走向研判、宏觀經濟預測",
        "system_prompt": (
            "你是大趨勢預測分析師。回答時以宏觀視角為核心，"
            "結合歷史數據、產業週期、科技演進、地緣政治進行趨勢研判。"
            "預測需標明信心度和時間框架，列出關鍵變數和轉折訊號。"
            "優先使用免費公開資料和新聞源。"
        ),
        "keywords": [
            "趨勢", "預測", "未來", "產業", "科技", "AI", "半導體",
            "能源", "電動車", "綠能", "人口", "通膨", "利率",
            "地緣政治", "供應鏈", "數位轉型", "元宇宙", "量子",
        ],
        "categories": ["其他"],
        "mcp_tools": {
            "research": ["fetch", "open-web-search", "yahoo-finance", "arxiv-research"],
            "execute": ["yahoo-finance", "sqlite-local", "fetch"],
            "verify": ["open-web-search", "yahoo-finance"],
            "optimize": ["sequential-thinking", "memory-service"],
        },
    },
    "divination_master": {
        "name": "占卜師",
        "icon": "🔯",
        "collection": "jarvis_role_divination",
        "description": "負責塔羅牌解讀、易經卦象、星座運勢、紫微斗數、風水分析",
        "system_prompt": (
            "你是資深占卜師與命理顧問。回答時以東西方命理體系為基礎，"
            "結合塔羅、易經、星座、紫微斗數等工具進行解讀。"
            "解讀需正面引導，提供具體行動建議，避免過度恐嚇。"
            "強調命理為參考，最終決定權在問卜者。"
        ),
        "keywords": [
            "塔羅", "占卜", "星座", "運勢", "紫微", "斗數", "易經",
            "卦象", "風水", "八字", "命盤", "流年", "大運",
            "感情", "事業", "財運", "健康", "桃花",
        ],
        "categories": ["其他"],
        "mcp_tools": {
            "research": ["open-web-search", "fetch"],
            "execute": ["sqlite-local", "memory-service"],
            "verify": ["open-web-search"],
            "optimize": ["sequential-thinking", "memory-service"],
        },
    },
    "financial_advisor": {
        "name": "金融顧問",
        "icon": "🏦",
        "collection": "jarvis_role_financial",
        "description": "負責財務規劃、稅務諮詢、保險規劃、退休規劃、資產傳承",
        "system_prompt": (
            "你是專業金融顧問。回答時以個人/企業財務規劃為核心，"
            "注重稅務效率、風險轉嫁、現金流管理、長期財富累積。"
            "建議需符合台灣法規，標明適用條文。"
            "優先使用免費公開資料和政府資源。"
        ),
        "keywords": [
            "財務", "稅務", "所得稅", "營業稅", "保險", "壽險", "產險",
            "退休", "勞保", "勞退", "年金", "信託", "遺產", "贈與",
            "貸款", "房貸", "利率", "現金流", "節稅",
        ],
        "categories": ["其他"],
        "mcp_tools": {
            "research": ["fetch", "open-web-search", "yahoo-finance"],
            "execute": ["yahoo-finance", "sqlite-local", "fetch"],
            "verify": ["yahoo-finance", "open-web-search"],
            "optimize": ["sequential-thinking", "memory-service"],
        },
    },
    "media_creator": {
        "name": "影音創作工程師",
        "icon": "🎬",
        "collection": "jarvis_role_media",
        "description": "負責影片企劃、腳本撰寫、剪輯流程、特效合成、音效配樂、社群經營",
        "system_prompt": (
            "你是影音創作工程師助理。回答時以內容創作和技術實現為核心，"
            "注重敘事結構、視覺呈現、音效設計、平台演算法。"
            "建議需包含具體工具選用和工作流程，優先使用免費/開源工具。"
        ),
        "keywords": [
            "影片", "剪輯", "腳本", "分鏡", "特效", "動畫", "配樂",
            "音效", "字幕", "縮圖", "YouTube", "TikTok", "Reels",
            "Premiere", "DaVinci", "After Effects", "OBS", "直播",
            "SEO", "演算法", "流量", "訂閱",
        ],
        "categories": ["其他"],
        "mcp_tools": {
            "research": ["fetch", "open-web-search", "puppeteer"],
            "execute": ["filesystem-restricted", "ffmpeg-video", "puppeteer"],
            "verify": ["puppeteer", "fetch"],
            "optimize": ["sequential-thinking", "memory-service"],
        },
    },
}

MASTER_COLLECTION = "jarvis_training"


# ═══════════════════════════════════════════
# 公開 API
# ═══════════════════════════════════════════

def list_roles() -> list[dict[str, Any]]:
    """列出所有可用角色。"""
    result = []
    for role_id, role in ROLES.items():
        result.append({
            "id": role_id,
            "name": role["name"],
            "icon": role["icon"],
            "description": role["description"],
            "collection": role["collection"],
        })
    return result


def get_role(role_id: str) -> dict[str, Any] | None:
    """取得角色定義。"""
    return ROLES.get(role_id)


def get_role_collection_name(role_id: str) -> str:
    """取得角色的 ChromaDB collection 名稱。"""
    role = ROLES.get(role_id)
    if role:
        return role["collection"]
    return MASTER_COLLECTION


def get_role_system_prompt(role_id: str) -> str:
    """取得角色的系統提示詞。"""
    role = ROLES.get(role_id)
    if role:
        return role["system_prompt"]
    return "你是工地智腦。請優先根據提供的本地知識回答，條列、精準、可執行。"


def classify_to_role(text: str) -> str:
    """根據文字內容自動分類到最適合的角色。"""
    t = (text or "").lower()
    scores: dict[str, int] = {}
    for role_id, role in ROLES.items():
        score = 0
        for kw in role.get("keywords", []):
            if kw.lower() in t:
                score += 1
        scores[role_id] = score
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else ""


def get_role_collection(role_id: str):
    """取得角色專屬的 ChromaDB collection（自動建立）。"""
    import chromadb
    db_dir = ROOT / "Jarvis_Training" / "chroma_db"
    db_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(db_dir))
    coll_name = get_role_collection_name(role_id)
    return client.get_or_create_collection(
        name=coll_name,
        metadata={"hnsw:space": "cosine"},
    )


def get_master_collection():
    """取得共用大智庫 collection。"""
    import chromadb
    db_dir = ROOT / "Jarvis_Training" / "chroma_db"
    db_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(db_dir))
    return client.get_or_create_collection(
        name=MASTER_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


def role_learn(role_id: str, question: str, answer: str, source: str = "role_learn") -> dict[str, Any]:
    """將知識寫入角色專屬知識庫。"""
    import hashlib, time as _time
    import sys
    sys.path.insert(0, str(ROOT / "Jarvis_Training"))
    from local_learning_system import stable_embedding, log_event

    q = (question or "").strip()
    a = (answer or "").strip()
    if not q or not a:
        return {"ok": False, "error": "question/answer 不可為空"}

    role = ROLES.get(role_id)
    if not role:
        return {"ok": False, "error": f"角色 '{role_id}' 不存在"}

    coll = get_role_collection(role_id)
    h = hashlib.sha1((q + "\n" + a).encode("utf-8", errors="ignore")).hexdigest()[:12]
    new_id = f"role_{role_id}_{int(_time.time())}_{h}"
    coll.upsert(
        ids=[new_id],
        documents=[a],
        metadatas=[{"question": q, "source": source, "role": role_id}],
        embeddings=[stable_embedding(q + "\n" + a)],
    )
    log_event("role_learn", {"id": new_id, "role": role_id, "question": q[:100], "source": source})
    return {"ok": True, "id": new_id, "role": role_id, "collection": role["collection"]}


def role_search(role_id: str, query: str, top_k: int = 5, include_master: bool = True) -> list[dict[str, Any]]:
    """搜尋角色知識庫，可選擇是否也搜尋大智庫。"""
    import sys
    sys.path.insert(0, str(ROOT / "Jarvis_Training"))
    from local_learning_system import stable_embedding

    q = (query or "").strip()
    if not q:
        return []

    emb = stable_embedding(q)
    items: list[dict[str, Any]] = []

    # 1. 搜尋角色專屬知識庫
    role = ROLES.get(role_id)
    if role:
        try:
            coll = get_role_collection(role_id)
            if coll.count() > 0:
                result = coll.query(query_embeddings=[emb], n_results=max(1, top_k))
                ids = (result.get("ids") or [[]])[0]
                docs = (result.get("documents") or [[]])[0]
                metas = (result.get("metadatas") or [[]])[0]
                dists = (result.get("distances") or [[]])[0]
                for idx, rid in enumerate(ids):
                    meta = metas[idx] if idx < len(metas) and isinstance(metas[idx], dict) else {}
                    items.append({
                        "id": rid,
                        "question": meta.get("question", ""),
                        "answer": docs[idx] if idx < len(docs) else "",
                        "distance": float(dists[idx]) if idx < len(dists) and dists[idx] is not None else None,
                        "source": meta.get("source", ""),
                        "from": f"role:{role_id}",
                    })
        except Exception:
            pass

    # 2. 搜尋大智庫
    if include_master:
        try:
            master = get_master_collection()
            if master.count() > 0:
                result = master.query(query_embeddings=[emb], n_results=max(1, top_k))
                ids = (result.get("ids") or [[]])[0]
                docs = (result.get("documents") or [[]])[0]
                metas = (result.get("metadatas") or [[]])[0]
                dists = (result.get("distances") or [[]])[0]
                for idx, rid in enumerate(ids):
                    meta = metas[idx] if idx < len(metas) and isinstance(metas[idx], dict) else {}
                    items.append({
                        "id": rid,
                        "question": meta.get("question", ""),
                        "answer": docs[idx] if idx < len(docs) else "",
                        "distance": float(dists[idx]) if idx < len(dists) and dists[idx] is not None else None,
                        "source": meta.get("source", ""),
                        "from": "master",
                    })
        except Exception:
            pass

    # 依距離排序（越小越相關）
    items.sort(key=lambda x: x.get("distance") or 999)
    return items[:top_k * 2]


def role_ask(role_id: str, query: str, top_k: int = 5) -> dict[str, Any]:
    """以角色身份回答問題（角色知識庫 + 大智庫 + 角色提示詞）。"""
    import sys
    sys.path.insert(0, str(ROOT / "Jarvis_Training"))
    from local_learning_system import ollama_generate, log_event

    q = (query or "").strip()
    if not q:
        return {"ok": False, "error": "問題不可為空"}

    role = ROLES.get(role_id)
    if not role:
        return {"ok": False, "error": f"角色 '{role_id}' 不存在"}

    hits = role_search(role_id, q, top_k=top_k)
    context_lines = []
    for i, h in enumerate(hits, start=1):
        src_label = "專業庫" if h.get("from", "").startswith("role:") else "通識庫"
        qh = h.get("question", "").strip()
        ah = h.get("answer", "").strip()
        context_lines.append(f"[{src_label} 參考{i}] 問題: {qh}\n[{src_label} 參考{i}] 答案: {ah}")
    context = "\n\n".join(context_lines)

    system_prompt = role["system_prompt"]
    prompt = (
        f"{system_prompt}\n\n"
        f"你的角色：{role['name']}（{role['description']}）\n\n"
        f"本地知識:\n{context or '（暫無命中記憶）'}\n\n"
        f"使用者問題:\n{q}\n\n"
        "請輸出：1) 結論 2) 依據 3) 建議行動"
    )
    try:
        answer = ollama_generate(prompt)
    except Exception as e:
        answer = f"模型暫時不可用：{e}\n\n以下是檢索結果：\n{context}"
        log_event("role_ask_fallback", {"role": role_id, "query": q, "error": str(e)})

    log_event("role_ask", {"role": role_id, "query": q, "hits": len(hits)})
    return {
        "ok": True,
        "role": role_id,
        "role_name": role["name"],
        "answer": answer,
        "hits": len(hits),
        "sources": [{"from": h.get("from", ""), "question": h.get("question", "")[:60]} for h in hits[:5]],
    }


def role_stats(role_id: str) -> dict[str, Any]:
    """取得角色知識庫統計。"""
    role = ROLES.get(role_id)
    if not role:
        return {"ok": False, "error": f"角色 '{role_id}' 不存在"}
    try:
        coll = get_role_collection(role_id)
        master = get_master_collection()
        return {
            "ok": True,
            "role": role_id,
            "role_name": role["name"],
            "role_count": coll.count(),
            "master_count": master.count(),
            "collection": role["collection"],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def all_roles_stats() -> dict[str, Any]:
    """取得所有角色知識庫統計。"""
    stats = []
    master_count = 0
    try:
        master = get_master_collection()
        master_count = master.count()
    except Exception:
        pass
    for role_id, role in ROLES.items():
        count = 0
        try:
            coll = get_role_collection(role_id)
            count = coll.count()
        except Exception:
            pass
        stats.append({
            "id": role_id,
            "name": role["name"],
            "icon": role["icon"],
            "count": count,
            "collection": role["collection"],
        })
    return {
        "ok": True,
        "master_count": master_count,
        "roles": stats,
        "total_roles": len(ROLES),
    }
