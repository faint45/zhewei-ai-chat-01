#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
築未科技全系統測試腳本 (簡化版)
測試所有組件的可用性和功能
"""

import requests
import time
import sys
import os
import socket

def test_endpoint(name, url, timeout=5):
    """測試單個端點"""
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code == 200, response.status_code
    except requests.exceptions.ConnectionError:
        return False, "Connection Failed"
    except requests.exceptions.Timeout:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)[:50]

def test_service_port(port):
    """測試服務端口是否開放"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result == 0
    except:
        return False

def main():
    """主測試函數"""
    print("\n" + "="*60)
    print(" " * 15 + "築未科技全系統測試")
    print("="*60 + "\n")

    # 測試端口
    print("[1] 檢查服務端口...")
    
    port_8000 = test_service_port(8000)
    port_8005 = test_service_port(8005)
    
    if port_8000:
        print("    [OK] 端口 8000 (網站服務器) 已啟動")
    else:
        print("    [FAIL] 端口 8000 (網站服務器) 未啟動")
    
    if port_8005:
        print("    [OK] 端口 8005 (遠程控制服務器) 已啟動")
    else:
        print("    [FAIL] 端口 8005 (遠程控制服務器) 未啟動")

    # 測試網站端點
    print("\n[2] 測試網站服務器端點...")
    
    if port_8000:
        endpoints = [
            ("網站首頁", "http://localhost:8000/"),
            ("AI對話頁面", "http://localhost:8000/chat"),
            ("管理後台", "http://localhost:8000/admin"),
            ("聯繫我們", "http://localhost:8000/contact"),
            ("健康檢查", "http://localhost:8000/health"),
            ("網站統計API", "http://localhost:8000/api/stats"),
        ]
        
        for name, url in endpoints:
            success, status = test_endpoint(name, url)
            if success:
                print(f"    [OK] {name} - HTTP {status}")
            else:
                print(f"    [FAIL] {name} - {status}")
    else:
        print("    [SKIP] 網站服務器未啟動")

    # 測試遠程控制端點
    print("\n[3] 測試遠程控制服務器端點...")
    
    if port_8005:
        endpoints = [
            ("遠程控制狀態", "http://localhost:8005/api/status"),
            ("遠程控制首頁", "http://localhost:8005/"),
        ]
        
        for name, url in endpoints:
            success, status = test_endpoint(name, url)
            if success:
                print(f"    [OK] {name} - HTTP {status}")
            else:
                print(f"    [FAIL] {name} - {status}")
    else:
        print("    [SKIP] 遠程控制服務器未啟動")

    # 檢查文件
    print("\n[4] 檢查系統文件...")
    
    files = [
        ("website_server.py", "網站服務器"),
        ("remote_control_server.py", "遠程控制服務器"),
        ("ai_service.py", "AI 服務"),
        ("config_ai.py", "AI 配置"),
        ("website.db", "資料庫"),
        ("static/css/admin.css", "管理後台樣式"),
    ]
    
    for filepath, desc in files:
        if os.path.exists(filepath):
            print(f"    [OK] {desc} - {filepath}")
        else:
            print(f"    [FAIL] {desc} - {filepath} 不存在")

    # 檢查依賴
    print("\n[5] 檢查依賴套件...")
    
    packages = [
        ("flask", "Flask"),
        ("requests", "Requests"),
    ]
    
    for module, name in packages:
        try:
            __import__(module)
            print(f"    [OK] {name} 已安裝")
        except ImportError:
            print(f"    [FAIL] {name} 未安裝")

    # 總結
    print("\n" + "="*60)
    print(" " * 20 + "測試完成")
    print("="*60 + "\n")
    
    print("使用說明:")
    print("1. 啟動所有服務: 運行 start_all_services.bat")
    print("2. 訪問網站: http://localhost:8000")
    print("3. 訪問管理後台: http://localhost:8000/admin")
    print("4. 訪問AI對話: http://localhost:8000/chat")
    print("5. 訪問遠程控制: http://localhost:8005")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n測試已中斷")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
