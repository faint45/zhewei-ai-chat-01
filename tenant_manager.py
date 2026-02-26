# -*- coding: utf-8 -*-
"""
築未科技 — 多租戶管理模組

商用核心：每個企業客戶（租戶）擁有獨立的：
  1. 知識庫 Collection（ChromaDB，前綴隔離）
  2. 角色存取權限（依方案限制角色數量）
  3. 用量配額（獨立計量）
  4. 設定（自訂系統提示詞、品牌等）

Collection 命名規則：
  - 共用大智庫：jarvis_training（所有租戶共享的通識知識）
  - 租戶角色庫：t_{slug}_role_{role_id}
  - 租戶私有庫：t_{slug}_private

設計原則：
  - 租戶間資料完全隔離
  - 共用大智庫只讀（租戶不能寫入）
  - 無租戶時降級為原有行為（向後相容）
"""
import os
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent

# ── 訂閱方案角色限制 ──
PLAN_ROLE_LIMITS = {
    "free": 1,
    "basic": 9,
    "pro": 15,
    "enterprise": -1,   # 無限
    "unlimited": -1,
}

PLAN_KB_LIMITS = {
    "free": 2000,
    "basic": 20000,
    "pro": 50000,
    "enterprise": -1,
    "unlimited": -1,
}


def get_tenant_collection_name(tenant_slug: str, role_id: str) -> str:
    """取得租戶專屬的角色 Collection 名稱。"""
    if not tenant_slug:
        # 無租戶 → 使用原有命名（向後相容）
        import role_manager
        return role_manager.get_role_collection_name(role_id)
    slug = tenant_slug.lower().replace("-", "_")[:20]
    return f"t_{slug}_role_{role_id}"


def get_tenant_private_collection_name(tenant_slug: str) -> str:
    """取得租戶私有知識庫 Collection 名稱。"""
    slug = tenant_slug.lower().replace("-", "_")[:20]
    return f"t_{slug}_private"


def get_tenant_collection(tenant_slug: str, role_id: str):
    """取得租戶專屬的角色 ChromaDB Collection（自動建立）。"""
    import chromadb
    db_dir = ROOT / "Jarvis_Training" / "chroma_db"
    db_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(db_dir))
    coll_name = get_tenant_collection_name(tenant_slug, role_id)
    return client.get_or_create_collection(
        name=coll_name,
        metadata={"hnsw:space": "cosine"},
    )


def check_role_access(tenant_plan: str, role_id: str, available_roles: list[str]) -> bool:
    """檢查租戶方案是否允許使用該角色。"""
    limit = PLAN_ROLE_LIMITS.get(tenant_plan, 1)
    if limit == -1:
        return True
    # 取得角色在列表中的索引（前 N 個角色可用）
    if role_id not in available_roles:
        return False
    idx = available_roles.index(role_id)
    return idx < limit


def check_kb_quota(tenant_slug: str, tenant_plan: str) -> dict:
    """檢查租戶知識庫容量。"""
    limit = PLAN_KB_LIMITS.get(tenant_plan, 2000)
    if limit == -1:
        return {"allowed": True, "plan": tenant_plan, "limit": -1, "used": 0}

    # 計算租戶所有 Collection 的總筆數
    try:
        import chromadb
        db_dir = ROOT / "Jarvis_Training" / "chroma_db"
        client = chromadb.PersistentClient(path=str(db_dir))
        prefix = f"t_{tenant_slug.lower().replace('-', '_')[:20]}_"
        total = 0
        for coll in client.list_collections():
            if coll.name.startswith(prefix):
                total += coll.count()
        return {
            "allowed": total < limit,
            "plan": tenant_plan,
            "limit": limit,
            "used": total,
            "remaining": max(0, limit - total),
        }
    except Exception as e:
        return {"allowed": True, "error": str(e)}


def tenant_role_learn(
    tenant_slug: str, role_id: str, question: str, answer: str, source: str = "tenant_learn"
) -> dict[str, Any]:
    """將知識寫入租戶專屬角色知識庫。"""
    import hashlib
    import sys
    sys.path.insert(0, str(ROOT / "Jarvis_Training"))
    from local_learning_system import stable_embedding, log_event

    q = (question or "").strip()
    a = (answer or "").strip()
    if not q or not a:
        return {"ok": False, "error": "question/answer 不可為空"}

    coll = get_tenant_collection(tenant_slug, role_id)
    h = hashlib.sha1((q + "\n" + a).encode("utf-8", errors="ignore")).hexdigest()[:12]
    slug_short = (tenant_slug or "default")[:10]
    new_id = f"t_{slug_short}_{role_id}_{int(time.time())}_{h}"
    coll.upsert(
        ids=[new_id],
        documents=[a],
        metadatas=[{"question": q, "source": source, "role": role_id, "tenant": tenant_slug}],
        embeddings=[stable_embedding(q + "\n" + a)],
    )
    log_event("tenant_role_learn", {
        "id": new_id, "tenant": tenant_slug, "role": role_id, "question": q[:100],
    })
    return {"ok": True, "id": new_id, "tenant": tenant_slug, "role": role_id}


def tenant_role_search(
    tenant_slug: str, role_id: str, query: str, top_k: int = 5, include_master: bool = True
) -> list[dict[str, Any]]:
    """搜尋租戶角色知識庫 + 共用大智庫。"""
    import sys
    sys.path.insert(0, str(ROOT / "Jarvis_Training"))
    from local_learning_system import stable_embedding

    q = (query or "").strip()
    if not q:
        return []

    emb = stable_embedding(q)
    items: list[dict[str, Any]] = []

    # 1. 搜尋租戶專屬角色庫
    try:
        coll = get_tenant_collection(tenant_slug, role_id)
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
                    "from": f"tenant:{tenant_slug}:role:{role_id}",
                })
    except Exception:
        pass

    # 2. 搜尋共用大智庫（只讀）
    if include_master:
        try:
            import role_manager
            master = role_manager.get_master_collection()
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

    items.sort(key=lambda x: x.get("distance") or 999)
    return items[:top_k * 2]


def tenant_stats(tenant_slug: str) -> dict[str, Any]:
    """取得租戶所有知識庫統計。"""
    try:
        import chromadb
        import role_manager
        db_dir = ROOT / "Jarvis_Training" / "chroma_db"
        client = chromadb.PersistentClient(path=str(db_dir))
        prefix = f"t_{tenant_slug.lower().replace('-', '_')[:20]}_"
        collections = {}
        total = 0
        for coll in client.list_collections():
            if coll.name.startswith(prefix):
                count = coll.count()
                collections[coll.name] = count
                total += count
        master = role_manager.get_master_collection()
        return {
            "ok": True,
            "tenant": tenant_slug,
            "collections": collections,
            "total_entries": total,
            "master_count": master.count(),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_user_tenant_slug(user_id: str) -> str | None:
    """從用戶 ID 取得其所屬租戶的 slug。"""
    try:
        import db_postgres
        conn = db_postgres._get_conn()
        cur = conn.cursor()
        cur.execute(
            """SELECT t.slug FROM users u
               JOIN tenants t ON u.tenant_id = t.id
               WHERE u.id = %s::UUID""",
            (user_id,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None
