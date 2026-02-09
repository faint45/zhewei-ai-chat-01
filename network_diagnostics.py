# -*- coding: utf-8 -*-
"""
築未科技 — 一鍵網路診斷工具
驗證築未大腦之內外部連線：網際網路、Tailscale、Port 8000、Z 槽、E 槽。
輸出為 Markdown 相容清單，並計算延遲 $L_{total}$。
"""
import os
import socket
import sys
import time
from pathlib import Path

# 配置（可透過環境變數覆寫）
TAILSCALE_PREFIX = "100.116."
PORT_BRAIN = int(os.environ.get("BRAIN_WS_PORT", "8000"))
Z_PATH = Path(os.environ.get("ZHEWEI_MEMORY_ROOT", "Z:/Zhewei_Brain"))
E_PATH = Path(os.environ.get("ZHEWEI_ARCHIVE_ROOT", "E:/Zhewei_Archive"))
INTERNET_TEST_HOST = "8.8.8.8"
INTERNET_TEST_PORT = 53
TIMEOUT = 5

results = []
latencies = []


def _ms(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000, 1)


def check_internet() -> bool:
    """對外網路：連線 8.8.8.8"""
    t0 = time.perf_counter()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(TIMEOUT)
        s.connect((INTERNET_TEST_HOST, INTERNET_TEST_PORT))
        s.close()
        ms = _ms(t0)
        latencies.append(ms)
        results.append(("網際網路 (8.8.8.8)", True, f"暢通，延遲 {ms} ms"))
        return True
    except (socket.timeout, OSError):
        results.append(("網際網路 (8.8.8.8)", False, "無法連線，請檢查對外網路"))
        return False


def check_tailscale() -> bool:
    """本機出站 IP 是否為 100.116.x.x（Tailscale 網段）"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(1)
            s.connect((INTERNET_TEST_HOST, INTERNET_TEST_PORT))
            ip = s.getsockname()[0]
        ok = ip.startswith(TAILSCALE_PREFIX)
        results.append(("Tailscale (100.116.x.x)", ok, f"本機 IP: {ip}" if ok else f"本機 IP: {ip}，非 100.116 網段"))
        return ok
    except Exception:
        try:
            ip = socket.gethostbyname(socket.gethostname())
            ok = ip.startswith(TAILSCALE_PREFIX)
            results.append(("Tailscale (100.116.x.x)", ok, f"本機 IP: {ip}" if ok else f"本機 IP: {ip}，非 100.116 網段"))
            return ok
        except Exception:
            results.append(("Tailscale (100.116.x.x)", False, "無法取得本機 IP"))
            return False


def check_port_8000() -> bool:
    """localhost:8000 是否監聽"""
    t0 = time.perf_counter()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(("127.0.0.1", PORT_BRAIN))
        s.close()
        ms = _ms(t0)
        latencies.append(ms)
        results.append((f"服務埠 Port {PORT_BRAIN}", True, f"已啟動，延遲 {ms} ms"))
        return True
    except (socket.timeout, OSError):
        results.append((f"服務埠 Port {PORT_BRAIN}", False, "未開啟，請啟動 brain_server.py"))
        return False


def check_z_drive() -> bool:
    """Z:/Zhewei_Brain 讀寫延遲"""
    t0 = time.perf_counter()
    if not Z_PATH.exists():
        results.append(("磁碟 Z 槽 (Zhewei_Brain)", False, "路徑不存在或未掛載"))
        return False
    try:
        test_file = Z_PATH / ".network_diag_tmp"
        test_file.write_text("ok", encoding="utf-8")
        test_file.read_text(encoding="utf-8")
        test_file.unlink(missing_ok=True)
        ms = _ms(t0)
        latencies.append(ms)
        results.append(("磁碟 Z 槽 (Zhewei_Brain)", True, f"讀寫正常，延遲 {ms} ms"))
        return True
    except Exception as e:
        results.append(("磁碟 Z 槽 (Zhewei_Brain)", False, f"讀寫異常: {e}"))
        return False


def check_e_drive() -> bool:
    """E:/Zhewei_Archive 是否已插入"""
    if not E_PATH.exists():
        results.append(("磁碟 E 槽 (Zhewei_Archive)", False, "路徑不存在，請確認外接硬碟已插入"))
        return False
    results.append(("磁碟 E 槽 (Zhewei_Archive)", True, "已掛載"))
    return True


def run() -> int:
    print("## 築未大腦 — 網路診斷結果\n")
    check_internet()
    check_tailscale()
    check_port_8000()
    check_z_drive()
    check_e_drive()

    for name, ok, msg in results:
        status = "✅" if ok else "❌"
        print(f"- **{name}**: {status} {msg}")

    L_total = sum(latencies) if latencies else 0
    print(f"\n**延遲總計** $L_{{total}} = {L_total}$ ms\n")
    if not all(r[1] for r in results):
        print("> 部分項目未通過，請依提示修正後再執行診斷。")
        return 1
    print("> 所有連線項目通過，築未大腦網路狀態正常。")
    return 0


if __name__ == "__main__":
    sys.exit(run())
