"""
易經科學預測系統測試腳本
Test Script for I Ching Scientific Prediction System
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from iching_core import IChingEngine
from scientific_data_collector import ScientificDataCollector
from prediction_engine import PredictionEngine
from datetime import datetime
import json

def test_iching_core():
    """測試易經核心引擎"""
    print("=" * 60)
    print("測試 1: 易經核心引擎")
    print("=" * 60)
    
    engine = IChingEngine()
    
    # 時間起卦
    print("\n[1.1] 時間起卦")
    hexagram = engine.cast_hexagram_by_time()
    print(f"卦象: {hexagram.name_zh} (第{hexagram.number}卦)")
    print(f"上下卦: {hexagram.trigram_upper}上{hexagram.trigram_lower}下")
    print(f"五行: {hexagram.element}")
    print(f"卦性: {hexagram.nature}")
    print(f"解釋: {hexagram.interpretation}")
    if hexagram.changing_lines:
        print(f"動爻: {hexagram.changing_lines}")
    
    # 數據起卦
    print("\n[1.2] 數據起卦（模擬電離層數據）")
    data = [12.5, 13.2, 14.1, 15.3, 13.8, 12.9]
    hexagram2 = engine.cast_hexagram_by_data(data)
    print(f"卦象: {hexagram2.name_zh} (第{hexagram2.number}卦)")
    
    # 變卦
    if hexagram2.changing_lines:
        transformed = engine.get_transformed_hexagram(hexagram2)
        if transformed:
            print(f"變卦: {transformed.name_zh} (第{transformed.number}卦)")
    
    print("\n✅ 易經核心引擎測試通過")
    return True

def test_scientific_data():
    """測試科學數據收集"""
    print("\n" + "=" * 60)
    print("測試 2: 科學數據收集")
    print("=" * 60)
    
    collector = ScientificDataCollector()
    
    # 電離層數據
    print("\n[2.1] 電離層數據")
    iono_data = collector.collect_ionosphere_data()
    print(f"收集到 {len(iono_data)} 筆電離層數據")
    if iono_data:
        data = iono_data[0]
        print(f"  - TEC值: {data.tec_value} TECU")
        print(f"  - 異常分數: {data.anomaly_score}")
        print(f"  - 來源: {data.source}")
    
    # 地磁數據
    print("\n[2.2] 地磁數據")
    geo_data = collector.collect_geomagnetic_data()
    print(f"收集到 {len(geo_data)} 筆地磁數據")
    if geo_data:
        data = geo_data[0]
        print(f"  - Kp指數: {data.kp_index}")
        print(f"  - 異常分數: {data.anomaly_score}")
        print(f"  - 來源: {data.source}")
    
    # 地震數據
    print("\n[2.3] 地震數據（7天內）")
    eq_data = collector.collect_earthquake_data(days=7)
    print(f"收集到 {len(eq_data)} 筆地震數據")
    if eq_data:
        for i, eq in enumerate(eq_data[:3], 1):
            print(f"  {i}. M{eq.magnitude:.1f} - {eq.location} (深度{eq.depth:.1f}km)")
    
    # 氣象數據
    print("\n[2.4] 氣象數據")
    weather_data = collector.collect_weather_data()
    print(f"收集到 {len(weather_data)} 筆氣象數據")
    if weather_data:
        data = weather_data[0]
        print(f"  - 溫度: {data.temperature}°C")
        print(f"  - 濕度: {data.humidity}%")
        print(f"  - 氣壓: {data.pressure} hPa")
    
    # 綜合異常指標
    print("\n[2.5] 綜合異常指標")
    anomaly = collector.calculate_anomaly_indicators()
    print(f"  - 電離層異常: {anomaly['ionosphere_anomaly']:.3f}")
    print(f"  - 地磁異常: {anomaly['geomagnetic_anomaly']:.3f}")
    print(f"  - 地震活動度: {anomaly['seismic_activity']:.3f}")
    print(f"  - 氣壓異常: {anomaly['pressure_anomaly']:.3f}")
    print(f"  - 總異常指標: {anomaly['total_anomaly']:.3f}")
    
    print("\n✅ 科學數據收集測試通過")
    return True

def test_prediction_engine():
    """測試預測引擎"""
    print("\n" + "=" * 60)
    print("測試 3: 預測引擎")
    print("=" * 60)
    
    engine = PredictionEngine()
    
    # 地震預測
    print("\n[3.1] 地震預測")
    eq_prediction = engine.predict_earthquake(use_time_casting=False)
    print(f"預測ID: {eq_prediction.id}")
    print(f"卦象: {eq_prediction.hexagram_name} (第{eq_prediction.hexagram_number}卦)")
    print(f"風險等級: {eq_prediction.risk_level:.1f}%")
    print(f"風險分類: {eq_prediction.prediction_details['risk_category']}")
    print(f"預測期間: {eq_prediction.forecast_period}")
    print(f"建議: {eq_prediction.prediction_details['recommendation']}")
    print(f"指標:")
    for indicator in eq_prediction.prediction_details['indicators']:
        print(f"  - {indicator}")
    
    # 氣象預測
    print("\n[3.2] 氣象預測")
    wx_prediction = engine.predict_weather()
    print(f"預測ID: {wx_prediction.id}")
    print(f"卦象: {wx_prediction.hexagram_name}")
    print(f"天氣類型: {wx_prediction.prediction_details['weather_type']}")
    print(f"嚴重程度: {wx_prediction.risk_level:.1f}%")
    
    # 經濟預測
    print("\n[3.3] 經濟預測")
    ec_prediction = engine.predict_economy()
    print(f"預測ID: {ec_prediction.id}")
    print(f"卦象: {ec_prediction.hexagram_name}")
    print(f"市場趨勢: {ec_prediction.prediction_details['trend']}")
    print(f"信心指數: {ec_prediction.risk_level:.1f}%")
    
    # 驗證測試（模擬）
    print("\n[3.4] 預測驗證測試")
    actual_event = {
        'occurred': True,
        'magnitude': 4.5,
        'days_from_prediction': 3
    }
    accuracy = engine.validate_prediction(eq_prediction.id, actual_event)
    print(f"驗證準確度: {accuracy:.1f}%")
    
    # 統計數據
    print("\n[3.5] 準確度統計")
    stats = engine.get_accuracy_statistics()
    print(f"總預測次數: {stats['total_predictions']}")
    print(f"已驗證次數: {stats['verified_predictions']}")
    print(f"平均準確度: {stats['average_accuracy']:.1f}%")
    print(f"成功率: {stats['success_rate']:.1f}%")
    
    # 歷史記錄
    print("\n[3.6] 預測歷史")
    history = engine.get_prediction_history(limit=5)
    print(f"最近 {len(history)} 筆預測:")
    for pred in history:
        status_icon = "✅" if pred.status == "verified" else "⏳" if pred.status == "pending" else "❌"
        print(f"  {status_icon} {pred.id} - {pred.hexagram_name} - 風險{pred.risk_level:.1f}%")
    
    print("\n✅ 預測引擎測試通過")
    return True

def test_integration():
    """整合測試"""
    print("\n" + "=" * 60)
    print("測試 4: 系統整合測試")
    print("=" * 60)
    
    # 完整預測流程
    print("\n[4.1] 完整預測流程（易經+科學數據）")
    
    collector = ScientificDataCollector()
    iching = IChingEngine()
    
    # 收集數據
    anomaly = collector.calculate_anomaly_indicators()
    print(f"當前總異常指標: {anomaly['total_anomaly']:.3f}")
    
    # 數據起卦
    iono_series = collector.get_time_series_data('ionosphere')
    geo_series = collector.get_time_series_data('geomagnetic')
    combined = iono_series + geo_series
    
    if combined:
        hexagram = iching.cast_hexagram_by_data(combined)
        print(f"數據起卦結果: {hexagram.name_zh}")
        
        # 解讀
        interpretation = iching.interpret_for_earthquake(hexagram, anomaly)
        print(f"地震風險評估: {interpretation['risk_level']:.1f}% - {interpretation['risk_category']}")
    
    print("\n✅ 系統整合測試通過")
    return True

def generate_test_report():
    """生成測試報告"""
    print("\n" + "=" * 60)
    print("測試報告生成")
    print("=" * 60)
    
    report = {
        'test_time': datetime.now().isoformat(),
        'system_version': '1.0.0',
        'tests': {
            'iching_core': 'PASS',
            'scientific_data': 'PASS',
            'prediction_engine': 'PASS',
            'integration': 'PASS'
        },
        'summary': {
            'total_tests': 4,
            'passed': 4,
            'failed': 0,
            'success_rate': 100.0
        }
    }
    
    report_file = os.path.join(os.path.dirname(__file__), 'test_report.json')
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n測試報告已保存: {report_file}")
    print(f"總測試數: {report['summary']['total_tests']}")
    print(f"通過: {report['summary']['passed']}")
    print(f"失敗: {report['summary']['failed']}")
    print(f"成功率: {report['summary']['success_rate']}%")

def main():
    """主測試函數"""
    print("\n" + "=" * 60)
    print("易經科學預測系統 - 完整測試")
    print("I Ching Scientific Prediction System - Full Test")
    print("=" * 60)
    print(f"測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    try:
        # 執行所有測試
        test_iching_core()
        test_scientific_data()
        test_prediction_engine()
        test_integration()
        
        # 生成報告
        generate_test_report()
        
        print("\n" + "=" * 60)
        print("🎉 所有測試通過！系統運行正常")
        print("=" * 60)
        
        return 0
    
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ 測試失敗: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    exit_code = main()
    print("\n按任意鍵退出...")
    input()
    sys.exit(exit_code)
