"""
預測服務 FastAPI - Prediction Service
提供 REST API 和 WebSocket 即時預測
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import asyncio
import json
from datetime import datetime
import uvicorn

from prediction_engine import PredictionEngine
from iching_core import IChingEngine
from scientific_data_collector import ScientificDataCollector
from alert_manager import NationalAlertManager, AlertType, AlertLevel

app = FastAPI(title="易經科學預測系統", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化引擎
prediction_engine = PredictionEngine()
iching_engine = IChingEngine()
data_collector = ScientificDataCollector()
alert_manager = NationalAlertManager()

# WebSocket 連接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

# Pydantic Models
class PredictionRequest(BaseModel):
    prediction_type: str  # earthquake, weather, economy
    use_time_casting: bool = False
    market_data: Optional[Dict] = None

class ValidationRequest(BaseModel):
    prediction_id: str
    actual_event: Dict

class HexagramRequest(BaseModel):
    method: str = 'time'  # time, data, yarrow
    data_values: Optional[List[float]] = None

# API 端點
@app.get("/")
async def root():
    """首頁重定向"""
    return {"message": "易經科學預測系統 API", "version": "1.0.0"}

@app.get("/api/prediction/health")
async def health_check():
    """健康檢查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "iching_engine": "running",
            "data_collector": "running",
            "prediction_engine": "running"
        }
    }

@app.post("/api/prediction/predict")
async def create_prediction(request: PredictionRequest):
    """創建新預測"""
    try:
        if request.prediction_type == 'earthquake':
            prediction = prediction_engine.predict_earthquake(request.use_time_casting)
        elif request.prediction_type == 'weather':
            prediction = prediction_engine.predict_weather(request.use_time_casting)
        elif request.prediction_type == 'economy':
            prediction = prediction_engine.predict_economy(request.market_data)
        else:
            raise HTTPException(status_code=400, detail="無效的預測類型")
        
        # 廣播給 WebSocket 客戶端
        await manager.broadcast({
            "type": "new_prediction",
            "data": prediction.to_dict()
        })
        
        return prediction.to_dict()
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/prediction/validate")
async def validate_prediction(request: ValidationRequest):
    """驗證預測結果"""
    try:
        accuracy = prediction_engine.validate_prediction(
            request.prediction_id,
            request.actual_event
        )
        
        # 廣播驗證結果
        await manager.broadcast({
            "type": "validation_result",
            "data": {
                "prediction_id": request.prediction_id,
                "accuracy": accuracy
            }
        })
        
        return {
            "prediction_id": request.prediction_id,
            "accuracy_score": accuracy,
            "status": "verified" if accuracy > 50 else "failed"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/prediction/history")
async def get_history(
    prediction_type: Optional[str] = None,
    limit: int = 50
):
    """獲取預測歷史"""
    try:
        predictions = prediction_engine.get_prediction_history(prediction_type, limit)
        return {
            "total": len(predictions),
            "predictions": [p.to_dict() for p in predictions]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/prediction/statistics")
async def get_statistics(prediction_type: Optional[str] = None):
    """獲取統計數據"""
    try:
        stats = prediction_engine.get_accuracy_statistics(prediction_type)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/scientific/anomaly")
async def get_anomaly_data():
    """獲取科學異常指標"""
    try:
        anomaly = data_collector.calculate_anomaly_indicators()
        return anomaly
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/scientific/ionosphere")
async def get_ionosphere_data():
    """獲取電離層數據"""
    try:
        data = data_collector.collect_ionosphere_data()
        return {
            "count": len(data),
            "data": [d.to_dict() for d in data]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/scientific/geomagnetic")
async def get_geomagnetic_data():
    """獲取地磁數據"""
    try:
        data = data_collector.collect_geomagnetic_data()
        return {
            "count": len(data),
            "data": [d.to_dict() for d in data]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/scientific/earthquake")
async def get_earthquake_data(days: int = 7):
    """獲取地震數據"""
    try:
        data = data_collector.collect_earthquake_data(days)
        return {
            "count": len(data),
            "data": [d.to_dict() for d in data]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/scientific/weather")
async def get_weather_data():
    """獲取氣象數據"""
    try:
        data = data_collector.collect_weather_data()
        return {
            "count": len(data),
            "data": [d.to_dict() for d in data]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/iching/cast")
async def cast_hexagram(request: HexagramRequest):
    """起卦"""
    try:
        if request.method == 'time':
            hexagram = iching_engine.cast_hexagram_by_time()
        elif request.method == 'data' and request.data_values:
            hexagram = iching_engine.cast_hexagram_by_data(request.data_values)
        elif request.method == 'yarrow':
            hexagram = iching_engine.cast_hexagram_yarrow_stalks()
        else:
            raise HTTPException(status_code=400, detail="無效的起卦方法")
        
        # 獲取變卦
        transformed = iching_engine.get_transformed_hexagram(hexagram)
        
        return {
            "hexagram": hexagram.to_dict(),
            "transformed_hexagram": transformed.to_dict() if transformed else None
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/iching/hexagrams")
async def get_all_hexagrams():
    """獲取所有卦象資料"""
    return {
        "count": len(iching_engine.HEXAGRAMS),
        "hexagrams": iching_engine.HEXAGRAMS
    }

@app.get("/api/iching/trigrams")
async def get_all_trigrams():
    """獲取八卦資料"""
    return {
        "count": len(iching_engine.TRIGRAMS),
        "trigrams": iching_engine.TRIGRAMS
    }

@app.websocket("/ws/predictions")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 即時預測推送"""
    await manager.connect(websocket)
    try:
        while True:
            # 接收客戶端訊息
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "subscribe":
                # 訂閱特定類型預測
                await websocket.send_json({
                    "type": "subscribed",
                    "message": "已訂閱預測推送"
                })
            
            elif message.get("type") == "request_prediction":
                # 即時預測請求
                pred_type = message.get("prediction_type", "earthquake")
                
                if pred_type == "earthquake":
                    prediction = prediction_engine.predict_earthquake()
                elif pred_type == "weather":
                    prediction = prediction_engine.predict_weather()
                elif pred_type == "economy":
                    prediction = prediction_engine.predict_economy()
                
                await websocket.send_json({
                    "type": "prediction_result",
                    "data": prediction.to_dict()
                })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket 錯誤: {e}")
        manager.disconnect(websocket)

@app.get("/api/prediction/auto-monitor/status")
async def get_auto_monitor_status():
    """獲取自動監測狀態"""
    return {
        "enabled": False,
        "interval_minutes": 60,
        "last_check": None,
        "next_check": None
    }

# 背景任務：自動監測
async def auto_monitor_task():
    """自動監測任務（每小時執行一次）"""
    while True:
        try:
            # 收集科學數據
            anomaly = data_collector.calculate_anomaly_indicators()
            
            # 如果異常指標超過閾值，自動進行預測
            if anomaly['total_anomaly'] > 0.6:
                # 地震預測
                eq_prediction = prediction_engine.predict_earthquake()
                
                # 廣播高風險警報
                if eq_prediction.risk_level > 70:
                    await manager.broadcast({
                        "type": "high_risk_alert",
                        "data": {
                            "prediction_type": "earthquake",
                            "risk_level": eq_prediction.risk_level,
                            "prediction": eq_prediction.to_dict()
                        }
                    })
            
            # 每小時執行一次
            await asyncio.sleep(3600)
        
        except Exception as e:
            print(f"自動監測錯誤: {e}")
            await asyncio.sleep(3600)

@app.on_event("startup")
async def startup_event():
    """啟動事件"""
    # 啟動背景監測任務
    asyncio.create_task(auto_monitor_task())
    print("易經科學預測系統已啟動")
    print("API 文檔: http://localhost:8025/docs")

if __name__ == "__main__":
    uvicorn.run(
        "prediction_service:app",
        host="0.0.0.0",
        port=8025,
        reload=True,
        log_level="info"
    )
