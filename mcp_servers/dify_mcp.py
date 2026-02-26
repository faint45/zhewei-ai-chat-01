#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
築未科技 Dify MCP Server
整合 Dify AI 平台 API，提供對話、工作流、知識庫等功能
"""
import json
import os
from typing import Any

try:
    import httpx
except ImportError:
    httpx = None

from mcp.server.fastmcp import FastMCP

SERVER_NAME = "dify_mcp"
mcp = FastMCP(SERVER_NAME)

DIFY_API_URL = os.environ.get("DIFY_API_URL", "http://localhost:8080/v1")
DIFY_API_KEY = os.environ.get("DIFY_API_KEY", "")


def _get_headers() -> dict[str, str]:
    if not DIFY_API_KEY:
        raise ValueError("DIFY_API_KEY 環境變數未設定")
    return {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json",
    }


@mcp.tool(
    name="dify_chat",
    annotations={
        "title": "Chat with Dify AI",
        "description": "與 Dify AI 對話",
    },
)
def dify_chat(message: str, conversation_id: str = "", user: str = "mcp-user") -> str:
    if not httpx:
        return json.dumps({"ok": False, "error": "httpx 未安裝，請執行: pip install httpx"}, ensure_ascii=False)
    
    try:
        url = f"{DIFY_API_URL}/chat-messages"
        payload = {
            "inputs": {},
            "query": message,
            "response_mode": "blocking",
            "user": user,
        }
        if conversation_id:
            payload["conversation_id"] = conversation_id
        
        with httpx.Client() as client:
            response = client.post(url, headers=_get_headers(), json=payload, timeout=60.0)
            response.raise_for_status()
            data = response.json()
        
        return json.dumps({
            "ok": True,
            "answer": data.get("answer", ""),
            "conversation_id": data.get("conversation_id", ""),
            "message_id": data.get("message_id", ""),
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)


@mcp.tool(
    name="dify_run_workflow",
    annotations={
        "title": "Run Dify workflow",
        "description": "執行 Dify 工作流",
    },
)
def dify_run_workflow(inputs: dict[str, Any], user: str = "mcp-user") -> str:
    if not httpx:
        return json.dumps({"ok": False, "error": "httpx 未安裝，請執行: pip install httpx"}, ensure_ascii=False)
    
    try:
        url = f"{DIFY_API_URL}/workflows/run"
        payload = {
            "inputs": inputs,
            "response_mode": "blocking",
            "user": user,
        }
        
        with httpx.Client() as client:
            response = client.post(url, headers=_get_headers(), json=payload, timeout=120.0)
            response.raise_for_status()
            data = response.json()
        
        return json.dumps({
            "ok": True,
            "workflow_run_id": data.get("workflow_run_id", ""),
            "task_id": data.get("task_id", ""),
            "data": data.get("data", {}),
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)


@mcp.tool(
    name="dify_get_conversations",
    annotations={
        "title": "Get conversation history",
        "description": "取得對話歷史",
    },
)
def dify_get_conversations(user: str = "mcp-user", limit: int = 20) -> str:
    if not httpx:
        return json.dumps({"ok": False, "error": "httpx 未安裝，請執行: pip install httpx"}, ensure_ascii=False)
    
    try:
        url = f"{DIFY_API_URL}/conversations"
        params = {
            "user": user,
            "limit": limit,
        }
        
        with httpx.Client() as client:
            response = client.get(url, headers=_get_headers(), params=params, timeout=30.0)
            response.raise_for_status()
            data = response.json()
        
        return json.dumps({
            "ok": True,
            "conversations": data.get("data", []),
            "total": data.get("total", 0),
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)


@mcp.tool(
    name="dify_get_messages",
    annotations={
        "title": "Get conversation messages",
        "description": "取得對話訊息",
    },
)
def dify_get_messages(conversation_id: str, user: str = "mcp-user", limit: int = 20) -> str:
    if not httpx:
        return json.dumps({"ok": False, "error": "httpx 未安裝，請執行: pip install httpx"}, ensure_ascii=False)
    
    try:
        url = f"{DIFY_API_URL}/messages"
        params = {
            "conversation_id": conversation_id,
            "user": user,
            "limit": limit,
        }
        
        with httpx.Client() as client:
            response = client.get(url, headers=_get_headers(), params=params, timeout=30.0)
            response.raise_for_status()
            data = response.json()
        
        return json.dumps({
            "ok": True,
            "messages": data.get("data", []),
            "total": data.get("total", 0),
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)


@mcp.tool(
    name="dify_feedback",
    annotations={
        "title": "Send message feedback",
        "description": "對訊息提供回饋（讚/踩）",
    },
)
def dify_feedback(message_id: str, rating: str, user: str = "mcp-user") -> str:
    if not httpx:
        return json.dumps({"ok": False, "error": "httpx 未安裝，請執行: pip install httpx"}, ensure_ascii=False)
    
    if rating not in ["like", "dislike"]:
        return json.dumps({"ok": False, "error": "rating 必須是 'like' 或 'dislike'"}, ensure_ascii=False)
    
    try:
        url = f"{DIFY_API_URL}/messages/{message_id}/feedbacks"
        payload = {
            "rating": rating,
            "user": user,
        }
        
        with httpx.Client() as client:
            response = client.post(url, headers=_get_headers(), json=payload, timeout=30.0)
            response.raise_for_status()
            data = response.json()
        
        return json.dumps({"ok": True, "result": data}, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)


@mcp.tool(
    name="dify_get_parameters",
    annotations={
        "title": "Get app parameters",
        "description": "取得應用參數",
    },
)
def dify_get_parameters(user: str = "mcp-user") -> str:
    if not httpx:
        return json.dumps({"ok": False, "error": "httpx 未安裝，請執行: pip install httpx"}, ensure_ascii=False)
    
    try:
        url = f"{DIFY_API_URL}/parameters"
        params = {"user": user}
        
        with httpx.Client() as client:
            response = client.get(url, headers=_get_headers(), params=params, timeout=30.0)
            response.raise_for_status()
            data = response.json()
        
        return json.dumps({"ok": True, "parameters": data}, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
