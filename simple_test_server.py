#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
簡單測試服務器 - 驗證FastAPI是否能正常運行
"""

from fastapi import FastAPI
import uvicorn

app = FastAPI(title="築未科技測試服務器")

@app.get("/")
async def root():
    return {"message": "築未科技測試服務器運行正常", "status": "success"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": "2026-02-03 15:00:00"}

if __name__ == "__main__":
    print("啟動簡單測試服務器...")
    print("訪問地址: http://localhost:8003")
    print("健康檢查: http://localhost:8003/health")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8003,
        log_level="info"
    )