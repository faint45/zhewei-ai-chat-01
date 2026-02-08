#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
築未科技七階段系統 HTTP API
暴露 RESTful 接口供外部調用
"""

import os
import sys
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from seven_stage_system import SevenStageSystem

app = FastAPI(title="七階段指揮作戰系統 API", version="1.0.0")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局系統實例
system = SevenStageSystem(workspace="D:/brain_workspace")

# 請求模型
class TaskRequest(BaseModel):
    """任務請求"""
    input: str
    priority: str = "medium"
    metadata: Dict[str, Any] = {}


class HealthResponse(BaseModel):
    """健康檢查響應"""
    status: str
    system: str
    roles: Dict[str, str]
    workspace: str


class TaskResponse(BaseModel):
    """任務響應"""
    task_id: str
    status: str
    result: Dict[str, Any]
    created_at: str


@app.get("/", summary="API 根路徑")
async def root():
    """API 根路徑"""
    return {
        "name": "七階段指揮作戰系統",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "execute": "/execute",
            "status": "/status"
        }
    }


@app.get("/health", response_model=HealthResponse, summary="健康檢查")
async def health_check():
    """檢查系統健康狀態"""
    return HealthResponse(
        status="healthy",
        system="Seven-Stage Command Operations System",
        roles={
            "commander": "Gemini Pro",
            "lead_dev": "Claude Pro",
            "executor": "Cursor Pro / Windsurf",
            "local_guard": "Ollama (Qwen)",
            "verify": "通義千問 / 元寶",
            "platform": "Docker"
        },
        workspace="D:/brain_workspace"
    )


@app.post("/execute", response_model=TaskResponse, summary="執行任務")
async def execute_task(request: TaskRequest, background_tasks: BackgroundTasks):
    """
    執行完整的七階段流程

    - **input**: 用戶輸入（如「幫我弄個網頁」）
    - **priority**: 任務優先級
    - **metadata**: 額外元數據
    """
    task_id = datetime.now().strftime("%Y%m%d%H%M%S")

    try:
        # 執行完整工作流
        result = await system.execute_full_workflow(request.input)

        return TaskResponse(
            task_id=task_id,
            status="completed",
            result=result,
            created_at=datetime.now().isoformat()
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"執行失敗: {str(e)}"
        )


@app.get("/status", summary="系統狀態")
async def get_status():
    """獲取當前系統狀態"""
    return {
        "system": "七階段指揮作戰系統",
        "workspace": str(system.workspace),
        "current_stage": system.current_stage.value,
        "total_tasks": len(system.tasks),
        "completed_tasks": len([t for t in system.tasks if t.status == "completed"]),
        "roles_status": {
            "commander": "ready",
            "lead_dev": "ready",
            "executor": "ready",
            "local_guard": "ready",
            "verify": "ready",
            "platform": "ready"
        }
    }


@app.get("/api-docs", summary="API 文檔")
async def api_docs():
    """獲取 API 文檔"""
    return {
        "endpoints": {
            "GET /": "API 根路徑和系統信息",
            "GET /health": "健康檢查",
            "POST /execute": "執行七階段任務",
            "GET /status": "獲取系統狀態",
            "GET /api-docs": "API 文檔"
        },
        "examples": {
            "execute_task": {
                "method": "POST",
                "url": "/execute",
                "body": {
                    "input": "幫我弄個網頁",
                    "priority": "high"
                }
            }
        }
    }


def start_server(host: str = "0.0.0.0", port: int = 8006):
    """
    啟動 HTTP 服務器

    Args:
        host: 監聽地址
        port: 監聽端口
    """
    print("=" * 60)
    print("七階段指揮作戰系統 HTTP API")
    print("=" * 60)
    print(f"啟動服務器...")
    print(f"本地訪問: http://localhost:{port}")
    print(f"文檔地址: http://localhost:{port}/docs")
    print("=" * 60)

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    # 從環境變量讀取配置
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8006"))

    start_server(host, port)
