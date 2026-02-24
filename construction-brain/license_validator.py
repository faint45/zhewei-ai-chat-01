# -*- coding: utf-8 -*-
"""
築未科技 Construction Brain
license_validator.py

功能：
  - 產生本機 machine_id（CPU+主機板序號 hash）
  - 驗證授權碼（到期日 + 允許模組 + machine 綁定）
  - 提供模組開關（各功能先查授權再執行）

用法：
    # 查看本機 machine_id（提供給銷售人員產生授權碼）
    python license_validator.py --machine_id

    # 啟用授權碼
    python license_validator.py --activate YOUR-LICENSE-KEY

    # 查看目前授權狀態
    python license_validator.py --status

授權碼格式（base64 編碼 JSON，以私鑰簽章）：
    {
      "machine_id": "sha256前16碼",
      "sku": "starter|pro|enterprise",
      "modules": ["daily_report","safety","schedule","rag"],
      "expires": "2027-03-01",
      "issued_to": "公司名稱",
      "issued_at": "2026-03-01"
    }
"""

import base64
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

BASE_DIR = Path(os.environ.get("ZHEWEI_BASE", r"C:\ZheweiConstruction"))
LICENSE_FILE = BASE_DIR / "config" / "license.json"

# ─── SKU 模組對應表 ──────────────────────────────────────────
SKU_MODULES = {
    "starter": [
        "daily_report",   # 日報產生
        "safety",         # 工安缺失
        "line_receiver",  # LINE 接收
    ],
    "pro": [
        "daily_report",
        "safety",
        "line_receiver",
        "schedule",       # CPM 進度網圖 + S 曲線
        "rag",            # 施工知識庫問答
    ],
    "enterprise": [
        "daily_report",
        "safety",
        "line_receiver",
        "schedule",
        "rag",
        "multi_project",  # 多專案管理
        "api_export",     # API 匯出整合
    ],
}

SKU_NAMES = {
    "starter":    "入門版（Starter）",
    "pro":        "專業版（Pro）",
    "enterprise": "企業版（Enterprise）",
}

# ─── 公鑰（HMAC-SHA256，實際部署時換為 RSA 公鑰驗簽）─────────
# 此處用 HMAC 模擬簽章驗證，主力電腦上以同一把 secret 產生授權碼
# 正式產品：改用 RSA-2048，私鑰僅存於授權伺服器
_HMAC_SECRET = os.environ.get("ZHEWEI_LICENSE_SECRET", "zhewei-construction-brain-2026")


# ─── machine_id ──────────────────────────────────────────────

def _get_machine_id() -> str:
    """
    取得本機唯一識別碼（CPU序號 + 主機板序號 + 磁碟序號的 SHA256 前 16 碼）
    Windows only；其他平台以 hostname+mac 替代
    """
    parts = []

    if platform.system() == "Windows":
        try:
            cpu = subprocess.check_output(
                "wmic cpu get ProcessorId /value",
                shell=True, stderr=subprocess.DEVNULL
            ).decode(errors="ignore")
            parts.append(cpu.strip())
        except Exception:
            pass

        try:
            mb = subprocess.check_output(
                "wmic baseboard get SerialNumber /value",
                shell=True, stderr=subprocess.DEVNULL
            ).decode(errors="ignore")
            parts.append(mb.strip())
        except Exception:
            pass

        try:
            disk = subprocess.check_output(
                "wmic diskdrive get SerialNumber /value",
                shell=True, stderr=subprocess.DEVNULL
            ).decode(errors="ignore")
            parts.append(disk.strip().split("\n")[0])
        except Exception:
            pass

    if not parts:
        import socket
        import uuid
        parts.append(socket.gethostname())
        parts.append(str(uuid.getnode()))

    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ─── 授權碼產生（銷售工具，只在授權伺服器執行）─────────────────

def generate_license_key(
    machine_id: str,
    sku: str,
    issued_to: str,
    expires: str,
    extra_modules: list = None,
) -> str:
    """
    產生授權碼（base64 JSON + HMAC 簽章）
    僅供銷售後台使用

    Args:
        machine_id: 客戶回報的 machine_id
        sku: starter / pro / enterprise
        issued_to: 公司名稱
        expires: 到期日 YYYY-MM-DD
        extra_modules: 額外開放的模組（選填）

    Returns:
        授權碼字串（複製給客戶）
    """
    import hmac

    modules = list(SKU_MODULES.get(sku, []))
    if extra_modules:
        for m in extra_modules:
            if m not in modules:
                modules.append(m)

    payload = {
        "machine_id": machine_id,
        "sku": sku,
        "modules": modules,
        "expires": expires,
        "issued_to": issued_to,
        "issued_at": date.today().isoformat(),
    }
    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(payload, ensure_ascii=False).encode()
    ).decode()

    sig = hmac.new(
        _HMAC_SECRET.encode(),
        payload_b64.encode(),
        hashlib.sha256,
    ).hexdigest()[:32]

    return f"{payload_b64}.{sig}"


# ─── 授權碼驗證 ──────────────────────────────────────────────

def _verify_and_decode(license_key: str) -> dict:
    """
    驗證授權碼格式、HMAC 簽章、到期日、machine_id

    Returns:
        payload dict（驗證通過）

    Raises:
        ValueError: 驗證失敗（含原因）
    """
    import hmac

    parts = license_key.strip().split(".")
    if len(parts) != 2:
        raise ValueError("授權碼格式錯誤")

    payload_b64, sig = parts

    expected_sig = hmac.new(
        _HMAC_SECRET.encode(),
        payload_b64.encode(),
        hashlib.sha256,
    ).hexdigest()[:32]

    if not hmac.compare_digest(sig, expected_sig):
        raise ValueError("授權碼簽章不符（偽造或損毀）")

    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "==").decode())
    except Exception:
        raise ValueError("授權碼內容解碼失敗")

    expires = date.fromisoformat(payload["expires"])
    if date.today() > expires:
        raise ValueError(f"授權已到期（{expires}）")

    local_mid = _get_machine_id()
    if payload.get("machine_id") and payload["machine_id"] != local_mid:
        raise ValueError(
            f"授權碼與本機不符\n  授權碼 machine_id：{payload['machine_id']}\n  本機   machine_id：{local_mid}"
        )

    return payload


# ─── 啟用授權 ────────────────────────────────────────────────

def activate(license_key: str) -> bool:
    """
    啟用授權碼，寫入 license.json

    Returns:
        True = 成功
    """
    try:
        payload = _verify_and_decode(license_key)
    except ValueError as e:
        print(f"[license] ❌ 授權碼驗證失敗：{e}")
        return False

    LICENSE_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "license_key": license_key,
        "payload": payload,
        "activated_at": datetime.now().isoformat(),
        "machine_id": _get_machine_id(),
    }
    LICENSE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[license] ✅ 授權啟用成功！")
    print(f"  版本  ：{SKU_NAMES.get(payload['sku'], payload['sku'])}")
    print(f"  授權給：{payload.get('issued_to', '')}")
    print(f"  到期日：{payload['expires']}")
    print(f"  模組  ：{', '.join(payload['modules'])}")
    return True


# ─── 讀取授權狀態 ────────────────────────────────────────────

def _load_license() -> dict | None:
    if not LICENSE_FILE.exists():
        return None
    try:
        data = json.loads(LICENSE_FILE.read_text(encoding="utf-8"))
        _verify_and_decode(data["license_key"])
        return data
    except ValueError:
        return None
    except Exception:
        return None


# ─── 公開 API：模組授權檢查 ──────────────────────────────────

def require_module(module_name: str) -> bool:
    """
    檢查指定模組是否有授權
    在各功能程式的入口呼叫，未授權則印出提示並回傳 False

    Args:
        module_name: 模組名稱（如 "schedule", "rag", "daily_report"）

    Returns:
        True = 已授權，False = 無授權
    """
    data = _load_license()

    if data is None:
        print(f"[license] ⚠️  未找到有效授權，模組「{module_name}」無法使用")
        print(f"[license]    請聯絡築未科技取得授權碼，然後執行：")
        print(f"[license]    python license_validator.py --activate YOUR-KEY")
        return False

    payload = data["payload"]
    if module_name not in payload.get("modules", []):
        sku = payload.get("sku", "")
        print(f"[license] ⚠️  目前方案（{SKU_NAMES.get(sku, sku)}）不含「{module_name}」模組")
        print(f"[license]    升級至專業版或企業版可解鎖此功能")
        print(f"[license]    聯絡：contact@zhewei.tech")
        return False

    return True


def is_licensed(module_name: str) -> bool:
    """靜默版（不印訊息），供程式內部判斷用"""
    data = _load_license()
    if data is None:
        return False
    return module_name in data["payload"].get("modules", [])


# ─── 狀態顯示 ────────────────────────────────────────────────

def show_status():
    mid = _get_machine_id()
    print(f"\n{'='*55}")
    print(f"  築未科技 Construction Brain — 授權狀態")
    print(f"{'='*55}")
    print(f"  本機 machine_id：{mid}")
    print()

    data = _load_license()
    if data is None:
        print("  狀態：❌ 尚未授權")
        print()
        print("  取得授權步驟：")
        print(f"  1. 複製上方 machine_id 給築未科技業務")
        print(f"  2. 收到授權碼後執行：")
        print(f"     python license_validator.py --activate YOUR-KEY")
    else:
        payload = data["payload"]
        expires = date.fromisoformat(payload["expires"])
        days_left = (expires - date.today()).days
        status = "✅ 有效" if days_left > 0 else "❌ 已到期"
        warn = f"（⚠️ 剩餘 {days_left} 天，請盡快續約）" if 0 < days_left <= 30 else ""

        print(f"  狀態  ：{status} {warn}")
        print(f"  版本  ：{SKU_NAMES.get(payload['sku'], payload['sku'])}")
        print(f"  授權給：{payload.get('issued_to', '')}")
        print(f"  到期日：{payload['expires']}（剩 {days_left} 天）")
        print(f"  啟用於：{data.get('activated_at', '')[:10]}")
        print()
        print("  已開放模組：")
        for m in payload.get("modules", []):
            print(f"    ✓ {m}")

        locked = [m for sku_mods in SKU_MODULES.values()
                  for m in sku_mods
                  if m not in payload.get("modules", [])]
        locked = sorted(set(locked))
        if locked:
            print()
            print("  未開放模組（升級可解鎖）：")
            for m in locked:
                print(f"    ✗ {m}")

    print(f"{'='*55}\n")


# ─── CLI ─────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="築未科技 — 授權管理")
    parser.add_argument("--machine_id", action="store_true", help="顯示本機 machine_id")
    parser.add_argument("--activate", metavar="KEY", help="啟用授權碼")
    parser.add_argument("--status", action="store_true", help="查看授權狀態")
    parser.add_argument("--generate", action="store_true", help="[銷售後台] 產生授權碼")
    parser.add_argument("--mid",        help="[generate] 客戶 machine_id")
    parser.add_argument("--sku",        default="pro", choices=list(SKU_MODULES.keys()))
    parser.add_argument("--issued_to",  default="測試客戶")
    parser.add_argument("--expires",    default="2027-03-01")
    args = parser.parse_args()

    if args.machine_id:
        mid = _get_machine_id()
        print(f"\n  本機 machine_id：{mid}")
        print(f"  請複製此代碼提供給築未科技業務以取得授權碼\n")

    elif args.activate:
        activate(args.activate)

    elif args.generate:
        if not args.mid:
            print("請提供 --mid（客戶的 machine_id）")
            sys.exit(1)
        key = generate_license_key(
            machine_id=args.mid,
            sku=args.sku,
            issued_to=args.issued_to,
            expires=args.expires,
        )
        print(f"\n授權碼（複製給客戶）：\n{key}\n")

    else:
        show_status()
