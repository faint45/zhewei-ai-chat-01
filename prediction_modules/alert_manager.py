"""
國家級警報推播管理系統 - National Alert Push Notification Manager
整合 Ntfy 推播服務，提供多級別、多類型的即時警報
"""
import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
import base64

class AlertLevel(Enum):
    """警報等級"""
    INFO = 1          # 資訊 - 藍色
    WARNING = 2       # 注意 - 黃色
    ALERT = 3         # 警報 - 橙色
    CRITICAL = 4      # 緊急 - 紅色
    EMERGENCY = 5     # 國家級緊急 - 深紅色

class AlertType(Enum):
    """警報類型"""
    EARTHQUAKE = "earthquake"           # 地震
    TSUNAMI = "tsunami"                 # 海嘯
    TYPHOON = "typhoon"                 # 颱風
    FLOOD = "flood"                     # 水災
    LANDSLIDE = "landslide"             # 土石流
    FIRE = "fire"                       # 火災
    WEATHER_SEVERE = "weather_severe"   # 劇烈天氣
    AIR_QUALITY = "air_quality"         # 空氣品質
    EPIDEMIC = "epidemic"               # 疫情
    ECONOMIC = "economic"               # 經濟
    SYSTEM = "system"                   # 系統

@dataclass
class Alert:
    """警報數據結構"""
    id: str
    timestamp: str
    alert_type: str
    alert_level: int
    title: str
    message: str
    area: str
    prediction_id: Optional[str] = None
    expires_at: Optional[str] = None
    sent_count: int = 0
    delivery_status: str = "pending"  # pending, sent, failed
    ntfy_response: Optional[Dict] = None
    
    def to_dict(self):
        return asdict(self)

class NationalAlertManager:
    """國家級警報管理器"""
    
    def __init__(self, db_path: str = "prediction_modules/alerts.db"):
        self.db_path = db_path
        self._init_database()
        
        # Ntfy 配置
        self.ntfy_server = os.getenv('NTFY_SERVER', 'https://ntfy.sh')
        self.ntfy_admin_user = os.getenv('NTFY_ADMIN_USER', '')
        self.ntfy_admin_pass = os.getenv('NTFY_ADMIN_PASS', '')
        
        # 警報主題配置
        self.topics = {
            AlertType.EARTHQUAKE: 'taiwan_earthquake_alert',
            AlertType.TSUNAMI: 'taiwan_tsunami_alert',
            AlertType.TYPHOON: 'taiwan_typhoon_alert',
            AlertType.FLOOD: 'taiwan_flood_alert',
            AlertType.LANDSLIDE: 'taiwan_landslide_alert',
            AlertType.FIRE: 'taiwan_fire_alert',
            AlertType.WEATHER_SEVERE: 'taiwan_weather_alert',
            AlertType.AIR_QUALITY: 'taiwan_air_alert',
            AlertType.EPIDEMIC: 'taiwan_epidemic_alert',
            AlertType.ECONOMIC: 'taiwan_economic_alert',
            AlertType.SYSTEM: 'taiwan_system_alert'
        }
        
        # 警報等級配置
        self.level_config = {
            AlertLevel.INFO: {
                'icon': 'ℹ️',
                'color': '#3B82F6',
                'priority': 1,
                'sound': 'default',
                'vibrate': False
            },
            AlertLevel.WARNING: {
                'icon': '⚠️',
                'color': '#F59E0B',
                'priority': 3,
                'sound': 'warning',
                'vibrate': True
            },
            AlertLevel.ALERT: {
                'icon': '🚨',
                'color': '#F97316',
                'priority': 4,
                'sound': 'alarm',
                'vibrate': True
            },
            AlertLevel.CRITICAL: {
                'icon': '🔴',
                'color': '#EF4444',
                'priority': 5,
                'sound': 'emergency',
                'vibrate': True
            },
            AlertLevel.EMERGENCY: {
                'icon': '🆘',
                'color': '#991B1B',
                'priority': 5,
                'sound': 'emergency',
                'vibrate': True
            }
        }
        
        # 警報類型配置
        self.type_config = {
            AlertType.EARTHQUAKE: {'name': '地震警報', 'icon': '🌍'},
            AlertType.TSUNAMI: {'name': '海嘯警報', 'icon': '🌊'},
            AlertType.TYPHOON: {'name': '颱風警報', 'icon': '🌀'},
            AlertType.FLOOD: {'name': '水災警報', 'icon': '💧'},
            AlertType.LANDSLIDE: {'name': '土石流警報', 'icon': '⛰️'},
            AlertType.FIRE: {'name': '火災警報', 'icon': '🔥'},
            AlertType.WEATHER_SEVERE: {'name': '劇烈天氣警報', 'icon': '⛈️'},
            AlertType.AIR_QUALITY: {'name': '空氣品質警報', 'icon': '💨'},
            AlertType.EPIDEMIC: {'name': '疫情警報', 'icon': '🦠'},
            AlertType.ECONOMIC: {'name': '經濟警報', 'icon': '📉'},
            AlertType.SYSTEM: {'name': '系統通知', 'icon': '🔔'}
        }
    
    def _init_database(self):
        """初始化資料庫"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 警報記錄表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                alert_level INTEGER NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                area TEXT,
                prediction_id TEXT,
                expires_at TEXT,
                sent_count INTEGER DEFAULT 0,
                delivery_status TEXT DEFAULT 'pending',
                ntfy_response TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 訂閱者表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscribers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT UNIQUE,
                device_name TEXT,
                platform TEXT,
                subscribed_topics TEXT,
                subscribed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_active TEXT,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # 發送記錄表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS delivery_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT NOT NULL,
                topic TEXT NOT NULL,
                sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
                status TEXT,
                response_code INTEGER,
                error_message TEXT,
                FOREIGN KEY (alert_id) REFERENCES alerts(id)
            )
        ''')
        
        # 統計表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alert_statistics (
                date TEXT PRIMARY KEY,
                total_alerts INTEGER DEFAULT 0,
                by_type TEXT,
                by_level TEXT,
                delivery_success_rate REAL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def send_alert(
        self,
        alert_type: AlertType,
        alert_level: AlertLevel,
        title: str,
        message: str,
        area: str = "全台灣",
        prediction_id: Optional[str] = None,
        expires_in_hours: int = 24,
        custom_data: Optional[Dict] = None
    ) -> Alert:
        """
        發送國家級警報
        
        Args:
            alert_type: 警報類型
            alert_level: 警報等級
            title: 警報標題
            message: 警報內容
            area: 影響區域
            prediction_id: 關聯的預測ID
            expires_in_hours: 過期時間（小時）
            custom_data: 自訂數據
        
        Returns:
            Alert: 警報對象
        """
        # 創建警報
        alert_id = f"ALERT_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        expires_at = (datetime.now() + timedelta(hours=expires_in_hours)).isoformat()
        
        alert = Alert(
            id=alert_id,
            timestamp=datetime.now().isoformat(),
            alert_type=alert_type.value,
            alert_level=alert_level.value,
            title=title,
            message=message,
            area=area,
            prediction_id=prediction_id,
            expires_at=expires_at
        )
        
        # 發送到 Ntfy
        topic = self.topics.get(alert_type, 'taiwan_general_alert')
        success, response = self._send_to_ntfy(alert, topic, custom_data)
        
        # 更新警報狀態
        alert.sent_count = 1
        alert.delivery_status = "sent" if success else "failed"
        alert.ntfy_response = response
        
        # 保存到資料庫
        self._save_alert(alert)
        
        # 記錄發送日誌
        self._log_delivery(alert_id, topic, success, response)
        
        return alert
    
    def _send_to_ntfy(
        self,
        alert: Alert,
        topic: str,
        custom_data: Optional[Dict] = None
    ) -> Tuple[bool, Dict]:
        """發送到 Ntfy 服務器"""
        try:
            level_config = self.level_config[AlertLevel(alert.alert_level)]
            type_config = self.type_config[AlertType(alert.alert_type)]
            
            # 構建 Ntfy 消息
            headers = {
                'Title': f"{level_config['icon']} {type_config['icon']} {alert.title}",
                'Priority': str(level_config['priority']),
                'Tags': f"{alert.alert_type},{AlertLevel(alert.alert_level).name.lower()}",
            }
            
            # 添加認證
            if self.ntfy_admin_user and self.ntfy_admin_pass:
                auth_string = f"{self.ntfy_admin_user}:{self.ntfy_admin_pass}"
                auth_bytes = auth_string.encode('utf-8')
                auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')
                headers['Authorization'] = f'Basic {auth_b64}'
            
            # 添加動作按鈕
            actions = [
                {
                    'action': 'view',
                    'label': '查看詳情',
                    'url': f'https://predict.zhe-wei.net/alert/{alert.id}'
                }
            ]
            
            if alert.alert_level >= AlertLevel.ALERT.value:
                actions.append({
                    'action': 'broadcast',
                    'label': '我安全',
                    'intent': 'io.heckel.ntfy.USER_ACTION'
                })
            
            headers['Actions'] = json.dumps(actions)
            
            # 添加附加數據
            attach_data = {
                'alert_id': alert.id,
                'alert_type': alert.alert_type,
                'alert_level': alert.alert_level,
                'area': alert.area,
                'timestamp': alert.timestamp,
                'expires_at': alert.expires_at
            }
            
            if custom_data:
                attach_data.update(custom_data)
            
            # 構建完整消息
            full_message = f"{alert.message}\n\n"
            full_message += f"📍 影響區域: {alert.area}\n"
            full_message += f"⏰ 發布時間: {datetime.fromisoformat(alert.timestamp).strftime('%Y-%m-%d %H:%M:%S')}\n"
            
            if alert.prediction_id:
                full_message += f"🔮 預測編號: {alert.prediction_id}\n"
            
            # 發送請求
            url = f"{self.ntfy_server}/{topic}"
            response = requests.post(
                url,
                data=full_message.encode('utf-8'),
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return True, {
                    'status': 'success',
                    'code': response.status_code,
                    'topic': topic,
                    'message_id': response.json().get('id', '')
                }
            else:
                return False, {
                    'status': 'failed',
                    'code': response.status_code,
                    'error': response.text
                }
        
        except Exception as e:
            return False, {
                'status': 'error',
                'error': str(e)
            }
    
    def send_earthquake_alert(
        self,
        magnitude: float,
        depth: float,
        location: str,
        risk_level: float,
        prediction_id: Optional[str] = None
    ) -> Alert:
        """發送地震警報"""
        # 根據規模和風險決定警報等級
        if magnitude >= 6.0 or risk_level >= 80:
            level = AlertLevel.EMERGENCY
            title = "🆘 國家級地震緊急警報"
        elif magnitude >= 5.0 or risk_level >= 60:
            level = AlertLevel.CRITICAL
            title = "🔴 地震警報 - 請立即避難"
        elif magnitude >= 4.0 or risk_level >= 40:
            level = AlertLevel.ALERT
            title = "🚨 地震警報 - 請注意安全"
        else:
            level = AlertLevel.WARNING
            title = "⚠️ 地震預警 - 請保持警覺"
        
        message = f"預測地震規模: M{magnitude:.1f}\n"
        message += f"震源深度: {depth:.1f} 公里\n"
        message += f"震央位置: {location}\n"
        message += f"風險評估: {risk_level:.1f}%\n\n"
        
        if level == AlertLevel.EMERGENCY:
            message += "⚠️ 請立即採取避難措施！\n"
            message += "• 遠離窗戶和重物\n"
            message += "• 躲在堅固桌下\n"
            message += "• 保護頭部和頸部"
        elif level == AlertLevel.CRITICAL:
            message += "請做好防震準備：\n"
            message += "• 檢查緊急避難包\n"
            message += "• 確認逃生路線\n"
            message += "• 關注後續通報"
        
        return self.send_alert(
            alert_type=AlertType.EARTHQUAKE,
            alert_level=level,
            title=title,
            message=message,
            area=location,
            prediction_id=prediction_id,
            custom_data={
                'magnitude': magnitude,
                'depth': depth,
                'risk_level': risk_level
            }
        )
    
    def send_weather_alert(
        self,
        weather_type: str,
        severity: float,
        forecast_period: str,
        prediction_id: Optional[str] = None
    ) -> Alert:
        """發送氣象警報"""
        # 根據天氣類型和嚴重程度決定警報類型和等級
        if weather_type == "強風" or weather_type == "颱風":
            alert_type = AlertType.TYPHOON
            type_icon = "🌀"
        elif weather_type == "降雨":
            alert_type = AlertType.FLOOD
            type_icon = "💧"
        else:
            alert_type = AlertType.WEATHER_SEVERE
            type_icon = "⛈️"
        
        if severity >= 80:
            level = AlertLevel.CRITICAL
            title = f"🔴 {type_icon} 劇烈天氣警報"
        elif severity >= 60:
            level = AlertLevel.ALERT
            title = f"🚨 {type_icon} 天氣警報"
        elif severity >= 40:
            level = AlertLevel.WARNING
            title = f"⚠️ {type_icon} 天氣注意"
        else:
            level = AlertLevel.INFO
            title = f"ℹ️ {type_icon} 天氣資訊"
        
        message = f"天氣類型: {weather_type}\n"
        message += f"嚴重程度: {severity:.1f}%\n"
        message += f"預測期間: {forecast_period}\n\n"
        message += "請注意安全，做好防護措施。"
        
        return self.send_alert(
            alert_type=alert_type,
            alert_level=level,
            title=title,
            message=message,
            area="全台灣",
            prediction_id=prediction_id,
            custom_data={
                'weather_type': weather_type,
                'severity': severity
            }
        )
    
    def send_economic_alert(
        self,
        trend: str,
        confidence: float,
        forecast_period: str,
        prediction_id: Optional[str] = None
    ) -> Alert:
        """發送經濟警報"""
        if trend == "下降" and confidence >= 70:
            level = AlertLevel.ALERT
            title = "🚨 經濟警報 - 市場下行風險"
        elif trend == "震盪" and confidence >= 60:
            level = AlertLevel.WARNING
            title = "⚠️ 經濟注意 - 市場波動加劇"
        else:
            level = AlertLevel.INFO
            title = "ℹ️ 經濟資訊 - 市場趨勢更新"
        
        message = f"市場趨勢: {trend}\n"
        message += f"信心指數: {confidence:.1f}%\n"
        message += f"預測期間: {forecast_period}\n\n"
        message += "建議關注市場動態，審慎投資。"
        
        return self.send_alert(
            alert_type=AlertType.ECONOMIC,
            alert_level=level,
            title=title,
            message=message,
            area="全台灣",
            prediction_id=prediction_id,
            custom_data={
                'trend': trend,
                'confidence': confidence
            }
        )
    
    def broadcast_emergency(
        self,
        title: str,
        message: str,
        alert_type: AlertType = AlertType.SYSTEM
    ) -> List[Alert]:
        """廣播緊急通知到所有主題"""
        alerts = []
        
        for topic_type, topic in self.topics.items():
            alert = self.send_alert(
                alert_type=topic_type,
                alert_level=AlertLevel.EMERGENCY,
                title=title,
                message=message,
                area="全台灣"
            )
            alerts.append(alert)
        
        return alerts
    
    def _save_alert(self, alert: Alert):
        """保存警報到資料庫"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO alerts 
            (id, timestamp, alert_type, alert_level, title, message, area, 
             prediction_id, expires_at, sent_count, delivery_status, ntfy_response)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            alert.id, alert.timestamp, alert.alert_type, alert.alert_level,
            alert.title, alert.message, alert.area, alert.prediction_id,
            alert.expires_at, alert.sent_count, alert.delivery_status,
            json.dumps(alert.ntfy_response) if alert.ntfy_response else None
        ))
        
        conn.commit()
        conn.close()
    
    def _log_delivery(self, alert_id: str, topic: str, success: bool, response: Dict):
        """記錄發送日誌"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO delivery_logs (alert_id, topic, status, response_code, error_message)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            alert_id,
            topic,
            'success' if success else 'failed',
            response.get('code', 0),
            response.get('error', '')
        ))
        
        conn.commit()
        conn.close()
    
    def get_alert_history(self, limit: int = 50, alert_type: Optional[str] = None) -> List[Alert]:
        """獲取警報歷史"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if alert_type:
            cursor.execute('''
                SELECT * FROM alerts 
                WHERE alert_type = ?
                ORDER BY timestamp DESC LIMIT ?
            ''', (alert_type, limit))
        else:
            cursor.execute('''
                SELECT * FROM alerts 
                ORDER BY timestamp DESC LIMIT ?
            ''', (limit,))
        
        results = cursor.fetchall()
        conn.close()
        
        alerts = []
        for row in results:
            alerts.append(Alert(
                id=row[0],
                timestamp=row[1],
                alert_type=row[2],
                alert_level=row[3],
                title=row[4],
                message=row[5],
                area=row[6],
                prediction_id=row[7],
                expires_at=row[8],
                sent_count=row[9],
                delivery_status=row[10],
                ntfy_response=json.loads(row[11]) if row[11] else None
            ))
        
        return alerts
    
    def get_statistics(self, days: int = 7) -> Dict:
        """獲取警報統計"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # 總警報數
        cursor.execute('''
            SELECT COUNT(*) FROM alerts WHERE timestamp >= ?
        ''', (start_date,))
        total_alerts = cursor.fetchone()[0]
        
        # 按類型統計
        cursor.execute('''
            SELECT alert_type, COUNT(*) FROM alerts 
            WHERE timestamp >= ?
            GROUP BY alert_type
        ''', (start_date,))
        by_type = dict(cursor.fetchall())
        
        # 按等級統計
        cursor.execute('''
            SELECT alert_level, COUNT(*) FROM alerts 
            WHERE timestamp >= ?
            GROUP BY alert_level
        ''', (start_date,))
        by_level = dict(cursor.fetchall())
        
        # 發送成功率
        cursor.execute('''
            SELECT 
                SUM(CASE WHEN delivery_status = 'sent' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)
            FROM alerts WHERE timestamp >= ?
        ''', (start_date,))
        success_rate = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'period_days': days,
            'total_alerts': total_alerts,
            'by_type': by_type,
            'by_level': by_level,
            'delivery_success_rate': round(success_rate, 2)
        }


    # ===== 水情警報（增量擴充，不動現有方法）=====

    # 水情專屬 Ntfy topic
    FLOOD_TOPICS = {
        'flood_upstream_3km': '上游3km觀測站',
        'flood_upstream_1km': '上游1km觀測站',
        'flood_site_hq': '工地總機',
        'flood_general': '水情總覽',
    }

    def send_flood_alert(
        self,
        station_id: str,
        alert_level_num: int,
        water_level_m: float,
        weighted_score: float,
        trend: str = "stable",
        actions: List[str] = None,
        eta_critical_min: Optional[float] = None,
        prediction_id: Optional[str] = None,
        trigger_broadcast: bool = True,
    ) -> Alert:
        """
        發送水情警報 — 整合 Ntfy 推播 + 可選廣播喇叭觸發

        Args:
            station_id: 觀測站代號 (WA-001, WA-002, WA-HQ)
            alert_level_num: 0=安全, 1=注意, 2=警戒, 3=危險, 4=撤離
            water_level_m: 當前水位 (m)
            weighted_score: 五源加權分數 (0-100)
            trend: 趨勢 (rising/stable/falling)
            actions: 建議行動列表
            eta_critical_min: 預估幾分鐘後到危險水位
            prediction_id: 關聯預測 ID
            trigger_broadcast: 是否觸發實體廣播（喇叭+閃光燈）

        Returns:
            Alert 物件
        """
        level_names = {0: "安全", 1: "注意", 2: "警戒", 3: "危險", 4: "撤離"}
        level_emoji = {0: "🟢", 1: "🟡", 2: "🟠", 3: "🔴", 4: "🆘"}

        # 對應 AlertLevel
        if alert_level_num >= 4:
            level = AlertLevel.EMERGENCY
        elif alert_level_num >= 3:
            level = AlertLevel.CRITICAL
        elif alert_level_num >= 2:
            level = AlertLevel.ALERT
        elif alert_level_num >= 1:
            level = AlertLevel.WARNING
        else:
            level = AlertLevel.INFO

        emoji = level_emoji.get(alert_level_num, "⚠️")
        name = level_names.get(alert_level_num, "未知")
        title = f"{emoji} 水情{name} — {station_id}"

        message = f"觀測站: {station_id}\n"
        message += f"水位: {water_level_m:.2f} m\n"
        message += f"AI 加權分數: {weighted_score:.0f}/100\n"
        message += f"趨勢: {trend}\n"
        if eta_critical_min is not None:
            message += f"⏱ 預估 {eta_critical_min:.0f} 分鐘後到危險水位\n"
        if actions:
            message += "\n建議行動:\n" + "\n".join(f"• {a}" for a in actions[:5])

        # 發送主警報（用現有 FLOOD topic）
        alert = self.send_alert(
            alert_type=AlertType.FLOOD,
            alert_level=level,
            title=title,
            message=message,
            area=station_id,
            prediction_id=prediction_id,
            custom_data={
                'station_id': station_id,
                'water_level_m': water_level_m,
                'weighted_score': weighted_score,
                'trend': trend,
                'alert_level_num': alert_level_num,
            },
        )

        # 額外推送到站點專屬 topic
        station_topics = {
            'WA-001': 'flood_upstream_3km',
            'WA-002': 'flood_upstream_1km',
            'WA-HQ': 'flood_site_hq',
        }
        extra_topic = station_topics.get(station_id)
        if extra_topic:
            self._send_to_ntfy(alert, extra_topic)

        # 觸發實體廣播（等級 >= 2）
        if trigger_broadcast and alert_level_num >= 2:
            try:
                from water_alert.broadcast_controller import BroadcastController
                bc = BroadcastController()
                bc.trigger_alert(alert_level_num)
            except Exception as e:
                # 廣播不可用時不影響主流程
                pass

        return alert


if __name__ == '__main__':
    # 測試
    manager = NationalAlertManager()
    
    print("=== 國家級警報系統測試 ===\n")
    
    # 測試地震警報
    print("[1] 發送地震警報")
    alert = manager.send_earthquake_alert(
        magnitude=5.2,
        depth=15.0,
        location="台北市",
        risk_level=75.0,
        prediction_id="EQ_20260215_220000"
    )
    print(f"警報ID: {alert.id}")
    print(f"發送狀態: {alert.delivery_status}")
    print(f"Ntfy 回應: {alert.ntfy_response}\n")
    
    # 測試氣象警報
    print("[2] 發送氣象警報")
    alert2 = manager.send_weather_alert(
        weather_type="強風",
        severity=65.0,
        forecast_period="未來3-7天",
        prediction_id="WX_20260215_220100"
    )
    print(f"警報ID: {alert2.id}\n")
    
    # 獲取統計
    print("[3] 警報統計")
    stats = manager.get_statistics(days=7)
    print(json.dumps(stats, indent=2, ensure_ascii=False))
