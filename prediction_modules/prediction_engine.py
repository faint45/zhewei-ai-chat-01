"""
預測引擎 - Prediction Engine
整合易經與科學數據進行地震、氣象、經濟預測
包含驗證修正機制
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import sqlite3

from iching_core import IChingEngine, Hexagram
from scientific_data_collector import ScientificDataCollector

@dataclass
class Prediction:
    """預測記錄"""
    id: str
    timestamp: str
    prediction_type: str  # earthquake, weather, economy
    hexagram_number: int
    hexagram_name: str
    risk_level: float
    prediction_details: Dict
    scientific_data: Dict
    forecast_period: str
    status: str = 'pending'  # pending, verified, failed
    actual_event: Optional[Dict] = None
    accuracy_score: Optional[float] = None
    
    def to_dict(self):
        return asdict(self)

class PredictionEngine:
    """預測引擎主類"""
    
    def __init__(self, db_path: str = "prediction_modules/predictions.db"):
        self.iching = IChingEngine()
        self.collector = ScientificDataCollector()
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """初始化資料庫"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 預測記錄表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                prediction_type TEXT NOT NULL,
                hexagram_number INTEGER,
                hexagram_name TEXT,
                risk_level REAL,
                prediction_details TEXT,
                scientific_data TEXT,
                forecast_period TEXT,
                status TEXT DEFAULT 'pending',
                actual_event TEXT,
                accuracy_score REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 驗證記錄表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS validations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_id TEXT NOT NULL,
                validation_time TEXT NOT NULL,
                actual_data TEXT,
                accuracy_score REAL,
                notes TEXT,
                FOREIGN KEY (prediction_id) REFERENCES predictions(id)
            )
        ''')
        
        # 修正參數表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS correction_params (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_type TEXT NOT NULL,
                hexagram_number INTEGER,
                correction_factor REAL DEFAULT 1.0,
                weight_adjustment REAL DEFAULT 0.0,
                update_count INTEGER DEFAULT 0,
                last_updated TEXT,
                notes TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def predict_earthquake(self, use_time_casting: bool = False) -> Prediction:
        """
        地震預測
        use_time_casting: 是否使用時間起卦（False則使用科學數據起卦）
        """
        # 收集科學數據
        anomaly_data = self.collector.calculate_anomaly_indicators()
        
        # 起卦
        if use_time_casting:
            hexagram = self.iching.cast_hexagram_by_time()
        else:
            # 使用電離層和地磁數據起卦
            iono_data = self.collector.get_time_series_data('ionosphere', hours=24)
            geo_data = self.collector.get_time_series_data('geomagnetic', hours=24)
            combined_data = iono_data + geo_data
            hexagram = self.iching.cast_hexagram_by_data(combined_data)
        
        # 解讀預測
        interpretation = self.iching.interpret_for_earthquake(hexagram, anomaly_data)
        
        # 應用修正參數
        corrected_risk = self._apply_correction(
            'earthquake', 
            hexagram.number, 
            interpretation['risk_level']
        )
        
        # 創建預測記錄
        prediction_id = f"EQ_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        prediction = Prediction(
            id=prediction_id,
            timestamp=datetime.now().isoformat(),
            prediction_type='earthquake',
            hexagram_number=hexagram.number,
            hexagram_name=hexagram.name_zh,
            risk_level=corrected_risk,
            prediction_details={
                'original_risk': interpretation['risk_level'],
                'corrected_risk': corrected_risk,
                'risk_category': interpretation['risk_category'],
                'indicators': interpretation['indicators'],
                'recommendation': interpretation['recommendation'],
                'hexagram_interpretation': interpretation['hexagram_interpretation'],
                'changing_lines': hexagram.changing_lines,
                'trigrams': f"{hexagram.trigram_upper}上{hexagram.trigram_lower}下"
            },
            scientific_data=anomaly_data,
            forecast_period='未來3-7天'
        )
        
        # 保存到資料庫
        self._save_prediction(prediction)
        
        return prediction
    
    def predict_weather(self, use_time_casting: bool = False) -> Prediction:
        """氣象預測"""
        # 收集氣象數據
        weather_data = self.collector.collect_weather_data()
        anomaly_data = self.collector.calculate_anomaly_indicators()
        
        # 起卦
        if use_time_casting:
            hexagram = self.iching.cast_hexagram_by_time()
        else:
            # 使用氣象數據起卦
            pressure_series = [w.pressure for w in weather_data]
            humidity_series = [w.humidity for w in weather_data]
            combined_data = pressure_series + humidity_series
            hexagram = self.iching.cast_hexagram_by_data(combined_data)
        
        # 解讀預測
        scientific_data = {
            'atmospheric_pressure': anomaly_data.get('atmospheric_pressure', 1013),
            'humidity': weather_data[0].humidity if weather_data else 50,
            'pressure_anomaly': anomaly_data.get('pressure_anomaly', 0)
        }
        interpretation = self.iching.interpret_for_weather(hexagram, scientific_data)
        
        # 應用修正
        corrected_severity = self._apply_correction(
            'weather',
            hexagram.number,
            interpretation['severity']
        )
        
        # 創建預測記錄
        prediction_id = f"WX_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        prediction = Prediction(
            id=prediction_id,
            timestamp=datetime.now().isoformat(),
            prediction_type='weather',
            hexagram_number=hexagram.number,
            hexagram_name=hexagram.name_zh,
            risk_level=corrected_severity,
            prediction_details={
                'weather_type': interpretation['weather_type'],
                'original_severity': interpretation['severity'],
                'corrected_severity': corrected_severity,
                'indicators': interpretation['indicators'],
                'hexagram_interpretation': interpretation['hexagram_interpretation'],
                'trigrams': f"{hexagram.trigram_upper}上{hexagram.trigram_lower}下"
            },
            scientific_data=scientific_data,
            forecast_period=interpretation['forecast_period']
        )
        
        self._save_prediction(prediction)
        return prediction
    
    def predict_economy(self, market_data: Optional[Dict] = None) -> Prediction:
        """經濟預測"""
        # 使用時間起卦（經濟預測較依賴時間週期）
        hexagram = self.iching.cast_hexagram_by_time()
        
        # 如果沒有提供市場數據，使用模擬數據
        if market_data is None:
            market_data = {
                'volatility': 0.15,
                'trend': 'neutral'
            }
        
        # 解讀預測
        interpretation = self.iching.interpret_for_economy(hexagram, market_data)
        
        # 應用修正
        corrected_confidence = self._apply_correction(
            'economy',
            hexagram.number,
            interpretation['confidence']
        )
        
        # 創建預測記錄
        prediction_id = f"EC_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        prediction = Prediction(
            id=prediction_id,
            timestamp=datetime.now().isoformat(),
            prediction_type='economy',
            hexagram_number=hexagram.number,
            hexagram_name=hexagram.name_zh,
            risk_level=corrected_confidence,
            prediction_details={
                'trend': interpretation['trend'],
                'original_confidence': interpretation['confidence'],
                'corrected_confidence': corrected_confidence,
                'indicators': interpretation['indicators'],
                'hexagram_interpretation': interpretation['hexagram_interpretation'],
                'trigrams': f"{hexagram.trigram_upper}上{hexagram.trigram_lower}下"
            },
            scientific_data=market_data,
            forecast_period=interpretation['forecast_period']
        )
        
        self._save_prediction(prediction)
        return prediction
    
    def validate_prediction(self, prediction_id: str, actual_event: Dict) -> float:
        """
        驗證預測準確度
        actual_event: 實際發生的事件數據
        返回準確度分數 0-100
        """
        prediction = self._load_prediction(prediction_id)
        if not prediction:
            return 0.0
        
        accuracy_score = 0.0
        
        if prediction.prediction_type == 'earthquake':
            accuracy_score = self._validate_earthquake(prediction, actual_event)
        elif prediction.prediction_type == 'weather':
            accuracy_score = self._validate_weather(prediction, actual_event)
        elif prediction.prediction_type == 'economy':
            accuracy_score = self._validate_economy(prediction, actual_event)
        
        # 更新預測記錄
        prediction.status = 'verified' if accuracy_score > 50 else 'failed'
        prediction.actual_event = actual_event
        prediction.accuracy_score = accuracy_score
        
        self._update_prediction(prediction)
        
        # 記錄驗證
        self._save_validation(prediction_id, actual_event, accuracy_score)
        
        # 更新修正參數
        self._update_correction_params(prediction, accuracy_score)
        
        return accuracy_score
    
    def _validate_earthquake(self, prediction: Prediction, actual_event: Dict) -> float:
        """驗證地震預測"""
        score = 0.0
        
        # 檢查是否在預測期間內發生地震
        occurred = actual_event.get('occurred', False)
        magnitude = actual_event.get('magnitude', 0)
        
        if occurred:
            # 預測有地震且確實發生
            if prediction.risk_level >= 60:
                score += 40
                
                # 規模匹配度
                predicted_mag = prediction.risk_level / 20  # 簡化轉換
                mag_diff = abs(predicted_mag - magnitude)
                if mag_diff < 1.0:
                    score += 30
                elif mag_diff < 2.0:
                    score += 20
                else:
                    score += 10
                
                # 時間準確度
                days_diff = actual_event.get('days_from_prediction', 0)
                if days_diff <= 3:
                    score += 30
                elif days_diff <= 7:
                    score += 20
                else:
                    score += 10
        else:
            # 沒有發生地震
            if prediction.risk_level < 40:
                score += 80  # 正確預測無地震
            else:
                score += 20  # 誤報
        
        return min(score, 100)
    
    def _validate_weather(self, prediction: Prediction, actual_event: Dict) -> float:
        """驗證氣象預測"""
        score = 0.0
        
        predicted_type = prediction.prediction_details.get('weather_type', '正常')
        actual_type = actual_event.get('weather_type', '正常')
        
        # 天氣類型匹配
        if predicted_type == actual_type:
            score += 50
        elif predicted_type in actual_type or actual_type in predicted_type:
            score += 30
        
        # 嚴重程度匹配
        predicted_severity = prediction.risk_level
        actual_severity = actual_event.get('severity', 0)
        severity_diff = abs(predicted_severity - actual_severity)
        
        if severity_diff < 10:
            score += 50
        elif severity_diff < 20:
            score += 30
        elif severity_diff < 30:
            score += 20
        else:
            score += 10
        
        return min(score, 100)
    
    def _validate_economy(self, prediction: Prediction, actual_event: Dict) -> float:
        """驗證經濟預測"""
        score = 0.0
        
        predicted_trend = prediction.prediction_details.get('trend', '持平')
        actual_trend = actual_event.get('trend', '持平')
        
        # 趨勢匹配
        if predicted_trend == actual_trend:
            score += 70
        elif (predicted_trend in ['上升', '下降'] and actual_trend == '震盪') or \
             (predicted_trend == '震盪' and actual_trend in ['上升', '下降']):
            score += 40
        else:
            score += 10
        
        # 信心度與實際波動匹配
        predicted_confidence = prediction.risk_level
        actual_volatility = actual_event.get('volatility', 0.5)
        
        if (predicted_confidence > 70 and actual_volatility < 0.3) or \
           (predicted_confidence < 50 and actual_volatility > 0.3):
            score += 30
        else:
            score += 15
        
        return min(score, 100)
    
    def _apply_correction(self, prediction_type: str, hexagram_number: int, original_value: float) -> float:
        """應用修正參數"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT correction_factor, weight_adjustment 
            FROM correction_params 
            WHERE prediction_type = ? AND hexagram_number = ?
        ''', (prediction_type, hexagram_number))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            factor, adjustment = result
            corrected = original_value * factor + adjustment
            return max(0, min(corrected, 100))
        
        return original_value
    
    def _update_correction_params(self, prediction: Prediction, accuracy_score: float):
        """根據驗證結果更新修正參數"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 檢查是否已有記錄
        cursor.execute('''
            SELECT id, correction_factor, weight_adjustment, update_count
            FROM correction_params
            WHERE prediction_type = ? AND hexagram_number = ?
        ''', (prediction.prediction_type, prediction.hexagram_number))
        
        result = cursor.fetchone()
        
        # 計算新的修正參數
        learning_rate = 0.1  # 學習率
        
        if accuracy_score < 50:
            # 預測不準，需要調整
            error_ratio = (50 - accuracy_score) / 50
            new_factor = 1.0 - (error_ratio * learning_rate)
            new_adjustment = -5 * error_ratio
        else:
            # 預測準確，微調
            success_ratio = (accuracy_score - 50) / 50
            new_factor = 1.0 + (success_ratio * learning_rate * 0.5)
            new_adjustment = 2 * success_ratio
        
        if result:
            # 更新現有記錄
            old_id, old_factor, old_adjustment, update_count = result
            
            # 加權平均
            updated_factor = old_factor * 0.7 + new_factor * 0.3
            updated_adjustment = old_adjustment * 0.7 + new_adjustment * 0.3
            
            cursor.execute('''
                UPDATE correction_params
                SET correction_factor = ?, weight_adjustment = ?, 
                    update_count = ?, last_updated = ?
                WHERE id = ?
            ''', (updated_factor, updated_adjustment, update_count + 1, 
                  datetime.now().isoformat(), old_id))
        else:
            # 創建新記錄
            cursor.execute('''
                INSERT INTO correction_params 
                (prediction_type, hexagram_number, correction_factor, weight_adjustment, update_count, last_updated)
                VALUES (?, ?, ?, ?, 1, ?)
            ''', (prediction.prediction_type, prediction.hexagram_number, 
                  new_factor, new_adjustment, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def _save_prediction(self, prediction: Prediction):
        """保存預測到資料庫"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO predictions 
            (id, timestamp, prediction_type, hexagram_number, hexagram_name, 
             risk_level, prediction_details, scientific_data, forecast_period, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            prediction.id, prediction.timestamp, prediction.prediction_type,
            prediction.hexagram_number, prediction.hexagram_name, prediction.risk_level,
            json.dumps(prediction.prediction_details, ensure_ascii=False),
            json.dumps(prediction.scientific_data, ensure_ascii=False),
            prediction.forecast_period, prediction.status
        ))
        
        conn.commit()
        conn.close()
    
    def _load_prediction(self, prediction_id: str) -> Optional[Prediction]:
        """從資料庫載入預測"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM predictions WHERE id = ?', (prediction_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return Prediction(
                id=result[0],
                timestamp=result[1],
                prediction_type=result[2],
                hexagram_number=result[3],
                hexagram_name=result[4],
                risk_level=result[5],
                prediction_details=json.loads(result[6]),
                scientific_data=json.loads(result[7]),
                forecast_period=result[8],
                status=result[9],
                actual_event=json.loads(result[10]) if result[10] else None,
                accuracy_score=result[11]
            )
        return None
    
    def _update_prediction(self, prediction: Prediction):
        """更新預測記錄"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE predictions
            SET status = ?, actual_event = ?, accuracy_score = ?
            WHERE id = ?
        ''', (
            prediction.status,
            json.dumps(prediction.actual_event, ensure_ascii=False) if prediction.actual_event else None,
            prediction.accuracy_score,
            prediction.id
        ))
        
        conn.commit()
        conn.close()
    
    def _save_validation(self, prediction_id: str, actual_data: Dict, accuracy_score: float):
        """保存驗證記錄"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO validations (prediction_id, validation_time, actual_data, accuracy_score)
            VALUES (?, ?, ?, ?)
        ''', (
            prediction_id,
            datetime.now().isoformat(),
            json.dumps(actual_data, ensure_ascii=False),
            accuracy_score
        ))
        
        conn.commit()
        conn.close()
    
    def get_prediction_history(self, prediction_type: Optional[str] = None, limit: int = 50) -> List[Prediction]:
        """獲取預測歷史"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if prediction_type:
            cursor.execute('''
                SELECT * FROM predictions 
                WHERE prediction_type = ?
                ORDER BY timestamp DESC LIMIT ?
            ''', (prediction_type, limit))
        else:
            cursor.execute('''
                SELECT * FROM predictions 
                ORDER BY timestamp DESC LIMIT ?
            ''', (limit,))
        
        results = cursor.fetchall()
        conn.close()
        
        predictions = []
        for result in results:
            predictions.append(Prediction(
                id=result[0],
                timestamp=result[1],
                prediction_type=result[2],
                hexagram_number=result[3],
                hexagram_name=result[4],
                risk_level=result[5],
                prediction_details=json.loads(result[6]),
                scientific_data=json.loads(result[7]),
                forecast_period=result[8],
                status=result[9],
                actual_event=json.loads(result[10]) if result[10] else None,
                accuracy_score=result[11]
            ))
        
        return predictions
    
    def get_accuracy_statistics(self, prediction_type: Optional[str] = None) -> Dict:
        """獲取準確度統計"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if prediction_type:
            cursor.execute('''
                SELECT COUNT(*), AVG(accuracy_score), 
                       SUM(CASE WHEN status = 'verified' THEN 1 ELSE 0 END)
                FROM predictions
                WHERE prediction_type = ? AND accuracy_score IS NOT NULL
            ''', (prediction_type,))
        else:
            cursor.execute('''
                SELECT COUNT(*), AVG(accuracy_score),
                       SUM(CASE WHEN status = 'verified' THEN 1 ELSE 0 END)
                FROM predictions
                WHERE accuracy_score IS NOT NULL
            ''')
        
        result = cursor.fetchone()
        conn.close()
        
        total_count = result[0] or 0
        avg_accuracy = result[1] or 0
        verified_count = result[2] or 0
        
        return {
            'total_predictions': total_count,
            'verified_predictions': verified_count,
            'average_accuracy': round(avg_accuracy, 2),
            'success_rate': round((verified_count / total_count * 100) if total_count > 0 else 0, 2)
        }


    # ===== 水情預測（增量擴充，不動現有方法）=====

    def predict_flood(self, water_level_m: float = 0, humidity: float = 0,
                      rainfall_forecast_mm: float = 0, cloud_cover_pct: float = 0,
                      station_id: str = "WA-001") -> Prediction:
        """
        水情預測 — 整合 water_alert.flood_decision_engine 五源加權

        Args:
            water_level_m: 當前雷達水位 (m)
            humidity: 當前濕度 (%RH)
            rainfall_forecast_mm: 6hr 預報雨量 (mm)
            cloud_cover_pct: 雲量佔比 (%)
            station_id: 觀測站代號

        Returns:
            Prediction 記錄（prediction_type='flood'）
        """
        # 嘗試使用 flood_decision_engine
        flood_result = {}
        risk_level = 0.0
        try:
            from water_alert.config import DEFAULT_STATIONS, DEFAULT_SYSTEM
            from water_alert.flood_decision_engine import FloodDecisionEngine

            station = next((s for s in DEFAULT_STATIONS if s.station_id == station_id), DEFAULT_STATIONS[0])
            engine = FloodDecisionEngine(station, DEFAULT_SYSTEM)

            inputs = []
            if water_level_m > 0:
                inputs.append(engine.normalize_radar(water_level_m))
            if humidity > 0:
                inputs.append(engine.normalize_dht(25, humidity))
            if rainfall_forecast_mm > 0:
                inputs.append(engine.normalize_forecast(rainfall_forecast_mm))
            if cloud_cover_pct > 0:
                inputs.append(engine.normalize_cloud(cloud_cover_pct))

            if inputs:
                decision = engine.decide(inputs)
                risk_level = decision.weighted_score
                flood_result = decision.to_dict()
        except ImportError:
            # water_alert 模組不可用，用簡易計算
            risk_level = min(100, water_level_m * 20 + humidity * 0.3 + rainfall_forecast_mm * 0.5)
            flood_result = {"fallback": True, "water_level_m": water_level_m}

        # 應用修正
        corrected_risk = self._apply_correction('flood', 0, risk_level)

        prediction_id = f"FL_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        prediction = Prediction(
            id=prediction_id,
            timestamp=datetime.now().isoformat(),
            prediction_type='flood',
            hexagram_number=0,
            hexagram_name='',
            risk_level=corrected_risk,
            prediction_details={
                'original_risk': risk_level,
                'corrected_risk': corrected_risk,
                'station_id': station_id,
                'flood_decision': flood_result,
            },
            scientific_data={
                'water_level_m': water_level_m,
                'humidity': humidity,
                'rainfall_forecast_mm': rainfall_forecast_mm,
                'cloud_cover_pct': cloud_cover_pct,
            },
            forecast_period='未來1-6小時',
        )

        self._save_prediction(prediction)
        return prediction


if __name__ == '__main__':
    # 測試
    engine = PredictionEngine()
    
    print("=== 地震預測 ===")
    eq_prediction = engine.predict_earthquake(use_time_casting=False)
    print(f"預測ID: {eq_prediction.id}")
    print(f"卦象: {eq_prediction.hexagram_name} (第{eq_prediction.hexagram_number}卦)")
    print(f"風險等級: {eq_prediction.risk_level}%")
    print(f"預測詳情: {json.dumps(eq_prediction.prediction_details, ensure_ascii=False, indent=2)}")
    
    print("\n=== 氣象預測 ===")
    wx_prediction = engine.predict_weather()
    print(f"預測ID: {wx_prediction.id}")
    print(f"卦象: {wx_prediction.hexagram_name}")
    print(f"天氣類型: {wx_prediction.prediction_details['weather_type']}")
    
    print("\n=== 準確度統計 ===")
    stats = engine.get_accuracy_statistics()
    print(json.dumps(stats, ensure_ascii=False, indent=2))
