#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zhewei Brain - System Health Check and Version Report
Check system health and report current version
"""
import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Version Information
VERSION = "1.0.0"
BUILD_DATE = "2026-02-05"
CODE_NAME = "Zhewei Brain"

def check_component(name, check_func):
    """Check component and return result"""
    try:
        result = check_func()
        status = "[OK]" if result else "[FAIL]"
        print(f"{status} {name}")
        return {"name": name, "status": "success" if result else "fail", "details": "Normal" if result else "Abnormal"}
    except Exception as e:
        print(f"[ERROR] {name}: {str(e)}")
        return {"name": name, "status": "error", "details": str(e)}

def check_z_drive():
    """Check Z drive (Google Drive)"""
    return os.path.exists("Z:/")

def check_python_env():
    """Check Python environment"""
    return True  # Running this script means Python exists

def check_brain_server():
    """Check brain_server.py"""
    return os.path.exists("brain_server.py")

def check_ai_service():
    """Check ai_service.py"""
    return os.path.exists("ai_service.py")

def check_website_server():
    """Check website_server.py"""
    return os.path.exists("website_server.py")

def check_monitoring_service():
    """Check monitoring_dashboard.py"""
    return os.path.exists("monitoring_dashboard.py")

def check_venv():
    """Check virtual environment"""
    venv_path = Path("venv/Scripts/python.exe")
    return venv_path.exists()

def check_config_files():
    """Check config files"""
    configs = [".env", "cloudbase.json", "config_ai.py"]
    return all(os.path.exists(c) for c in configs)

def check_database():
    """Check database files"""
    db_files = ["website.db", "api_monitoring.db"]
    return all(os.path.exists(f) for f in db_files)

def check_directories():
    """Check required directories"""
    dirs = ["static", "templates"]
    return all(os.path.exists(d) for d in dirs)

def calculate_health_score(results):
    """Calculate system health score"""
    success_count = sum(1 for r in results if r["status"] == "success")
    total_count = len(results)
    score = (success_count / total_count * 100) if total_count > 0 else 0
    return round(score, 2)

def generate_report(results):
    """Generate check report"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "version": VERSION,
        "build_date": BUILD_DATE,
        "code_name": CODE_NAME,
        "health_score": calculate_health_score(results),
        "components": results,
        "summary": {
            "total": len(results),
            "success": sum(1 for r in results if r["status"] == "success"),
            "fail": sum(1 for r in results if r["status"] == "fail"),
            "error": sum(1 for r in results if r["status"] == "error"),
        }
    }
    return report

def main():
    """Main function"""
    print("="*60)
    print(f"{CODE_NAME} - System Health Report")
    print("="*60)
    print(f"Version: {VERSION}")
    print(f"Build Date: {BUILD_DATE}")
    print(f"Check Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Execute all checks
    checks = [
        ("Z Drive (Google Drive)", check_z_drive),
        ("Python Environment", check_python_env),
        ("Virtual Environment", check_venv),
        ("brain_server.py", check_brain_server),
        ("ai_service.py", check_ai_service),
        ("website_server.py", check_website_server),
        ("monitoring_dashboard.py", check_monitoring_service),
        ("Config Files", check_config_files),
        ("Database Files", check_database),
        ("Required Directories", check_directories),
    ]

    results = []
    for name, check_func in checks:
        result = check_component(name, check_func)
        results.append(result)

    # Generate report
    report = generate_report(results)
    health_score = report["health_score"]
    summary = report["summary"]

    print()
    print("="*60)
    print("Summary")
    print("="*60)
    print(f"System Health Score: {health_score}%")
    print(f"Passed Items: {summary['success']}/{summary['total']}")
    print(f"Failed Items: {summary['fail']}/{summary['total']}")
    print(f"Error Items: {summary['error']}/{summary['total']}")

    # Health score evaluation
    print()
    if health_score >= 90:
        print("[Excellent] System is in good condition")
    elif health_score >= 70:
        print("[Good] System is basically normal")
    elif health_score >= 50:
        print("[Fair] Some components are abnormal")
    else:
        print("[Poor] System condition is poor, needs repair")

    # Show failed items
    failed_items = [r for r in results if r["status"] != "success"]
    if failed_items:
        print()
        print("="*60)
        print("Items Needing Repair")
        print("="*60)
        for item in failed_items:
            print(f"  * {item['name']}: {item['details']}")

    # Save report
    print()
    print("="*60)
    print("Report Generated")
    print("="*60)

    report_file = Path("system_health_report.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Report saved to: {report_file.absolute()}")

    # Return exit code
    return 0 if health_score >= 70 else 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[INFO] Check cancelled")
        sys.exit(130)
    except Exception as e:
        print(f"[ERROR] Error during execution: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
