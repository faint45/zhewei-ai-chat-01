#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
築未科技全系統測試腳本
測試所有組件的可用性和功能
"""

import requests
import time
import sys
from typing import Dict, List, Tuple

# 設置控制台編碼
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 顏色輸出
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(title: str):
    """打印標題"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}")
    print(f"{title:^60}")
    print(f"{'='*60}{Colors.RESET}\n")

def print_success(msg: str):
    """打印成功消息"""
    print(f"{Colors.GREEN}✅ {msg}{Colors.RESET}")

def print_error(msg: str):
    """打印錯誤消息"""
    print(f"{Colors.RED}❌ {msg}{Colors.RESET}")

def print_warning(msg: str):
    """打印警告消息"""
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.RESET}")

def test_endpoint(name: str, url: str, timeout: int = 5) -> Tuple[bool, str]:
    """測試單個端點"""
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            return True, f"狀態碼: {response.status_code}"
        else:
            return False, f"狀態碼: {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "連接失敗 - 服務未啟動"
    except requests.exceptions.Timeout:
        return False, "請求超時"
    except Exception as e:
        return False, f"錯誤: {str(e)[:50]}"

def test_service_port(port: int, name: str) -> bool:
    """測試服務端口是否開放"""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result == 0
    except:
        return False

def test_website_server():
    """測試網站服務器 (端口 8000)"""
    print_header("測試網站服務器 (端口 8000)")

    if not test_service_port(8000, "網站服務器"):
        print_error("網站服務器未啟動")
        print("請先運行: python website_server.py")
        return False

    print_success("網站服務器已啟動")

    endpoints = [
        ("網站首頁", "http://localhost:8000/"),
        ("AI對話頁面", "http://localhost:8000/chat"),
        ("管理後台登入", "http://localhost:8000/admin/login"),
        ("健康檢查", "http://localhost:8000/health"),
        ("網站統計API", "http://localhost:8000/api/stats"),
    ]

    all_passed = True
    for name, url in endpoints:
        success, msg = test_endpoint(name, url)
        if success:
            print_success(f"{name}: {url} ({msg})")
        else:
            print_error(f"{name}: {url} ({msg})")
            all_passed = False

    return all_passed

def test_remote_control_server():
    """測試遠程控制服務器 (端口 8005)"""
    print_header("測試遠程控制服務器 (端口 8005)")

    if not test_service_port(8005, "遠程控制服務器"):
        print_error("遠程控制服務器未啟動")
        print("請先運行: python remote_control_server.py")
        return False

    print_success("遠程控制服務器已啟動")

    endpoints = [
        ("遠程控制狀態", "http://localhost:8005/api/status"),
        ("遠程控制首頁", "http://localhost:8005/"),
    ]

    all_passed = True
    for name, url in endpoints:
        success, msg = test_endpoint(name, url)
        if success:
            print_success(f"{name}: {url} ({msg})")
        else:
            print_error(f"{name}: {url} ({msg})")
            all_passed = False

    return all_passed

def test_ai_service():
    """測試 AI 服務"""
    print_header("測試 AI 服務")

    try:
        import config_ai
        print_success("AI 配置模組載入成功")

        # 檢查配置
        if hasattr(config_ai, 'OLLAMA_API_URL'):
            print(f"📍 Ollama API 地址: {config_ai.OLLAMA_API_URL}")
        if hasattr(config_ai, 'AI_MODEL'):
            print(f"🤖 AI 模型: {config_ai.AI_MODEL}")
        if hasattr(config_ai, 'DEFAULT_MODEL'):
            print(f"🤖 默認模型: {config_ai.DEFAULT_MODEL}")

        return True
    except Exception as e:
        print_error(f"AI 配置模組載入失敗: {str(e)}")
        return False

def test_database():
    """測試資料庫"""
    print_header("測試資料庫")

    import os
    db_path = "website.db"

    if os.path.exists(db_path):
        print_success(f"資料庫文件存在: {db_path}")
        file_size = os.path.getsize(db_path)
        print(f"📊 資料庫大小: {file_size:,} 位元組")
        return True
    else:
        print_warning(f"資料庫文件不存在: {db_path}")
        print("資料庫將在第一次啟動時自動創建")
        return True  # 不算錯誤

def test_static_files():
    """測試靜態文件"""
    print_header("測試靜態文件")

    import os

    required_dirs = [
        ("templates", "模板目錄"),
        ("static", "靜態文件目錄"),
        ("static/css", "CSS 樣式目錄"),
    ]

    all_exist = True
    for dir_path, description in required_dirs:
        if os.path.exists(dir_path):
            print_success(f"{description} 存在")
        else:
            print_error(f"{description} 不存在: {dir_path}")
            all_exist = False

    # 檢查關鍵文件
    required_files = [
        ("website_server.py", "網站服務器"),
        ("remote_control_server.py", "遠程控制服務器"),
        ("ai_service.py", "AI 服務"),
        ("config_ai.py", "AI 配置"),
    ]

    for file_path, description in required_files:
        if os.path.exists(file_path):
            print_success(f"{description} 存在")
        else:
            print_error(f"{description} 不存在: {file_path}")
            all_exist = False

    return all_exist

def check_dependencies():
    """檢查依賴套件"""
    print_header("檢查依賴套件")

    required_packages = [
        "flask",
        "requests",
    ]

    optional_packages = [
        "openai",
        "python-dotenv",
    ]

    all_installed = True
    for package in required_packages:
        try:
            __import__(package)
            print_success(f"{package} 已安裝")
        except ImportError:
            print_error(f"{package} 未安裝")
            all_installed = False

    for package in optional_packages:
        try:
            __import__(package)
            print_success(f"{package} 已安裝 (可選)")
        except ImportError:
            print_warning(f"{package} 未安裝 (可選)")

    return all_installed

def main():
    """主測試函數"""
    print(f"\n{Colors.BOLD}{Colors.GREEN}")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║       築未科技全系統測試工具                                ║")
    print("║       Zhewei Tech System Test Tool                        ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}\n")

    # 檢查依賴
    deps_ok = check_dependencies()

    # 測試靜態文件
    files_ok = test_static_files()

    # 測試 AI 服務配置
    ai_ok = test_ai_service()

    # 測試資料庫
    db_ok = test_database()

    # 測試網站服務器
    website_ok = test_website_server()

    # 測試遠程控制服務器
    remote_ok = test_remote_control_server()

    # 總結
    print_header("測試總結")

    results = [
        ("依賴套件", deps_ok),
        ("靜態文件", files_ok),
        ("AI 服務配置", ai_ok),
        ("資料庫", db_ok),
        ("網站服務器", website_ok),
        ("遠程控制服務器", remote_ok),
    ]

    passed = sum(1 for _, ok in results if ok)
    total = len(results)

    for name, ok in results:
        if ok:
            print_success(f"{name}: ✅")
        else:
            print_error(f"{name}: ❌")

    print(f"\n{Colors.BOLD}總計: {passed}/{total} 通過{Colors.RESET}")

    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 所有測試通過！系統準備就緒。{Colors.RESET}")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}⚠️  部分測試失敗，請檢查上述錯誤。{Colors.RESET}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
