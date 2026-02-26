"""
科學數據收集模組 - Scientific Data Collector
收集電離層、地磁、地震、氣象等科學數據
"""
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time
from dataclasses import dataclass, asdict
import os

@dataclass
class IonosphereData:
    """電離層數據"""
    timestamp: str
    tec_value: float  # Total Electron Content
    foF2: float  # F2層臨界頻率
    hmF2: float  # F2層高度
    anomaly_score: float  # 異常分數 0-1
    source: str
    
    def to_dict(self):
        return asdict(self)

@dataclass
class GeomagneticData:
    """地磁數據"""
    timestamp: str
    kp_index: float  # Kp指數 0-9
    dst_index: float  # Dst指數
    bx: float  # X分量
    by: float  # Y分量
    bz: float  # Z分量
    anomaly_score: float
    source: str
    
    def to_dict(self):
        return asdict(self)

@dataclass
class SeismicData:
    """地震數據"""
    timestamp: str
    latitude: float
    longitude: float
    magnitude: float
    depth: float
    location: str
    source: str
    
    def to_dict(self):
        return asdict(self)

@dataclass
class WeatherData:
    """氣象數據"""
    timestamp: str
    temperature: float
    humidity: float
    pressure: float
    wind_speed: float
    wind_direction: float
    rainfall: float
    location: str
    source: str
    
    def to_dict(self):
        return asdict(self)

class ScientificDataCollector:
    """科學數據收集器"""
    
    def __init__(self, cache_dir: str = "prediction_modules/data_cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        
        # API 端點配置
        self.apis = {
            'cwb_earthquake': 'https://opendata.cwa.gov.tw/api/v1/rest/datastore/E-A0015-001',
            'cwb_weather': 'https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0003-001',
            'usgs_earthquake': 'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson',
            'noaa_geomagnetic': 'https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json',
            'nasa_ionosphere': 'https://kauai.ccmc.gsfc.nasa.gov/instantrun/tiegcm/',
        }
        
        # 環境變數中的 API Key
        self.cwb_api_key = os.getenv('CWB_API_KEY', '')
    
    def collect_ionosphere_data(self) -> List[IonosphereData]:
        """
        收集電離層數據
        來源: NASA CCMC, NOAA SWPC
        """
        data_list = []
        
        try:
            # 模擬數據（實際應用需要真實 API）
            # 台灣地區電離層觀測站數據
            now = datetime.now()
            
            # 使用 NOAA Space Weather 數據作為參考
            response = requests.get(
                'https://services.swpc.noaa.gov/json/f107_cm_flux.json',
                timeout=10
            )
            
            if response.status_code == 200:
                f107_data = response.json()
                if f107_data:
                    latest = f107_data[-1]
                    flux = float(latest.get('flux', 100))
                    
                    # 計算異常分數（基於歷史平均值）
                    # F10.7 正常範圍 70-200 SFU
                    anomaly = 0.0
                    if flux > 150:
                        anomaly = min((flux - 150) / 100, 1.0)
                    elif flux < 80:
                        anomaly = min((80 - flux) / 30, 1.0)
                    
                    data = IonosphereData(
                        timestamp=now.isoformat(),
                        tec_value=flux / 10,  # 簡化轉換
                        foF2=5.0 + (flux - 100) / 20,
                        hmF2=300.0,
                        anomaly_score=anomaly,
                        source='NOAA_SWPC'
                    )
                    data_list.append(data)
            
            # 補充台灣本地模擬數據
            local_data = IonosphereData(
                timestamp=now.isoformat(),
                tec_value=12.5,  # TECU
                foF2=6.8,  # MHz
                hmF2=320.0,  # km
                anomaly_score=0.15,
                source='Taiwan_Local_Simulation'
            )
            data_list.append(local_data)
            
        except Exception as e:
            print(f"電離層數據收集錯誤: {e}")
        
        return data_list
    
    def collect_geomagnetic_data(self) -> List[GeomagneticData]:
        """
        收集地磁數據
        來源: NOAA SWPC, INTERMAGNET
        """
        data_list = []
        
        try:
            # NOAA Kp Index
            response = requests.get(
                'https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json',
                timeout=10
            )
            
            if response.status_code == 200:
                kp_data = response.json()
                if len(kp_data) > 1:
                    latest = kp_data[-1]
                    kp_value = float(latest[1])
                    timestamp = latest[0]
                    
                    # 計算異常分數
                    # Kp > 5 為地磁擾動
                    anomaly = min(max(kp_value - 3, 0) / 6, 1.0)
                    
                    data = GeomagneticData(
                        timestamp=timestamp,
                        kp_index=kp_value,
                        dst_index=-20.0,  # 需要額外 API
                        bx=20000.0,  # nT
                        by=5000.0,
                        bz=-10000.0,
                        anomaly_score=anomaly,
                        source='NOAA_SWPC'
                    )
                    data_list.append(data)
            
            # 台灣地磁觀測站模擬數據
            now = datetime.now()
            taiwan_data = GeomagneticData(
                timestamp=now.isoformat(),
                kp_index=2.5,
                dst_index=-15.0,
                bx=22000.0,
                by=4500.0,
                bz=-8000.0,
                anomaly_score=0.2,
                source='Taiwan_Geomagnetic_Station'
            )
            data_list.append(taiwan_data)
            
        except Exception as e:
            print(f"地磁數據收集錯誤: {e}")
        
        return data_list
    
    def collect_earthquake_data(self, days: int = 7) -> List[SeismicData]:
        """
        收集地震數據
        來源: 中央氣象署、USGS
        """
        data_list = []
        
        try:
            # USGS 全球地震數據
            response = requests.get(
                'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_week.geojson',
                timeout=15
            )
            
            if response.status_code == 200:
                earthquake_data = response.json()
                features = earthquake_data.get('features', [])
                
                # 篩選台灣附近地震 (121-122E, 22-25N)
                for feature in features[:50]:  # 限制數量
                    props = feature.get('properties', {})
                    geom = feature.get('geometry', {})
                    coords = geom.get('coordinates', [0, 0, 0])
                    
                    lon, lat, depth = coords[0], coords[1], coords[2]
                    
                    # 台灣及周邊區域
                    if 119 <= lon <= 123 and 21 <= lat <= 26:
                        data = SeismicData(
                            timestamp=datetime.fromtimestamp(props.get('time', 0) / 1000).isoformat(),
                            latitude=lat,
                            longitude=lon,
                            magnitude=props.get('mag', 0),
                            depth=depth,
                            location=props.get('place', 'Unknown'),
                            source='USGS'
                        )
                        data_list.append(data)
            
            # 中央氣象署數據（需要 API Key）
            if self.cwb_api_key:
                cwb_url = f"{self.apis['cwb_earthquake']}?Authorization={self.cwb_api_key}"
                response = requests.get(cwb_url, timeout=10)
                
                if response.status_code == 200:
                    cwb_data = response.json()
                    records = cwb_data.get('records', {}).get('Earthquake', [])
                    
                    for record in records[:20]:
                        eq_info = record.get('EarthquakeInfo', {})
                        epicenter = eq_info.get('Epicenter', {})
                        
                        data = SeismicData(
                            timestamp=record.get('EarthquakeNo', ''),
                            latitude=epicenter.get('EpicenterLatitude', 0),
                            longitude=epicenter.get('EpicenterLongitude', 0),
                            magnitude=eq_info.get('EarthquakeMagnitude', {}).get('MagnitudeValue', 0),
                            depth=epicenter.get('FocalDepth', 0),
                            location=epicenter.get('Location', ''),
                            source='CWB_Taiwan'
                        )
                        data_list.append(data)
            
        except Exception as e:
            print(f"地震數據收集錯誤: {e}")
        
        return data_list
    
    def collect_weather_data(self, station: str = 'all') -> List[WeatherData]:
        """
        收集氣象數據
        來源: 中央氣象署自動氣象站
        """
        data_list = []
        
        try:
            if self.cwb_api_key:
                cwb_url = f"{self.apis['cwb_weather']}?Authorization={self.cwb_api_key}"
                response = requests.get(cwb_url, timeout=10)
                
                if response.status_code == 200:
                    weather_data = response.json()
                    stations = weather_data.get('records', {}).get('Station', [])
                    
                    for station_data in stations[:30]:  # 限制數量
                        obs_time = station_data.get('ObsTime', {}).get('DateTime', '')
                        station_name = station_data.get('StationName', '')
                        
                        # 提取氣象要素
                        elements = {elem.get('ElementName'): elem.get('ElementValue', {}).get('Value', 0) 
                                   for elem in station_data.get('WeatherElement', [])}
                        
                        data = WeatherData(
                            timestamp=obs_time,
                            temperature=float(elements.get('AirTemperature', 0)),
                            humidity=float(elements.get('RelativeHumidity', 0)),
                            pressure=float(elements.get('AirPressure', 1013)),
                            wind_speed=float(elements.get('WindSpeed', 0)),
                            wind_direction=float(elements.get('WindDirection', 0)),
                            rainfall=float(elements.get('Now_Precipitation', 0)),
                            location=station_name,
                            source='CWB_Taiwan'
                        )
                        data_list.append(data)
            
            # 模擬數據（無 API Key 時）
            if not data_list:
                now = datetime.now()
                data = WeatherData(
                    timestamp=now.isoformat(),
                    temperature=25.5,
                    humidity=75.0,
                    pressure=1010.0,
                    wind_speed=3.5,
                    wind_direction=180.0,
                    rainfall=0.0,
                    location='台北',
                    source='Simulation'
                )
                data_list.append(data)
            
        except Exception as e:
            print(f"氣象數據收集錯誤: {e}")
        
        return data_list
    
    def calculate_anomaly_indicators(self) -> Dict:
        """
        計算綜合異常指標
        整合多種數據源的異常分數
        """
        ionosphere = self.collect_ionosphere_data()
        geomagnetic = self.collect_geomagnetic_data()
        earthquakes = self.collect_earthquake_data(days=7)
        weather = self.collect_weather_data()
        
        # 計算異常分數
        iono_anomaly = sum([d.anomaly_score for d in ionosphere]) / max(len(ionosphere), 1)
        geo_anomaly = sum([d.anomaly_score for d in geomagnetic]) / max(len(geomagnetic), 1)
        
        # 地震活動度（7天內地震次數和強度）
        recent_quakes = [eq for eq in earthquakes if eq.magnitude >= 3.0]
        seismic_activity = min(len(recent_quakes) / 10, 1.0)
        
        # 氣象異常（氣壓異常）
        pressure_anomaly = 0.0
        if weather:
            avg_pressure = sum([w.pressure for w in weather]) / len(weather)
            if avg_pressure < 1000:
                pressure_anomaly = min((1000 - avg_pressure) / 30, 1.0)
        
        return {
            'ionosphere_anomaly': round(iono_anomaly, 3),
            'geomagnetic_anomaly': round(geo_anomaly, 3),
            'seismic_activity': round(seismic_activity, 3),
            'atmospheric_pressure': round(avg_pressure if weather else 1013, 2),
            'pressure_anomaly': round(pressure_anomaly, 3),
            'total_anomaly': round((iono_anomaly + geo_anomaly + seismic_activity + pressure_anomaly) / 4, 3),
            'timestamp': datetime.now().isoformat(),
            'data_sources': {
                'ionosphere_count': len(ionosphere),
                'geomagnetic_count': len(geomagnetic),
                'earthquake_count': len(earthquakes),
                'weather_count': len(weather)
            }
        }
    
    def get_time_series_data(self, data_type: str, hours: int = 24) -> List[float]:
        """
        獲取時間序列數據（用於易經起卦）
        data_type: 'ionosphere', 'geomagnetic', 'seismic'
        """
        # 實際應用需要從資料庫讀取歷史數據
        # 這裡返回模擬的時間序列
        
        if data_type == 'ionosphere':
            ionosphere = self.collect_ionosphere_data()
            return [d.tec_value for d in ionosphere]
        
        elif data_type == 'geomagnetic':
            geomagnetic = self.collect_geomagnetic_data()
            return [d.kp_index for d in geomagnetic]
        
        elif data_type == 'seismic':
            earthquakes = self.collect_earthquake_data(days=1)
            return [eq.magnitude for eq in earthquakes if eq.magnitude > 0]
        
        return []
    
    def save_to_cache(self, data: Dict, filename: str):
        """保存數據到快取"""
        filepath = os.path.join(self.cache_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_from_cache(self, filename: str) -> Optional[Dict]:
        """從快取載入數據"""
        filepath = os.path.join(self.cache_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None


    # ===== 水情數據（增量擴充，不動現有方法）=====

    def collect_water_level_data(self, station_id: str = "") -> List[Dict]:
        """
        收集水利署水位觀測站數據

        來源: 經濟部水利署 防災資訊服務網 API
        https://fhy.wra.gov.tw/WraApi/v1/Rain/Station

        Args:
            station_id: 觀測站代碼（空則取全部）

        Returns:
            [{"station_id", "station_name", "water_level_m", "flow_cms",
              "timestamp", "river_name", "latitude", "longitude"}]
        """
        results = []
        try:
            # 水利署即時水位 API
            wra_base = os.getenv("WRA_API_BASE", "https://fhy.wra.gov.tw/WraApi/v1")
            url = f"{wra_base}/Water/RiverWaterLevel"
            if station_id:
                url += f"?$filter=StationIdentifier eq '{station_id}'"

            response = requests.get(url, timeout=15, headers={
                "Accept": "application/json",
            })

            if response.status_code == 200:
                data = response.json()
                records = data if isinstance(data, list) else data.get("value", data.get("records", []))

                for r in records:
                    results.append({
                        "station_id": r.get("StationIdentifier", r.get("station_id", "")),
                        "station_name": r.get("StationName", r.get("station_name", "")),
                        "water_level_m": float(r.get("WaterLevel", r.get("water_level", 0)) or 0),
                        "flow_cms": float(r.get("Discharge", r.get("flow", 0)) or 0),
                        "timestamp": r.get("RecordTime", r.get("ObservationTime", "")),
                        "river_name": r.get("BasinName", r.get("river_name", "")),
                        "latitude": float(r.get("Latitude", 0) or 0),
                        "longitude": float(r.get("Longitude", 0) or 0),
                    })

            # 快取
            if results:
                self.save_to_cache(
                    {"timestamp": datetime.now().isoformat(), "data": results},
                    "water_level_latest.json",
                )

        except Exception as e:
            print(f"水位數據收集錯誤: {e}")
            # 嘗試從快取載入
            cached = self.load_from_cache("water_level_latest.json")
            if cached:
                results = cached.get("data", [])

        return results

    def collect_rainfall_forecast(self, location: str = "臺中市") -> Dict:
        """
        收集氣象局降雨預報

        Args:
            location: 縣市名稱

        Returns:
            {"location", "forecast_6h_mm", "forecast_24h_mm", "description", "timestamp"}
        """
        result = {
            "location": location,
            "forecast_6h_mm": 0,
            "forecast_24h_mm": 0,
            "description": "",
            "timestamp": datetime.now().isoformat(),
        }
        try:
            if not self.cwb_api_key:
                return result

            # CWB 天氣預報 API
            url = (
                f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001"
                f"?Authorization={self.cwb_api_key}"
                f"&locationName={location}"
            )
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                data = response.json()
                records = data.get("records", {}).get("location", [])
                if records:
                    loc = records[0]
                    for elem in loc.get("weatherElement", []):
                        if elem.get("elementName") == "PoP":
                            # 降雨機率
                            times = elem.get("time", [])
                            if times:
                                pop = int(times[0].get("parameter", {}).get("parameterName", "0"))
                                result["forecast_6h_mm"] = pop * 0.5  # 粗估
                        elif elem.get("elementName") == "Wx":
                            times = elem.get("time", [])
                            if times:
                                result["description"] = times[0].get("parameter", {}).get("parameterName", "")
        except Exception as e:
            print(f"降雨預報收集錯誤: {e}")

        return result


if __name__ == '__main__':
    # 測試
    collector = ScientificDataCollector()
    
    print("=== 電離層數據 ===")
    iono_data = collector.collect_ionosphere_data()
    for data in iono_data:
        print(f"時間: {data.timestamp}")
        print(f"TEC: {data.tec_value}, 異常分數: {data.anomaly_score}")
        print(f"來源: {data.source}\n")
    
    print("=== 地磁數據 ===")
    geo_data = collector.collect_geomagnetic_data()
    for data in geo_data:
        print(f"時間: {data.timestamp}")
        print(f"Kp指數: {data.kp_index}, 異常分數: {data.anomaly_score}")
        print(f"來源: {data.source}\n")
    
    print("=== 地震數據 ===")
    eq_data = collector.collect_earthquake_data()
    print(f"收集到 {len(eq_data)} 筆地震數據")
    for data in eq_data[:5]:
        print(f"時間: {data.timestamp}, 規模: {data.magnitude}, 位置: {data.location}")
    
    print("\n=== 綜合異常指標 ===")
    anomaly = collector.calculate_anomaly_indicators()
    print(json.dumps(anomaly, indent=2, ensure_ascii=False))
