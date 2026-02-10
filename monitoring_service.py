#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
築未科技 - API 監控服務
提供流量統計、費用追蹤、性能監控和告警功能
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import sqlite3
from pathlib import Path

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class APIRequest:
    """API 請求記錄"""
    request_id: str
    timestamp: datetime
    source: str  # telegram, discord, wechat, web
    user_id: str
    command: str
    status: str  # success, error
    execution_time: float  # 秒
    tokens_used: int = 0  # 使用的 token 數
    cost: float = 0.0  # 費用（USD）

    def to_dict(self):
        """轉換為字典"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class APIMetrics:
    """API 指標"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_execution_time: float = 0.0
    total_tokens: int = 0
    total_cost: float = 0.0
    avg_execution_time: float = 0.0
    success_rate: float = 0.0


class APIMonitor:
    """API 監控器"""
    
    def __init__(self, db_path: str = "api_monitoring.db"):
        self.db_path = db_path
        self.request_history: deque = deque(maxlen=1000)  # 記錄最近1000個請求
        self.hourly_stats: Dict[str, Dict] = defaultdict(lambda: {
            'requests': 0,
            'tokens': 0,
            'cost': 0.0,
            'errors': 0
        })
        self.daily_stats: Dict[str, Dict] = defaultdict(lambda: {
            'requests': 0,
            'tokens': 0,
            'cost': 0.0,
            'errors': 0
        })
        self.alerts: List[Dict] = []
        self.cost_threshold = 10.0  # 每日費用閾值（USD）
        self.error_rate_threshold = 0.1  # 錯誤率閾值（10%）
        
        self._init_database()
        
    def _init_database(self):
        """初始化數據庫"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 請求日誌表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT UNIQUE NOT NULL,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL,
                user_id TEXT NOT NULL,
                command TEXT NOT NULL,
                status TEXT NOT NULL,
                execution_time REAL NOT NULL,
                tokens_used INTEGER DEFAULT 0,
                cost REAL DEFAULT 0.0
            )
        """)
        
        # 小時統計表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hourly_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hour TEXT NOT NULL,
                source TEXT NOT NULL,
                requests INTEGER DEFAULT 0,
                tokens INTEGER DEFAULT 0,
                cost REAL DEFAULT 0.0,
                errors INTEGER DEFAULT 0,
                UNIQUE(hour, source)
            )
        """)
        
        # 每日統計表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                source TEXT NOT NULL,
                requests INTEGER DEFAULT 0,
                tokens INTEGER DEFAULT 0,
                cost REAL DEFAULT 0.0,
                errors INTEGER DEFAULT 0,
                UNIQUE(date, source)
            )
        """)
        
        # 告警記錄表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                resolved BOOLEAN DEFAULT 0
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("✓ 監控數據庫初始化完成")
    
    async def log_request(
        self,
        request_id: str,
        source: str,
        user_id: str,
        command: str,
        status: str,
        execution_time: float,
        tokens_used: int = 0,
        cost: float = 0.0
    ) -> None:
        """記錄 API 請求"""
        try:
            request = APIRequest(
                request_id=request_id,
                timestamp=datetime.now(),
                source=source,
                user_id=user_id,
                command=command,
                status=status,
                execution_time=execution_time,
                tokens_used=tokens_used,
                cost=cost
            )
            
            # 保存到數據庫
            self._save_request(request)
            
            # 更新統計
            self._update_stats(request)
            
            # 檢查告警
            await self._check_alerts(request)
            
            # 添加到歷史記錄
            self.request_history.append(request)
            
            logger.info(f"記錄請求: {request_id} ({source}) - {status} - {execution_time:.3f}s")
            
        except Exception as e:
            logger.error(f"記錄請求失敗: {e}")
    
    def _save_request(self, request: APIRequest):
        """保存請求到數據庫"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO api_requests 
                (request_id, timestamp, source, user_id, command, status, execution_time, tokens_used, cost)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                request.request_id,
                request.timestamp.isoformat(),
                request.source,
                request.user_id,
                request.command,
                request.status,
                request.execution_time,
                request.tokens_used,
                request.cost
            ))
            conn.commit()
        except Exception as e:
            logger.error(f"保存請求失敗: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def _update_stats(self, request: APIRequest):
        """更新統計數據"""
        hour = request.timestamp.strftime("%Y-%m-%d %H:00")
        date = request.timestamp.strftime("%Y-%m-%d")
        
        # 更新小時統計
        key = f"{hour}_{request.source}"
        self.hourly_stats[key]['requests'] += 1
        self.hourly_stats[key]['tokens'] += request.tokens_used
        self.hourly_stats[key]['cost'] += request.cost
        if request.status == 'error':
            self.hourly_stats[key]['errors'] += 1
        
        # 更新每日統計
        key = f"{date}_{request.source}"
        self.daily_stats[key]['requests'] += 1
        self.daily_stats[key]['tokens'] += request.tokens_used
        self.daily_stats[key]['cost'] += request.cost
        if request.status == 'error':
            self.daily_stats[key]['errors'] += 1
        
        # 保存到數據庫
        self._save_stats_to_db(hour, date, request.source)
    
    def _save_stats_to_db(self, hour: str, date: str, source: str):
        """保存統計到數據庫"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 小時統計
            key = f"{hour}_{source}"
            cursor.execute("""
                INSERT OR REPLACE INTO hourly_stats 
                (hour, source, requests, tokens, cost, errors)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                hour, source,
                self.hourly_stats[key]['requests'],
                self.hourly_stats[key]['tokens'],
                self.hourly_stats[key]['cost'],
                self.hourly_stats[key]['errors']
            ))
            
            # 每日統計
            key = f"{date}_{source}"
            cursor.execute("""
                INSERT OR REPLACE INTO daily_stats 
                (date, source, requests, tokens, cost, errors)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                date, source,
                self.daily_stats[key]['requests'],
                self.daily_stats[key]['tokens'],
                self.daily_stats[key]['cost'],
                self.daily_stats[key]['errors']
            ))
            
            conn.commit()
        except Exception as e:
            logger.error(f"保存統計失敗: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    async def _check_alerts(self, request: APIRequest):
        """檢查告警條件"""
        alerts = []
        
        # 檢查每日費用
        date = request.timestamp.strftime("%Y-%m-%d")
        total_cost = self._get_daily_cost(date)
        if total_cost > self.cost_threshold:
            alert = {
                'timestamp': datetime.now().isoformat(),
                'type': 'cost_alert',
                'severity': 'warning' if total_cost < self.cost_threshold * 2 else 'critical',
                'message': f"每日費用超過閾值: ${total_cost:.2f} (閾值: ${self.cost_threshold:.2f})"
            }
            alerts.append(alert)
            self._save_alert(alert)
        
        # 檢查錯誤率
        error_rate = self._get_error_rate(date)
        if error_rate > self.error_rate_threshold:
            alert = {
                'timestamp': datetime.now().isoformat(),
                'type': 'error_rate_alert',
                'severity': 'warning' if error_rate < self.error_rate_threshold * 2 else 'critical',
                'message': f"錯誤率過高: {error_rate*100:.1f}% (閾值: {self.error_rate_threshold*100:.1f}%)"
            }
            alerts.append(alert)
            self._save_alert(alert)
        
        return alerts
    
    def _save_alert(self, alert: Dict):
        """保存告警"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO alerts (timestamp, alert_type, severity, message)
                VALUES (?, ?, ?, ?)
            """, (alert['timestamp'], alert['type'], alert['severity'], alert['message']))
            conn.commit()
        except Exception as e:
            logger.error(f"保存告警失敗: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def _get_daily_cost(self, date: str) -> float:
        """獲取每日費用"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT SUM(cost) FROM daily_stats WHERE date = ?
            """, (date,))
            result = cursor.fetchone()
            return result[0] if result[0] else 0.0
        finally:
            conn.close()
    
    def _get_error_rate(self, date: str) -> float:
        """獲取錯誤率"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT SUM(requests), SUM(errors) FROM daily_stats WHERE date = ?
            """, (date,))
            result = cursor.fetchone()
            if result[0] and result[0] > 0:
                return result[1] / result[0]
            return 0.0
        finally:
            conn.close()
    
    def get_metrics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        source: Optional[str] = None
    ) -> APIMetrics:
        """獲取 API 指標"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            query = "SELECT COUNT(*), SUM(execution_time), SUM(tokens_used), SUM(cost) FROM api_requests WHERE 1=1"
            params = []
            
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time.isoformat())
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time.isoformat())
            if source:
                query += " AND source = ?"
                params.append(source)
            
            cursor.execute(query, params)
            result = cursor.fetchone()
            
            # 獲取成功/失敗計數
            query2 = f"{query} AND status = 'success'"
            cursor.execute(query2, params)
            success_result = cursor.fetchone()
            successful_requests = success_result[0] if success_result[0] else 0
            
            total_requests = result[0] if result[0] else 0
            failed_requests = total_requests - successful_requests
            total_execution_time = result[1] if result[1] else 0.0
            total_tokens = result[2] if result[2] else 0
            total_cost = result[3] if result[3] else 0.0
            
            metrics = APIMetrics(
                total_requests=total_requests,
                successful_requests=successful_requests,
                failed_requests=failed_requests,
                total_execution_time=total_execution_time,
                total_tokens=total_tokens,
                total_cost=total_cost,
                avg_execution_time=total_execution_time / total_requests if total_requests > 0 else 0.0,
                success_rate=successful_requests / total_requests if total_requests > 0 else 0.0
            )
            
            return metrics
        finally:
            conn.close()
    
    def get_recent_requests(self, limit: int = 50) -> List[Dict]:
        """獲取最近的請求"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM api_requests 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
            
            columns = [desc[0] for desc in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            return results
        finally:
            conn.close()
    
    def get_hourly_stats(self, hours: int = 24) -> List[Dict]:
        """獲取小時統計"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT hour, source, SUM(requests) as total_requests,
                       SUM(tokens) as total_tokens,
                       SUM(cost) as total_cost,
                       SUM(errors) as total_errors
                FROM hourly_stats
                WHERE hour >= datetime('now', '-{} hours')
                GROUP BY hour, source
                ORDER BY hour DESC
            """.format(hours))
            
            columns = [desc[0] for desc in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            return results
        finally:
            conn.close()
    
    def get_daily_stats(self, days: int = 7) -> List[Dict]:
        """獲取每日統計"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT date, source, SUM(requests) as total_requests,
                       SUM(tokens) as total_tokens,
                       SUM(cost) as total_cost,
                       SUM(errors) as total_errors
                FROM daily_stats
                WHERE date >= date('now', '-{} days')
                GROUP BY date, source
                ORDER BY date DESC
            """.format(days))
            
            columns = [desc[0] for desc in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            return results
        finally:
            conn.close()
    
    def get_alerts(self, limit: int = 20) -> List[Dict]:
        """獲取告警記錄"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM alerts 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
            
            columns = [desc[0] for desc in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            return results
        finally:
            conn.close()
    
    def generate_report(self, report_type: str = "daily") -> Dict:
        """生成報告"""
        today = datetime.now()
        
        if report_type == "daily":
            start_time = today.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = today
        elif report_type == "weekly":
            start_time = today - timedelta(days=7)
            end_time = today
        elif report_type == "monthly":
            start_time = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_time = today
        else:
            raise ValueError(f"不支持的報告類型: {report_type}")
        
        metrics = self.get_metrics(start_time, end_time)
        
        return {
            "report_type": report_type,
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "metrics": {
                "total_requests": metrics.total_requests,
                "successful_requests": metrics.successful_requests,
                "failed_requests": metrics.failed_requests,
                "total_tokens": metrics.total_tokens,
                "total_cost": metrics.total_cost,
                "avg_execution_time": metrics.avg_execution_time,
                "success_rate": metrics.success_rate
            },
            "breakdown_by_source": self._get_breakdown_by_source(start_time, end_time)
        }
    
    def _get_breakdown_by_source(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """按來源分組的統計"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT source, COUNT(*) as requests,
                       AVG(execution_time) as avg_time,
                       SUM(tokens_used) as tokens,
                       SUM(cost) as cost,
                       SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success,
                       SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as errors
                FROM api_requests
                WHERE timestamp >= ? AND timestamp <= ?
                GROUP BY source
            """, (start_time.isoformat(), end_time.isoformat()))
            
            columns = [desc[0] for desc in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            return results
        finally:
            conn.close()


# 全局監控器實例
monitor = APIMonitor()
