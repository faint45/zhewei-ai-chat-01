#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
築未科技 Weaviate MCP Server
提供向量資料庫操作、語意搜尋功能（整合 Dify 的 Weaviate）
"""
import json
import os
from typing import Any

try:
    import weaviate
    from weaviate.classes.query import MetadataQuery
except ImportError:
    weaviate = None

from mcp.server.fastmcp import FastMCP

SERVER_NAME = "weaviate_mcp"
mcp = FastMCP(SERVER_NAME)

WEAVIATE_URL = os.environ.get("WEAVIATE_URL", "http://localhost:8080")


def _get_client() -> Any:
    if not weaviate:
        raise RuntimeError("weaviate-client 未安裝，請執行: pip install weaviate-client")
    return weaviate.connect_to_local(host=WEAVIATE_URL.replace("http://", "").replace("https://", ""))


@mcp.tool(
    name="weaviate_list_classes",
    annotations={
        "title": "List all Weaviate classes",
        "description": "列出所有向量類別（schema）",
    },
)
def weaviate_list_classes() -> str:
    try:
        client = _get_client()
        schema = client.schema.get()
        classes = []
        for cls in schema.get("classes", []):
            classes.append({
                "name": cls.get("class"),
                "description": cls.get("description", ""),
                "properties_count": len(cls.get("properties", [])),
            })
        client.close()
        return json.dumps({"ok": True, "classes": classes}, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)


@mcp.tool(
    name="weaviate_get_schema",
    annotations={
        "title": "Get Weaviate schema",
        "description": "取得完整 schema 定義",
    },
)
def weaviate_get_schema() -> str:
    try:
        client = _get_client()
        schema = client.schema.get()
        client.close()
        return json.dumps({"ok": True, "schema": schema}, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)


@mcp.tool(
    name="weaviate_class_info",
    annotations={
        "title": "Get class information",
        "description": "取得特定類別的詳細資訊",
    },
)
def weaviate_class_info(class_name: str) -> str:
    try:
        client = _get_client()
        schema = client.schema.get(class_name)
        client.close()
        return json.dumps({"ok": True, "class_info": schema}, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)


@mcp.tool(
    name="weaviate_search",
    annotations={
        "title": "Search objects in Weaviate",
        "description": "語意搜尋（需提供 class_name 和 query）",
    },
)
def weaviate_search(class_name: str, query: str, limit: int = 5) -> str:
    try:
        client = _get_client()
        collection = client.collections.get(class_name)
        results = collection.query.near_text(
            query=query,
            limit=limit,
            return_metadata=MetadataQuery(distance=True)
        )
        
        hits = []
        for obj in results.objects:
            hits.append({
                "uuid": str(obj.uuid),
                "properties": obj.properties,
                "distance": obj.metadata.distance if hasattr(obj.metadata, 'distance') else None,
            })
        
        client.close()
        return json.dumps({"ok": True, "hits": hits}, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)


@mcp.tool(
    name="weaviate_get_objects",
    annotations={
        "title": "Get objects from class",
        "description": "取得類別中的物件（分頁）",
    },
)
def weaviate_get_objects(class_name: str, limit: int = 10, offset: int = 0) -> str:
    try:
        client = _get_client()
        collection = client.collections.get(class_name)
        results = collection.query.fetch_objects(limit=limit, offset=offset)
        
        objects = []
        for obj in results.objects:
            objects.append({
                "uuid": str(obj.uuid),
                "properties": obj.properties,
            })
        
        client.close()
        return json.dumps({
            "ok": True,
            "objects": objects,
            "count": len(objects),
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)


@mcp.tool(
    name="weaviate_stats",
    annotations={
        "title": "Get Weaviate statistics",
        "description": "取得統計資訊",
    },
)
def weaviate_stats() -> str:
    try:
        client = _get_client()
        schema = client.schema.get()
        
        stats = {
            "classes_count": len(schema.get("classes", [])),
            "classes": []
        }
        
        for cls in schema.get("classes", []):
            class_name = cls.get("class")
            try:
                collection = client.collections.get(class_name)
                aggregate = collection.aggregate.over_all(total_count=True)
                stats["classes"].append({
                    "name": class_name,
                    "objects_count": aggregate.total_count if hasattr(aggregate, 'total_count') else 0,
                })
            except Exception:
                stats["classes"].append({
                    "name": class_name,
                    "objects_count": "N/A",
                })
        
        client.close()
        return json.dumps({"ok": True, "stats": stats}, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
