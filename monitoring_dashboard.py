#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
築未科技 - API 監控面板
提供可視化的 API 監控界面
"""

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime, timedelta
from typing import Optional
import asyncio
import logging

from monitoring_service import APIMonitor

logger = logging.getLogger(__name__)

app = FastAPI(title="築未科技 API 監控面板", version="1.0.0")

# 掛載靜態文件和模板
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 監控器實例
monitor = APIMonitor()


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """監控儀表板主頁"""
    return templates.TemplateResponse("monitoring_dashboard.html", {
        "request": request,
        "title": "築未科技 - API 監控面板"
    })


@app.get("/api/metrics")
async def get_metrics(
    period: str = "today",  # today, week, month
    source: Optional[str] = None
):
    """獲取 API 指標"""
    try:
        now = datetime.now()
        
        if period == "today":
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = now
        elif period == "week":
            start_time = now - timedelta(days=7)
            end_time = now
        elif period == "month":
            start_time = now - timedelta(days=30)
            end_time = now
        else:
            raise HTTPException(status_code=400, detail=f"不支持的時間範圍: {period}")
        
        metrics = monitor.get_metrics(start_time, end_time, source)
        
        return JSONResponse({
            "period": period,
            "source": source,
            "metrics": {
                "total_requests": metrics.total_requests,
                "successful_requests": metrics.successful_requests,
                "failed_requests": metrics.failed_requests,
                "total_execution_time": round(metrics.total_execution_time, 2),
                "total_tokens": metrics.total_tokens,
                "total_cost": round(metrics.total_cost, 4),
                "avg_execution_time": round(metrics.avg_execution_time, 3),
                "success_rate": round(metrics.success_rate * 100, 1)
            }
        })
    except Exception as e:
        logger.error(f"獲取指標失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/requests")
async def get_requests(limit: int = 50):
    """獲取最近的請求"""
    try:
        requests = monitor.get_recent_requests(limit)
        return JSONResponse({"requests": requests})
    except Exception as e:
        logger.error(f"獲取請求失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/hourly-stats")
async def get_hourly_stats(hours: int = 24):
    """獲取小時統計"""
    try:
        stats = monitor.get_hourly_stats(hours)
        return JSONResponse({"stats": stats})
    except Exception as e:
        logger.error(f"獲取小時統計失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/daily-stats")
async def get_daily_stats(days: int = 7):
    """獲取每日統計"""
    try:
        stats = monitor.get_daily_stats(days)
        return JSONResponse({"stats": stats})
    except Exception as e:
        logger.error(f"獲取每日統計失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/alerts")
async def get_alerts(limit: int = 20):
    """獲取告警記錄"""
    try:
        alerts = monitor.get_alerts(limit)
        return JSONResponse({"alerts": alerts})
    except Exception as e:
        logger.error(f"獲取告警失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/report/{report_type}")
async def generate_report(report_type: str = "daily"):
    """生成報告"""
    try:
        report = monitor.generate_report(report_type)
        return JSONResponse(report)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"生成報告失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/log-request")
async def log_request(request_data: dict):
    """記錄 API 請求（供其他服務調用）"""
    try:
        await monitor.log_request(
            request_id=request_data.get("request_id"),
            source=request_data.get("source"),
            user_id=request_data.get("user_id"),
            command=request_data.get("command"),
            status=request_data.get("status"),
            execution_time=request_data.get("execution_time", 0.0),
            tokens_used=request_data.get("tokens_used", 0),
            cost=request_data.get("cost", 0.0)
        )
        return JSONResponse({"status": "success"})
    except Exception as e:
        logger.error(f"記錄請求失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """健康檢查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "API Monitoring Service"
    }


if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("築未科技 - API 監控面板")
    print("=" * 60)
    print()
    print("監控面板: http://localhost:8001")
    print("API 文檔: http://localhost:8001/docs")
    print()
    uvicorn.run(app, host="0.0.0.0", port=8001)
