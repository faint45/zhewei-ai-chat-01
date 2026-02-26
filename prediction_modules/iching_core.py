"""
易經八卦核心模組 - I Ching Core Module
結合傳統易經卦象與現代科學數據進行預測分析
"""
import random
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import json
from dataclasses import dataclass, asdict

@dataclass
class Hexagram:
    """卦象數據結構"""
    number: int
    name_zh: str
    name_pinyin: str
    trigram_upper: str
    trigram_lower: str
    element: str
    nature: str
    interpretation: str
    changing_lines: List[int] = None
    
    def to_dict(self):
        return asdict(self)

class IChingEngine:
    """易經推演引擎"""
    
    # 八卦基本屬性
    TRIGRAMS = {
        '乾': {'binary': '111', 'element': '金', 'nature': '天', 'direction': '西北', 'attribute': '剛健'},
        '坤': {'binary': '000', 'element': '土', 'nature': '地', 'direction': '西南', 'attribute': '柔順'},
        '震': {'binary': '001', 'element': '木', 'nature': '雷', 'direction': '東', 'attribute': '動'},
        '巽': {'binary': '011', 'element': '木', 'nature': '風', 'direction': '東南', 'attribute': '入'},
        '坎': {'binary': '010', 'element': '水', 'nature': '水', 'direction': '北', 'attribute': '陷'},
        '離': {'binary': '101', 'element': '火', 'nature': '火', 'direction': '南', 'attribute': '麗'},
        '艮': {'binary': '100', 'element': '土', 'nature': '山', 'direction': '東北', 'attribute': '止'},
        '兌': {'binary': '110', 'element': '金', 'nature': '澤', 'direction': '西', 'attribute': '悅'}
    }
    
    # 64卦完整資料庫
    HEXAGRAMS = {
        1: {'name': '乾為天', 'upper': '乾', 'lower': '乾', 'element': '金', 'nature': '至剛至健', 
            'interpretation': '大吉大利，事業亨通，但需防過剛則折'},
        2: {'name': '坤為地', 'upper': '坤', 'lower': '坤', 'element': '土', 'nature': '至柔至順',
            'interpretation': '柔順承載，厚德載物，宜守不宜攻'},
        3: {'name': '水雷屯', 'upper': '坎', 'lower': '震', 'element': '水木', 'nature': '初生艱難',
            'interpretation': '萬事起頭難，需堅持突破，地震前兆'},
        4: {'name': '山水蒙', 'upper': '艮', 'lower': '坎', 'element': '土水', 'nature': '蒙昧待啟',
            'interpretation': '需要學習和指導，不宜輕舉妄動'},
        5: {'name': '水天需', 'upper': '坎', 'lower': '乾', 'element': '水金', 'nature': '等待時機',
            'interpretation': '需耐心等待，時機未到勿強求'},
        6: {'name': '天水訟', 'upper': '乾', 'lower': '坎', 'element': '金水', 'nature': '爭訟不利',
            'interpretation': '易生爭端，宜和解不宜對抗'},
        7: {'name': '地水師', 'upper': '坤', 'lower': '坎', 'element': '土水', 'nature': '統兵征戰',
            'interpretation': '需要組織和紀律，眾志成城'},
        8: {'name': '水地比', 'upper': '坎', 'lower': '坤', 'element': '水土', 'nature': '親比輔佐',
            'interpretation': '團結合作，互相扶持'},
        9: {'name': '風天小畜', 'upper': '巽', 'lower': '乾', 'element': '木金', 'nature': '小有積蓄',
            'interpretation': '小有成就，需繼續積累'},
        10: {'name': '天澤履', 'upper': '乾', 'lower': '兌', 'element': '金金', 'nature': '履險如夷',
            'interpretation': '謹慎行事，如履薄冰'},
        # 地震相關重要卦象
        51: {'name': '震為雷', 'upper': '震', 'lower': '震', 'element': '木', 'nature': '震動驚恐',
            'interpretation': '地震強烈預兆，震動劇烈，需高度警戒'},
        52: {'name': '艮為山', 'upper': '艮', 'lower': '艮', 'element': '土', 'nature': '靜止穩定',
            'interpretation': '山體穩固，但需防地層變動'},
        56: {'name': '火山旅', 'upper': '離', 'lower': '艮', 'element': '火土', 'nature': '地熱異常',
            'interpretation': '地下能量累積，火山或地震前兆'},
        # 氣象相關卦象
        29: {'name': '坎為水', 'upper': '坎', 'lower': '坎', 'element': '水', 'nature': '重重險阻',
            'interpretation': '大雨洪水，水患之兆'},
        30: {'name': '離為火', 'upper': '離', 'lower': '離', 'element': '火', 'nature': '炎熱乾燥',
            'interpretation': '高溫乾旱，火災之兆'},
        57: {'name': '巽為風', 'upper': '巽', 'lower': '巽', 'element': '木', 'nature': '風行草偃',
            'interpretation': '強風颱風，風災之兆'},
    }
    
    def __init__(self):
        """初始化易經引擎"""
        self._load_full_hexagrams()
    
    def _load_full_hexagrams(self):
        """載入完整64卦資料（簡化版，實際應用需完整資料庫）"""
        for i in range(1, 65):
            if i not in self.HEXAGRAMS:
                self.HEXAGRAMS[i] = {
                    'name': f'第{i}卦',
                    'upper': '乾',
                    'lower': '乾',
                    'element': '未定',
                    'nature': '待補充',
                    'interpretation': '需補充完整卦辭'
                }
    
    def cast_hexagram_by_time(self, timestamp: datetime = None) -> Hexagram:
        """
        時間起卦法 - 根據時間推算卦象
        使用年月日時數字進行起卦
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        year = timestamp.year
        month = timestamp.month
        day = timestamp.day
        hour = timestamp.hour
        
        # 上卦 = (年 + 月 + 日) % 8
        upper_num = (year + month + day) % 8
        if upper_num == 0:
            upper_num = 8
        
        # 下卦 = (年 + 月 + 日 + 時) % 8
        lower_num = (year + month + day + hour) % 8
        if lower_num == 0:
            lower_num = 8
        
        # 動爻 = (年 + 月 + 日 + 時) % 6
        changing_line = (year + month + day + hour) % 6
        if changing_line == 0:
            changing_line = 6
        
        # 計算卦號 (簡化算法)
        hexagram_num = ((upper_num - 1) * 8 + lower_num) % 64
        if hexagram_num == 0:
            hexagram_num = 64
        
        return self._create_hexagram(hexagram_num, [changing_line])
    
    def cast_hexagram_by_data(self, data_values: List[float]) -> Hexagram:
        """
        數據起卦法 - 根據科學數據推算卦象
        data_values: 科學數據陣列（電離層、地磁等）
        """
        if not data_values or len(data_values) < 2:
            return self.cast_hexagram_by_time()
        
        # 使用數據值的總和和變化率起卦
        total = sum(data_values)
        variance = sum([(x - total/len(data_values))**2 for x in data_values])
        
        upper_num = int(abs(total)) % 8
        if upper_num == 0:
            upper_num = 8
        
        lower_num = int(abs(variance * 100)) % 8
        if lower_num == 0:
            lower_num = 8
        
        # 找出變化最大的位置作為動爻
        if len(data_values) >= 6:
            diffs = [abs(data_values[i] - data_values[i-1]) for i in range(1, min(7, len(data_values)))]
            changing_line = diffs.index(max(diffs)) + 1
        else:
            changing_line = int(abs(variance)) % 6 + 1
        
        hexagram_num = ((upper_num - 1) * 8 + lower_num) % 64
        if hexagram_num == 0:
            hexagram_num = 64
        
        return self._create_hexagram(hexagram_num, [changing_line])
    
    def cast_hexagram_yarrow_stalks(self) -> Hexagram:
        """
        蓍草起卦法 - 傳統隨機起卦（用於對照驗證）
        """
        lines = []
        changing_lines = []
        
        for i in range(6):
            # 簡化的蓍草算法
            first = random.choice([6, 7, 8, 9])
            lines.append(first)
            if first in [6, 9]:  # 老陰老陽為變爻
                changing_lines.append(i + 1)
        
        # 轉換為卦號
        binary = ''.join(['1' if x in [7, 9] else '0' for x in lines])
        hexagram_num = int(binary, 2) % 64
        if hexagram_num == 0:
            hexagram_num = 64
        
        return self._create_hexagram(hexagram_num, changing_lines)
    
    def _create_hexagram(self, number: int, changing_lines: List[int] = None) -> Hexagram:
        """創建卦象對象"""
        hex_data = self.HEXAGRAMS.get(number, self.HEXAGRAMS[1])
        
        return Hexagram(
            number=number,
            name_zh=hex_data['name'],
            name_pinyin='',  # 可補充拼音
            trigram_upper=hex_data['upper'],
            trigram_lower=hex_data['lower'],
            element=hex_data['element'],
            nature=hex_data['nature'],
            interpretation=hex_data['interpretation'],
            changing_lines=changing_lines or []
        )
    
    def get_transformed_hexagram(self, original: Hexagram) -> Optional[Hexagram]:
        """
        獲取變卦 - 根據動爻推算變化後的卦象
        """
        if not original.changing_lines:
            return None
        
        # 簡化算法：變卦號 = (原卦號 + 動爻數) % 64
        new_number = (original.number + len(original.changing_lines)) % 64
        if new_number == 0:
            new_number = 64
        
        return self._create_hexagram(new_number, [])
    
    def interpret_for_earthquake(self, hexagram: Hexagram, scientific_data: Dict) -> Dict:
        """
        地震預測解讀
        結合卦象與科學數據進行地震預測分析
        """
        risk_level = 0
        indicators = []
        
        # 卦象分析
        if hexagram.number in [3, 51]:  # 水雷屯、震為雷
            risk_level += 40
            indicators.append('卦象顯示強烈震動之兆')
        
        if hexagram.number in [52, 56]:  # 艮為山、火山旅
            risk_level += 30
            indicators.append('山體或地層變動跡象')
        
        if '震' in [hexagram.trigram_upper, hexagram.trigram_lower]:
            risk_level += 20
            indicators.append('震卦出現，地動之象')
        
        # 動爻分析
        if hexagram.changing_lines:
            if 1 in hexagram.changing_lines or 6 in hexagram.changing_lines:
                risk_level += 15
                indicators.append('初爻或上爻動，地基不穩')
        
        # 科學數據修正
        if scientific_data:
            if scientific_data.get('ionosphere_anomaly', 0) > 0.7:
                risk_level += 20
                indicators.append('電離層異常嚴重')
            
            if scientific_data.get('geomagnetic_anomaly', 0) > 0.6:
                risk_level += 15
                indicators.append('地磁場擾動明顯')
        
        risk_level = min(risk_level, 100)
        
        return {
            'risk_level': risk_level,
            'risk_category': self._categorize_risk(risk_level),
            'indicators': indicators,
            'hexagram_interpretation': hexagram.interpretation,
            'recommendation': self._get_earthquake_recommendation(risk_level)
        }
    
    def interpret_for_weather(self, hexagram: Hexagram, scientific_data: Dict) -> Dict:
        """
        氣象預測解讀
        """
        weather_type = '正常'
        severity = 0
        indicators = []
        
        # 水卦 - 降雨
        if hexagram.number == 29 or '坎' in [hexagram.trigram_upper, hexagram.trigram_lower]:
            weather_type = '降雨'
            severity += 30
            indicators.append('坎卦主水，降雨之兆')
        
        # 火卦 - 高溫
        if hexagram.number == 30 or '離' in [hexagram.trigram_upper, hexagram.trigram_lower]:
            weather_type = '高溫'
            severity += 25
            indicators.append('離卦主火，炎熱之象')
        
        # 風卦 - 強風
        if hexagram.number == 57 or '巽' in [hexagram.trigram_upper, hexagram.trigram_lower]:
            weather_type = '強風'
            severity += 35
            indicators.append('巽卦主風，颱風之兆')
        
        # 科學數據修正
        if scientific_data:
            pressure = scientific_data.get('atmospheric_pressure', 1013)
            if pressure < 1000:
                severity += 20
                indicators.append('氣壓異常偏低')
            
            humidity = scientific_data.get('humidity', 50)
            if humidity > 80:
                severity += 10
                indicators.append('濕度過高')
        
        return {
            'weather_type': weather_type,
            'severity': min(severity, 100),
            'indicators': indicators,
            'hexagram_interpretation': hexagram.interpretation,
            'forecast_period': '未來3-7天'
        }
    
    def interpret_for_economy(self, hexagram: Hexagram, market_data: Dict) -> Dict:
        """
        經濟預測解讀
        """
        trend = '持平'
        confidence = 50
        indicators = []
        
        # 乾卦 - 上升
        if '乾' in [hexagram.trigram_upper, hexagram.trigram_lower]:
            trend = '上升'
            confidence += 20
            indicators.append('乾卦剛健，市場向上')
        
        # 坤卦 - 下降
        if '坤' in [hexagram.trigram_upper, hexagram.trigram_lower]:
            trend = '下降'
            confidence += 15
            indicators.append('坤卦柔順，市場回調')
        
        # 震卦 - 震盪
        if '震' in [hexagram.trigram_upper, hexagram.trigram_lower]:
            trend = '震盪'
            confidence += 25
            indicators.append('震卦動盪，市場波動')
        
        # 市場數據修正
        if market_data:
            volatility = market_data.get('volatility', 0)
            if volatility > 0.3:
                trend = '震盪'
                confidence += 15
        
        return {
            'trend': trend,
            'confidence': min(confidence, 100),
            'indicators': indicators,
            'hexagram_interpretation': hexagram.interpretation,
            'forecast_period': '未來1-3個月'
        }
    
    def _categorize_risk(self, risk_level: int) -> str:
        """風險等級分類"""
        if risk_level >= 80:
            return '極高風險'
        elif risk_level >= 60:
            return '高風險'
        elif risk_level >= 40:
            return '中等風險'
        elif risk_level >= 20:
            return '低風險'
        else:
            return '極低風險'
    
    def _get_earthquake_recommendation(self, risk_level: int) -> str:
        """地震建議"""
        if risk_level >= 80:
            return '建議發布地震警報，加強監測，準備應急措施'
        elif risk_level >= 60:
            return '建議提高警戒，密切監測科學數據'
        elif risk_level >= 40:
            return '建議持續觀察，注意異常現象'
        else:
            return '維持正常監測即可'


if __name__ == '__main__':
    # 測試
    engine = IChingEngine()
    
    # 時間起卦
    hex1 = engine.cast_hexagram_by_time()
    print(f"時間起卦: {hex1.name_zh} (第{hex1.number}卦)")
    print(f"卦象: {hex1.trigram_upper}上{hex1.trigram_lower}下")
    print(f"解釋: {hex1.interpretation}\n")
    
    # 數據起卦
    test_data = [3.5, 4.2, 3.8, 5.1, 4.5, 3.9]
    hex2 = engine.cast_hexagram_by_data(test_data)
    print(f"數據起卦: {hex2.name_zh} (第{hex2.number}卦)")
    
    # 地震預測
    scientific_data = {
        'ionosphere_anomaly': 0.75,
        'geomagnetic_anomaly': 0.65
    }
    prediction = engine.interpret_for_earthquake(hex2, scientific_data)
    print(f"\n地震預測:")
    print(f"風險等級: {prediction['risk_level']}% - {prediction['risk_category']}")
    print(f"指標: {', '.join(prediction['indicators'])}")
    print(f"建議: {prediction['recommendation']}")
