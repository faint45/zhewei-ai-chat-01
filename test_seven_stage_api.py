#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
七階段系統 HTTP API 測試
"""

import requests
import json

API_BASE = "http://localhost:8006"


def test_health():
    """測試健康檢查"""
    print("\n[測試 1] 健康檢查")
    print("-" * 50)

    response = requests.get(f"{API_BASE}/health")

    if response.status_code == 200:
        data = response.json()
        print("狀態:", data["status"])
        print("系統:", data["system"])
        print("工作區:", data["workspace"])
        print("\n角色狀態:")
        for role, name in data["roles"].items():
            print(f"  - {role}: {name}")
        return True
    else:
        print("失敗:", response.status_code)
        return False


def test_execute_task():
    """測試執行任務"""
    print("\n[測試 2] 執行任務")
    print("-" * 50)

    payload = {
        "input": "幫我創建一個簡單的計算器",
        "priority": "high"
    }

    print(f"請求: {json.dumps(payload, ensure_ascii=False)}")

    response = requests.post(
        f"{API_BASE}/execute",
        json=payload,
        timeout=120
    )

    if response.status_code == 200:
        data = response.json()
        print("\n任務 ID:", data["task_id"])
        print("狀態:", data["status"])
        print("創建時間:", data["created_at"])

        if "result" in data and "final_report" in data["result"]:
            print("\n最終報告:")
            print("-" * 50)
            print(data["result"]["final_report"])

        return True
    else:
        print("失敗:", response.status_code)
        print(response.text)
        return False


def test_get_status():
    """測試獲取狀態"""
    print("\n[測試 3] 獲取系統狀態")
    print("-" * 50)

    response = requests.get(f"{API_BASE}/status")

    if response.status_code == 200:
        data = response.json()
        print("系統:", data["system"])
        print("工作區:", data["workspace"])
        print("當前階段:", data["current_stage"])
        print("總任務數:", data["total_tasks"])
        print("已完成:", data["completed_tasks"])

        print("\n角色狀態:")
        for role, status in data["roles_status"].items():
            print(f"  - {role}: {status}")

        return True
    else:
        print("失敗:", response.status_code)
        return False


def test_api_docs():
    """測試 API 文檔"""
    print("\n[測試 4] API 文檔")
    print("-" * 50)

    response = requests.get(f"{API_BASE}/api-docs")

    if response.status_code == 200:
        data = response.json()
        print("可用端點:")
        for endpoint, description in data["endpoints"].items():
            print(f"  {endpoint}: {description}")

        print("\n示例:")
        example = data["examples"]["execute_task"]
        print(f"  {example['method']} {example['url']}")
        print(f"  Body: {json.dumps(example['body'], ensure_ascii=False)}")

        return True
    else:
        print("失敗:", response.status_code)
        return False


def main():
    """運行所有測試"""
    print("=" * 60)
    print("七階段系統 HTTP API 測試")
    print("=" * 60)

    print(f"API 地址: {API_BASE}")

    tests = [
        ("健康檢查", test_health),
        ("執行任務", test_execute_task),
        ("獲取狀態", test_get_status),
        ("API 文檔", test_api_docs)
    ]

    results = []

    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, "通過" if result else "失敗"))
        except Exception as e:
            print(f"\n錯誤: {e}")
            results.append((name, f"錯誤: {e}"))

    # 總結
    print("\n" + "=" * 60)
    print("測試總結")
    print("=" * 60)

    for name, result in results:
        status = "[OK]" if "通過" in result else "[FAIL]"
        print(f"{status} {name}: {result}")

    passed = len([r for r in results if "通過" in r[1]])
    total = len(results)

    print(f"\n通過: {passed}/{total}")

    if passed == total:
        print("\n所有測試通過！")
    else:
        print(f"\n{total - passed} 個測試失敗")


if __name__ == "__main__":
    main()
