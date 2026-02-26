# -*- coding: utf-8 -*-
"""
築未科技 — 知識庫快照匯出/匯入 + 差量同步
──────────────────────────────────────────
商用核心模組：
  - 匯出：將 ChromaDB Collection 匯出為 JSON 快照（含 embeddings）
  - 匯入：從 JSON 快照匯入到客戶端 ChromaDB（upsert，不重複）
  - 差量同步：只傳送 version 之後新增/修改的文件
  - 版本管理：每次匯出產生遞增版本號

快照格式：
  {
    "version": 42,
    "collection": "jarvis_training",
    "exported_at": "2026-02-14T10:00:00",
    "total_items": 14662,
    "items": [
      {"id": "...", "document": "...", "metadata": {...}, "embedding": [...]},
      ...
    ]
  }
"""

import gzip
import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import numpy as np
    _has_numpy = True
except ImportError:
    _has_numpy = False


class _NumpyEncoder(json.JSONEncoder):
    """JSON encoder that handles numpy arrays and types."""
    def default(self, obj):
        if _has_numpy:
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
        return super().default(obj)

import chromadb

# ── 設定 ──
ROOT = Path(__file__).resolve().parent
JARVIS_DB = ROOT / "Jarvis_Training" / "chroma_db"
SNAPSHOT_DIR = ROOT / "brain_workspace" / "kb_snapshots"
VERSION_FILE = SNAPSHOT_DIR / "version.json"

DEFAULT_COLLECTION = os.environ.get("LEARNING_COLLECTION", "jarvis_training").strip()


# =====================================================================
# 版本管理
# =====================================================================

def _get_version_info() -> dict:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    if VERSION_FILE.exists():
        try:
            return json.loads(VERSION_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"current_version": 0, "history": []}


def _save_version_info(info: dict):
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    VERSION_FILE.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")


def _next_version() -> int:
    info = _get_version_info()
    return info.get("current_version", 0) + 1


# =====================================================================
# 匯出（伺服器端）
# =====================================================================

def export_snapshot(
    collection_name: str = "",
    db_path: str = "",
    include_embeddings: bool = True,
    compress: bool = True,
    max_items: int = -1,
) -> dict:
    """
    匯出 ChromaDB Collection 為 JSON 快照。

    Args:
        collection_name: Collection 名稱（預設 jarvis_training）
        db_path: ChromaDB 路徑（預設 Jarvis_Training/chroma_db）
        include_embeddings: 是否包含 embedding 向量（客戶端匯入時需要）
        compress: 是否 gzip 壓縮
        max_items: 最大匯出數量（-1 = 全部）

    Returns:
        {"ok": True, "version": 42, "file": "...", "items": 14662, "size_mb": 12.3}
    """
    coll_name = collection_name or DEFAULT_COLLECTION
    db = db_path or str(JARVIS_DB)

    try:
        client = chromadb.PersistentClient(path=db)
        coll = client.get_collection(name=coll_name)
    except Exception as e:
        return {"ok": False, "error": f"無法開啟 Collection '{coll_name}': {e}"}

    total = coll.count()
    if total == 0:
        return {"ok": False, "error": f"Collection '{coll_name}' 是空的"}

    # 分批讀取（ChromaDB 一次最多 ~10000）
    batch_size = 5000
    all_items = []
    offset = 0

    while True:
        limit = batch_size
        if max_items > 0:
            limit = min(batch_size, max_items - len(all_items))
            if limit <= 0:
                break

        include_fields = ["documents", "metadatas"]
        if include_embeddings:
            include_fields.append("embeddings")

        try:
            result = coll.get(
                limit=limit,
                offset=offset,
                include=include_fields,
            )
        except Exception as e:
            return {"ok": False, "error": f"讀取失敗 offset={offset}: {e}"}

        ids = result.get("ids", [])
        if not ids:
            break

        docs = result.get("documents", [])
        metas = result.get("metadatas", [])
        embeds = result.get("embeddings", []) if include_embeddings else []

        for i, doc_id in enumerate(ids):
            item = {
                "id": doc_id,
                "document": docs[i] if i < len(docs) else "",
                "metadata": metas[i] if i < len(metas) else {},
            }
            if include_embeddings and i < len(embeds):
                item["embedding"] = embeds[i]
            all_items.append(item)

        offset += len(ids)
        if len(ids) < limit:
            break

        print(f"  [export] {len(all_items)}/{total} items read...")

    # 產生版本號
    version = _next_version()
    now = datetime.now()

    snapshot = {
        "version": version,
        "collection": coll_name,
        "exported_at": now.isoformat(timespec="seconds"),
        "total_items": len(all_items),
        "include_embeddings": include_embeddings,
        "items": all_items,
    }

    # 寫入檔案
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    fname = f"kb_v{version}_{coll_name}_{now.strftime('%Y%m%d_%H%M%S')}"

    if compress:
        fpath = SNAPSHOT_DIR / f"{fname}.json.gz"
        with gzip.open(fpath, "wt", encoding="utf-8", compresslevel=6) as f:
            json.dump(snapshot, f, ensure_ascii=False, cls=_NumpyEncoder)
    else:
        fpath = SNAPSHOT_DIR / f"{fname}.json"
        fpath.write_text(json.dumps(snapshot, ensure_ascii=False, cls=_NumpyEncoder), encoding="utf-8")

    size_mb = round(fpath.stat().st_size / (1024 * 1024), 2)

    # 更新版本記錄
    info = _get_version_info()
    info["current_version"] = version
    info["history"].append({
        "version": version,
        "file": fpath.name,
        "collection": coll_name,
        "items": len(all_items),
        "size_mb": size_mb,
        "exported_at": now.isoformat(timespec="seconds"),
    })
    # 只保留最近 50 個版本記錄
    info["history"] = info["history"][-50:]
    _save_version_info(info)

    print(f"  [export] ✅ v{version} — {len(all_items)} items → {fpath.name} ({size_mb} MB)")
    return {
        "ok": True,
        "version": version,
        "file": str(fpath),
        "filename": fpath.name,
        "items": len(all_items),
        "size_mb": size_mb,
        "collection": coll_name,
    }


# =====================================================================
# 差量匯出（只匯出指定版本之後新增的）
# =====================================================================

def export_delta(
    since_version: int,
    collection_name: str = "",
    db_path: str = "",
    compress: bool = True,
) -> dict:
    """
    差量匯出：只匯出 since_version 之後新增的文件。
    依據 metadata.time 欄位判斷新舊。
    """
    coll_name = collection_name or DEFAULT_COLLECTION
    db = db_path or str(JARVIS_DB)

    # 找到 since_version 的匯出時間
    info = _get_version_info()
    since_time = None
    for h in info.get("history", []):
        if h.get("version") == since_version:
            since_time = h.get("exported_at")
            break

    if not since_time:
        return {"ok": False, "error": f"找不到版本 {since_version} 的記錄，請使用完整匯出"}

    try:
        client = chromadb.PersistentClient(path=db)
        coll = client.get_collection(name=coll_name)
    except Exception as e:
        return {"ok": False, "error": f"無法開啟 Collection: {e}"}

    # 讀取全部（ChromaDB 不支援 where > time 的高效查詢，需全量掃描）
    total = coll.count()
    batch_size = 5000
    delta_items = []
    offset = 0

    while True:
        result = coll.get(
            limit=batch_size,
            offset=offset,
            include=["documents", "metadatas", "embeddings"],
        )
        ids = result.get("ids", [])
        if not ids:
            break

        docs = result.get("documents", [])
        metas = result.get("metadatas", [])
        embeds = result.get("embeddings", [])

        for i, doc_id in enumerate(ids):
            meta = metas[i] if i < len(metas) else {}
            item_time = meta.get("time", "")
            # 只取 since_time 之後的
            if item_time and item_time > since_time:
                item = {
                    "id": doc_id,
                    "document": docs[i] if i < len(docs) else "",
                    "metadata": meta,
                }
                if i < len(embeds):
                    item["embedding"] = embeds[i]
                delta_items.append(item)

        offset += len(ids)
        if len(ids) < batch_size:
            break

    if not delta_items:
        return {"ok": True, "version": info.get("current_version", 0), "items": 0, "message": "無新增資料"}

    version = _next_version()
    now = datetime.now()

    snapshot = {
        "version": version,
        "delta_from": since_version,
        "collection": coll_name,
        "exported_at": now.isoformat(timespec="seconds"),
        "total_items": len(delta_items),
        "include_embeddings": True,
        "items": delta_items,
    }

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    fname = f"kb_delta_v{since_version}_to_v{version}_{now.strftime('%Y%m%d_%H%M%S')}"

    if compress:
        fpath = SNAPSHOT_DIR / f"{fname}.json.gz"
        with gzip.open(fpath, "wt", encoding="utf-8", compresslevel=6) as f:
            json.dump(snapshot, f, ensure_ascii=False, cls=_NumpyEncoder)
    else:
        fpath = SNAPSHOT_DIR / f"{fname}.json"
        fpath.write_text(json.dumps(snapshot, ensure_ascii=False, cls=_NumpyEncoder), encoding="utf-8")

    size_mb = round(fpath.stat().st_size / (1024 * 1024), 2)

    info["current_version"] = version
    info["history"].append({
        "version": version,
        "delta_from": since_version,
        "file": fpath.name,
        "collection": coll_name,
        "items": len(delta_items),
        "size_mb": size_mb,
        "exported_at": now.isoformat(timespec="seconds"),
    })
    info["history"] = info["history"][-50:]
    _save_version_info(info)

    print(f"  [delta] ✅ v{since_version}→v{version} — {len(delta_items)} new items ({size_mb} MB)")
    return {
        "ok": True,
        "version": version,
        "delta_from": since_version,
        "file": str(fpath),
        "filename": fpath.name,
        "items": len(delta_items),
        "size_mb": size_mb,
    }


# =====================================================================
# 匯入（客戶端）
# =====================================================================

def import_snapshot(
    snapshot_file: str,
    collection_name: str = "",
    db_path: str = "",
    skip_existing: bool = True,
) -> dict:
    """
    從 JSON 快照匯入到 ChromaDB。

    Args:
        snapshot_file: 快照檔案路徑（.json 或 .json.gz）
        collection_name: 目標 Collection（預設用快照中記錄的）
        db_path: ChromaDB 路徑
        skip_existing: 跳過已存在的 ID

    Returns:
        {"ok": True, "imported": 1234, "skipped": 56, "errors": 0}
    """
    fpath = Path(snapshot_file)
    if not fpath.exists():
        return {"ok": False, "error": f"檔案不存在: {snapshot_file}"}

    # 讀取快照
    try:
        if fpath.suffix == ".gz" or str(fpath).endswith(".json.gz"):
            with gzip.open(fpath, "rt", encoding="utf-8") as f:
                snapshot = json.load(f)
        else:
            snapshot = json.loads(fpath.read_text(encoding="utf-8"))
    except Exception as e:
        return {"ok": False, "error": f"讀取快照失敗: {e}"}

    coll_name = collection_name or snapshot.get("collection", DEFAULT_COLLECTION)
    db = db_path or str(JARVIS_DB)
    items = snapshot.get("items", [])

    if not items:
        return {"ok": True, "imported": 0, "skipped": 0, "errors": 0, "message": "快照為空"}

    try:
        client = chromadb.PersistentClient(path=db)
        coll = client.get_or_create_collection(
            name=coll_name,
            metadata={"hnsw:space": "cosine"},
        )
    except Exception as e:
        return {"ok": False, "error": f"無法開啟 Collection: {e}"}

    imported = 0
    skipped = 0
    errors = 0

    # 分批 upsert（ChromaDB 建議每批 <= 5000）
    batch_size = 500
    for batch_start in range(0, len(items), batch_size):
        batch = items[batch_start:batch_start + batch_size]

        batch_ids = []
        batch_docs = []
        batch_metas = []
        batch_embeds = []
        has_embeddings = False

        for item in batch:
            doc_id = item.get("id", "")
            if not doc_id:
                errors += 1
                continue

            # 檢查是否已存在
            if skip_existing:
                try:
                    existing = coll.get(ids=[doc_id], include=[])
                    if existing.get("ids"):
                        skipped += 1
                        continue
                except Exception:
                    pass

            batch_ids.append(doc_id)
            batch_docs.append(item.get("document", ""))
            batch_metas.append(item.get("metadata", {}))
            if "embedding" in item and item["embedding"]:
                batch_embeds.append(item["embedding"])
                has_embeddings = True

        if not batch_ids:
            continue

        try:
            kwargs = {
                "ids": batch_ids,
                "documents": batch_docs,
                "metadatas": batch_metas,
            }
            if has_embeddings and len(batch_embeds) == len(batch_ids):
                kwargs["embeddings"] = batch_embeds
            coll.upsert(**kwargs)
            imported += len(batch_ids)
        except Exception as e:
            errors += len(batch_ids)
            print(f"  [import] batch error: {e}")

        if (batch_start + batch_size) % 2000 == 0:
            print(f"  [import] {batch_start + len(batch)}/{len(items)} processed...")

    # 更新客戶端同步狀態
    try:
        from client_config import get_config
        cfg = get_config()
        cfg.update_sync_state(
            version=snapshot.get("version", 0),
            items_synced=imported,
        )
    except Exception:
        pass

    print(f"  [import] ✅ imported={imported} skipped={skipped} errors={errors}")
    return {
        "ok": True,
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
        "version": snapshot.get("version", 0),
        "collection": coll_name,
    }


# =====================================================================
# 查詢 API
# =====================================================================

def get_snapshot_info() -> dict:
    """取得快照版本資訊"""
    info = _get_version_info()
    return {
        "current_version": info.get("current_version", 0),
        "total_snapshots": len(info.get("history", [])),
        "history": info.get("history", [])[-10:],  # 最近 10 個
    }


def list_snapshots() -> list[dict]:
    """列出所有快照檔案"""
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    result = []
    for f in sorted(SNAPSHOT_DIR.glob("kb_*.json*")):
        result.append({
            "filename": f.name,
            "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
            "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(timespec="seconds"),
        })
    return result


# =====================================================================
# 多 Collection 批次匯出（角色庫 + 通識庫）
# =====================================================================

def export_all_collections(
    collections: list[str] | None = None,
    compress: bool = True,
) -> dict:
    """
    批次匯出多個 Collection（通識庫 + 角色庫）。
    """
    if not collections:
        # 自動偵測所有 jarvis_ 開頭的 Collection
        try:
            client = chromadb.PersistentClient(path=str(JARVIS_DB))
            all_colls = client.list_collections()
            collections = [c.name for c in all_colls if c.name.startswith("jarvis_")]
        except Exception as e:
            return {"ok": False, "error": f"無法列出 Collections: {e}"}

    results = []
    for coll_name in collections:
        print(f"\n[batch export] {coll_name}...")
        r = export_snapshot(collection_name=coll_name, compress=compress)
        results.append({"collection": coll_name, **r})

    success = sum(1 for r in results if r.get("ok"))
    return {
        "ok": success > 0,
        "total_collections": len(collections),
        "success": success,
        "results": results,
    }


# =====================================================================
# CLI
# =====================================================================

def _cli():
    import argparse
    parser = argparse.ArgumentParser(description="築未科技 知識庫快照工具")
    sub = parser.add_subparsers(dest="cmd")

    # export
    exp = sub.add_parser("export", help="匯出快照")
    exp.add_argument("--collection", default="", help="Collection 名稱")
    exp.add_argument("--no-compress", action="store_true")
    exp.add_argument("--no-embeddings", action="store_true")
    exp.add_argument("--max-items", type=int, default=-1)

    # delta
    delta = sub.add_parser("delta", help="差量匯出")
    delta.add_argument("--since", type=int, required=True, help="起始版本號")
    delta.add_argument("--collection", default="")

    # import
    imp = sub.add_parser("import", help="匯入快照")
    imp.add_argument("file", help="快照檔案路徑")
    imp.add_argument("--collection", default="")
    imp.add_argument("--force", action="store_true", help="不跳過已存在的")

    # export-all
    sub.add_parser("export-all", help="批次匯出所有 Collection")

    # info
    sub.add_parser("info", help="版本資訊")

    # list
    sub.add_parser("list", help="列出快照檔案")

    args = parser.parse_args()

    if args.cmd == "export":
        r = export_snapshot(
            collection_name=args.collection,
            include_embeddings=not args.no_embeddings,
            compress=not args.no_compress,
            max_items=args.max_items,
        )
        print(json.dumps(r, ensure_ascii=False, indent=2))

    elif args.cmd == "delta":
        r = export_delta(since_version=args.since, collection_name=args.collection)
        print(json.dumps(r, ensure_ascii=False, indent=2))

    elif args.cmd == "import":
        r = import_snapshot(
            snapshot_file=args.file,
            collection_name=args.collection,
            skip_existing=not getattr(args, "force", False),
        )
        print(json.dumps(r, ensure_ascii=False, indent=2))

    elif args.cmd == "export-all":
        r = export_all_collections()
        print(json.dumps(r, ensure_ascii=False, indent=2))

    elif args.cmd == "info":
        r = get_snapshot_info()
        print(json.dumps(r, ensure_ascii=False, indent=2))

    elif args.cmd == "list":
        snapshots = list_snapshots()
        if not snapshots:
            print("尚無快照檔案")
        for s in snapshots:
            print(f"  {s['filename']}  ({s['size_mb']} MB)  {s['modified']}")

    else:
        parser.print_help()


if __name__ == "__main__":
    _cli()
