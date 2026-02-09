"""
築未科技大腦 - 遠端連線測試
確認 Brain Bridge 是否在本機與區域網路可連，並印出遠端登入網址。
"""
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

PORT = 5100
LOCAL = f"http://127.0.0.1:{PORT}"
TIMEOUT = 3


def main():
    print()
    print("  ========================================")
    print("  築未科技大腦 - 遠端連線測試")
    print("  ========================================")
    print()

    # 1. 本機健康檢查
    try:
        import urllib.request
        req = urllib.request.Request(f"{LOCAL}/health", method="GET")
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            data = r.read().decode("utf-8", errors="replace")
            print(f"  [OK] 本機服務正常: {LOCAL}/health")
    except Exception as e:
        print(f"  [X] 本機連線失敗: {LOCAL}")
        print(f"      請先執行 run-brain-bridge-only.bat 啟動 Brain Bridge")
        print(f"      錯誤: {e}")
        print()
        return 1

    # 2. 取得遠端資訊（本機 IP、登入網址）
    try:
        import urllib.request
        req = urllib.request.Request(f"{LOCAL}/remote-info", method="GET")
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            import json
            info = json.loads(r.read().decode("utf-8", errors="replace"))
    except Exception as e:
        print(f"  [!] 無法取得遠端資訊: {e}")
        info = {"host_ips": [], "port": PORT, "login_url": f"http://127.0.0.1:{PORT}/login"}
    else:
        ips = info.get("host_ips", [])
        login_url = info.get("login_url", f"http://127.0.0.1:{PORT}/login")
        print(f"  [OK] 遠端資訊:")
        print(f"       本機登入: http://127.0.0.1:{PORT}/login")
        if ips:
            for ip in ips:
                if ip != "127.0.0.1":
                    print(f"       遠端登入: http://{ip}:{PORT}/login")
            print()
            print("  從同一 WiFi/網路的手機或另一台電腦，開啟上述「遠端登入」網址即可測試。")
        else:
            print(f"       登入網址: {login_url}")
    print()
    print("  若遠端無法連線，請檢查:")
    print("    - 本機防火牆是否允許 port 5100 入站")
    print("    - 遠端裝置是否與本機在同一網路")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
