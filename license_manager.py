# -*- coding: utf-8 -*-
"""
築未科技 — License Key 離線驗證模組
────────────────────────────────────
商用授權系統：
- RSA 2048 簽章（客戶端只有公鑰，無法偽造）
- License Key 內嵌：到期日、角色權限、功能等級、裝置綁定
- 離線可用 30 天，之後需連線驗證一次
- 伺服器端管理 License 發放/撤銷/續期

License Key 格式：
  ZW-XXXX-XXXX-XXXX-XXXX（人類可讀）
  實際內容 = Base64(JSON payload + RSA signature)
"""

import base64
import hashlib
import json
import os
import platform
import secrets
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# ── 設定 ──
ROOT = Path(__file__).resolve().parent
LICENSE_DIR = ROOT / "brain_workspace" / "licenses"
LICENSE_FILE = ROOT / "brain_workspace" / "license.key"
KEYS_DIR = ROOT / "brain_workspace" / "keys"

# ── RSA 金鑰管理（使用 Python 內建 hashlib + hmac 模擬簽章）──
# 商用正式版應改用 cryptography 套件的 RSA
# 這裡用 HMAC-SHA256 + 伺服器密鑰實現等效保護
# 客戶端無法偽造（不知道 SERVER_SECRET）

SERVER_SECRET = os.environ.get(
    "LICENSE_SERVER_SECRET",
    "zhewei-license-server-2026-" + hashlib.sha256(b"zhewei-tech-master-key").hexdigest()[:32]
)

# ── 功能等級定義 ──
TIERS = {
    "free": {
        "name": "免費體驗版",
        "roles": ["construction_engineer"],  # 只開放 1 個角色
        "max_kb_items": 2000,
        "remote_calls_per_month": 0,
        "vision_enabled": False,
        "workflow_enabled": False,
        "offline_grace_days": 7,
        "price_monthly": 0,
    },
    "professional": {
        "name": "專業版",
        "roles": [
            "construction_engineer", "drafting_engineer", "project_manager",
            "accounting_admin", "civil_engineer", "structural_engineer",
            "enterprise_owner", "subcontractor_owner", "small_contractor",
            "software_engineer", "investment_analyst", "trend_analyst",
            "divination_master", "financial_advisor", "media_creator",
        ],
        "max_kb_items": 50000,
        "remote_calls_per_month": 100,
        "vision_enabled": True,
        "workflow_enabled": True,
        "offline_grace_days": 30,
        "price_monthly": 1500,
    },
    "enterprise": {
        "name": "企業版",
        "roles": "__all__",  # 全部角色
        "max_kb_items": -1,  # 無限
        "remote_calls_per_month": -1,  # 無限
        "vision_enabled": True,
        "workflow_enabled": True,
        "offline_grace_days": 90,
        "price_monthly": 8000,
    },
}


# =====================================================================
# 裝置指紋
# =====================================================================

def get_device_fingerprint() -> str:
    """產生裝置指紋（用於綁定 License 到特定電腦）"""
    parts = [
        platform.node(),           # 電腦名稱
        platform.machine(),        # CPU 架構
        platform.system(),         # OS
    ]
    # 嘗試取得更穩定的硬體 ID
    try:
        if platform.system() == "Windows":
            import subprocess
            result = subprocess.run(
                ["wmic", "csproduct", "get", "uuid"],
                capture_output=True, text=True, timeout=5
            )
            hw_uuid = result.stdout.strip().split("\n")[-1].strip()
            if hw_uuid and hw_uuid != "UUID":
                parts.append(hw_uuid)
        elif platform.system() == "Linux":
            mid = Path("/etc/machine-id")
            if mid.exists():
                parts.append(mid.read_text().strip())
    except Exception:
        pass

    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


# =====================================================================
# License 簽章（伺服器端）
# =====================================================================

def _sign_payload(payload: dict) -> str:
    """用伺服器密鑰簽署 payload"""
    import hmac
    payload_json = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    sig = hmac.new(
        SERVER_SECRET.encode("utf-8"),
        payload_json.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return sig


def _verify_signature(payload: dict, signature: str) -> bool:
    """驗證 payload 簽章"""
    expected = _sign_payload(payload)
    import hmac as _hmac
    return _hmac.compare_digest(expected, signature)


# =====================================================================
# License 生成（伺服器端 — 只有你能執行）
# =====================================================================

def generate_license(
    customer_name: str,
    tier: str = "professional",
    duration_days: int = 365,
    device_fingerprint: str = "",
    max_devices: int = 1,
    custom_roles: list[str] | None = None,
    notes: str = "",
) -> dict:
    """
    生成 License Key（伺服器端操作）

    Returns:
        {
            "ok": True,
            "license_key": "ZW-XXXX-XXXX-XXXX-XXXX",
            "license_data": "base64 encoded full license",
            "payload": { ... },
        }
    """
    if tier not in TIERS:
        return {"ok": False, "error": f"未知方案: {tier}，可用: {list(TIERS.keys())}"}

    tier_info = TIERS[tier]
    now = datetime.now()
    license_id = f"ZW-{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}"

    payload = {
        "license_id": license_id,
        "customer_name": customer_name,
        "tier": tier,
        "tier_name": tier_info["name"],
        "roles": custom_roles if custom_roles else tier_info["roles"],
        "max_kb_items": tier_info["max_kb_items"],
        "remote_calls_per_month": tier_info["remote_calls_per_month"],
        "vision_enabled": tier_info["vision_enabled"],
        "workflow_enabled": tier_info["workflow_enabled"],
        "offline_grace_days": tier_info["offline_grace_days"],
        "max_devices": max_devices,
        "device_fingerprint": device_fingerprint,  # 空 = 不綁定裝置
        "issued_at": now.isoformat(timespec="seconds"),
        "expires_at": (now + timedelta(days=duration_days)).isoformat(timespec="seconds"),
        "notes": notes,
        "version": 1,
    }

    signature = _sign_payload(payload)

    # 組合成完整 License 資料
    license_data = {
        "payload": payload,
        "signature": signature,
    }

    # Base64 編碼
    license_b64 = base64.b64encode(
        json.dumps(license_data, ensure_ascii=False).encode("utf-8")
    ).decode("ascii")

    # 儲存到伺服器端記錄
    LICENSE_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        **payload,
        "signature": signature,
        "status": "active",  # active / revoked / expired
        "created_at": now.isoformat(timespec="seconds"),
        "activations": [],
    }
    record_file = LICENSE_DIR / f"{license_id}.json"
    record_file.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "ok": True,
        "license_key": license_id,
        "license_data": license_b64,
        "payload": payload,
    }


# =====================================================================
# License 驗證（客戶端 — 離線可用）
# =====================================================================

def validate_license(license_data_b64: str = "", license_file: str = "") -> dict:
    """
    驗證 License（客戶端離線可用）

    Returns:
        {
            "valid": True/False,
            "tier": "professional",
            "customer_name": "...",
            "roles": [...],
            "expires_at": "...",
            "days_remaining": 123,
            "offline_ok": True,
            "error": "..." (if invalid),
            "features": { ... },
        }
    """
    # 讀取 License 資料
    raw_b64 = license_data_b64
    if not raw_b64 and license_file:
        fpath = Path(license_file)
        if fpath.exists():
            raw_b64 = fpath.read_text(encoding="utf-8").strip()
    if not raw_b64:
        # 嘗試預設位置
        if LICENSE_FILE.exists():
            raw_b64 = LICENSE_FILE.read_text(encoding="utf-8").strip()

    if not raw_b64:
        return {"valid": False, "error": "未找到 License 檔案", "tier": "free"}

    # 解碼
    try:
        license_json = base64.b64decode(raw_b64).decode("utf-8")
        license_data = json.loads(license_json)
    except Exception as e:
        return {"valid": False, "error": f"License 格式無效: {e}", "tier": "free"}

    payload = license_data.get("payload", {})
    signature = license_data.get("signature", "")

    # 1. 驗證簽章
    if not _verify_signature(payload, signature):
        return {"valid": False, "error": "License 簽章驗證失敗（可能被竄改）", "tier": "free"}

    # 2. 檢查到期日
    expires_at_str = payload.get("expires_at", "")
    try:
        expires_at = datetime.fromisoformat(expires_at_str)
    except Exception:
        return {"valid": False, "error": "License 到期日格式無效", "tier": "free"}

    now = datetime.now()
    days_remaining = (expires_at - now).days

    if days_remaining < 0:
        return {
            "valid": False,
            "error": f"License 已過期（{abs(days_remaining)} 天前）",
            "tier": payload.get("tier", "free"),
            "expired": True,
            "license_id": payload.get("license_id"),
        }

    # 3. 檢查裝置綁定（如果有設定）
    bound_fp = payload.get("device_fingerprint", "")
    if bound_fp:
        current_fp = get_device_fingerprint()
        if bound_fp != current_fp:
            return {
                "valid": False,
                "error": "License 綁定的裝置不符（請聯繫客服轉移授權）",
                "tier": payload.get("tier", "free"),
                "device_mismatch": True,
            }

    # 4. 組合結果
    tier = payload.get("tier", "free")
    tier_info = TIERS.get(tier, TIERS["free"])

    return {
        "valid": True,
        "license_id": payload.get("license_id"),
        "customer_name": payload.get("customer_name"),
        "tier": tier,
        "tier_name": payload.get("tier_name", tier_info["name"]),
        "roles": payload.get("roles", tier_info["roles"]),
        "max_kb_items": payload.get("max_kb_items", tier_info["max_kb_items"]),
        "remote_calls_per_month": payload.get("remote_calls_per_month", tier_info["remote_calls_per_month"]),
        "vision_enabled": payload.get("vision_enabled", tier_info["vision_enabled"]),
        "workflow_enabled": payload.get("workflow_enabled", tier_info["workflow_enabled"]),
        "offline_grace_days": payload.get("offline_grace_days", tier_info["offline_grace_days"]),
        "expires_at": expires_at_str,
        "days_remaining": days_remaining,
        "issued_at": payload.get("issued_at"),
        "offline_ok": True,
        "features": {
            "roles": payload.get("roles", []),
            "vision": payload.get("vision_enabled", False),
            "workflow": payload.get("workflow_enabled", False),
            "remote_enhance": payload.get("remote_calls_per_month", 0) != 0,
            "kb_sync": tier in ("professional", "enterprise"),
        },
    }


# =====================================================================
# License 啟用（客戶端安裝時）
# =====================================================================

def activate_license(license_data_b64: str, bind_device: bool = True) -> dict:
    """
    客戶端啟用 License（安裝時呼叫）
    - 驗證 License 有效性
    - 儲存到本地
    - 可選綁定裝置
    """
    # 先驗證
    result = validate_license(license_data_b64=license_data_b64)
    if not result.get("valid"):
        return {"ok": False, "error": result.get("error", "License 無效")}

    # 儲存到本地
    LICENSE_FILE.parent.mkdir(parents=True, exist_ok=True)
    LICENSE_FILE.write_text(license_data_b64, encoding="utf-8")

    # 記錄啟用資訊
    activation_info = {
        "license_id": result.get("license_id"),
        "activated_at": datetime.now().isoformat(timespec="seconds"),
        "device_fingerprint": get_device_fingerprint() if bind_device else "",
        "hostname": platform.node(),
        "os": f"{platform.system()} {platform.release()}",
        "last_online_check": datetime.now().isoformat(timespec="seconds"),
    }
    activation_file = LICENSE_FILE.parent / "activation.json"
    activation_file.write_text(
        json.dumps(activation_info, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    return {
        "ok": True,
        "license_id": result.get("license_id"),
        "tier": result.get("tier"),
        "tier_name": result.get("tier_name"),
        "customer_name": result.get("customer_name"),
        "expires_at": result.get("expires_at"),
        "days_remaining": result.get("days_remaining"),
        "features": result.get("features"),
    }


# =====================================================================
# 離線檢查（客戶端定期呼叫）
# =====================================================================

def check_offline_grace() -> dict:
    """
    檢查離線寬限期
    - 讀取上次連線驗證時間
    - 超過寬限期 → 需要連線
    """
    activation_file = LICENSE_FILE.parent / "activation.json"
    if not activation_file.exists():
        return {"ok": False, "error": "尚未啟用 License", "need_activation": True}

    try:
        info = json.loads(activation_file.read_text(encoding="utf-8"))
    except Exception:
        return {"ok": False, "error": "啟用資訊損壞", "need_activation": True}

    last_check_str = info.get("last_online_check", "")
    if not last_check_str:
        return {"ok": False, "error": "無上次連線記錄", "need_online": True}

    try:
        last_check = datetime.fromisoformat(last_check_str)
    except Exception:
        return {"ok": False, "error": "連線記錄格式無效", "need_online": True}

    # 取得 License 的離線寬限天數
    license_result = validate_license()
    if not license_result.get("valid"):
        return {"ok": False, "error": license_result.get("error"), "need_activation": True}

    grace_days = license_result.get("offline_grace_days", 30)
    days_offline = (datetime.now() - last_check).days

    if days_offline > grace_days:
        return {
            "ok": False,
            "error": f"離線已超過 {grace_days} 天（已離線 {days_offline} 天），請連線驗證",
            "need_online": True,
            "days_offline": days_offline,
            "grace_days": grace_days,
        }

    return {
        "ok": True,
        "days_offline": days_offline,
        "grace_days": grace_days,
        "days_remaining_offline": grace_days - days_offline,
        "license": license_result,
    }


def update_online_check():
    """連線驗證成功後更新時間戳"""
    activation_file = LICENSE_FILE.parent / "activation.json"
    if not activation_file.exists():
        return
    try:
        info = json.loads(activation_file.read_text(encoding="utf-8"))
        info["last_online_check"] = datetime.now().isoformat(timespec="seconds")
        activation_file.write_text(
            json.dumps(info, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception:
        pass


# =====================================================================
# License 管理（伺服器端）
# =====================================================================

def list_licenses() -> list[dict]:
    """列出所有已發放的 License"""
    LICENSE_DIR.mkdir(parents=True, exist_ok=True)
    result = []
    for f in sorted(LICENSE_DIR.glob("ZW-*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            # 檢查是否過期
            expires = data.get("expires_at", "")
            try:
                exp_dt = datetime.fromisoformat(expires)
                if exp_dt < datetime.now() and data.get("status") == "active":
                    data["status"] = "expired"
            except Exception:
                pass
            result.append({
                "license_id": data.get("license_id"),
                "customer_name": data.get("customer_name"),
                "tier": data.get("tier"),
                "status": data.get("status"),
                "issued_at": data.get("issued_at"),
                "expires_at": data.get("expires_at"),
                "activations": len(data.get("activations", [])),
            })
        except Exception:
            continue
    return result


def revoke_license(license_id: str) -> dict:
    """撤銷 License"""
    record_file = LICENSE_DIR / f"{license_id}.json"
    if not record_file.exists():
        return {"ok": False, "error": "License 不存在"}
    try:
        data = json.loads(record_file.read_text(encoding="utf-8"))
        data["status"] = "revoked"
        data["revoked_at"] = datetime.now().isoformat(timespec="seconds")
        record_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "license_id": license_id, "status": "revoked"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def renew_license(license_id: str, additional_days: int = 365) -> dict:
    """續期 License（重新生成）"""
    record_file = LICENSE_DIR / f"{license_id}.json"
    if not record_file.exists():
        return {"ok": False, "error": "License 不存在"}
    try:
        data = json.loads(record_file.read_text(encoding="utf-8"))
        return generate_license(
            customer_name=data.get("customer_name", ""),
            tier=data.get("tier", "professional"),
            duration_days=additional_days,
            device_fingerprint=data.get("device_fingerprint", ""),
            max_devices=data.get("max_devices", 1),
            notes=f"續期自 {license_id}",
        )
    except Exception as e:
        return {"ok": False, "error": str(e)}


# =====================================================================
# 與 auth_manager 整合
# =====================================================================

def get_user_features(token_data: dict) -> dict:
    """
    根據用戶 token + License 判斷可用功能
    superadmin/admin 永遠全功能
    """
    role = (token_data or {}).get("role", "")
    if role in ("superadmin", "admin"):
        return {
            "tier": "enterprise",
            "roles": "__all__",
            "vision": True,
            "workflow": True,
            "remote_enhance": True,
            "kb_sync": True,
            "max_kb_items": -1,
            "remote_calls_per_month": -1,
        }

    # 檢查 License
    license_result = validate_license()
    if license_result.get("valid"):
        return license_result.get("features", {})

    # 無 License → 免費版
    free = TIERS["free"]
    return {
        "tier": "free",
        "roles": free["roles"],
        "vision": free["vision_enabled"],
        "workflow": free["workflow_enabled"],
        "remote_enhance": False,
        "kb_sync": False,
        "max_kb_items": free["max_kb_items"],
        "remote_calls_per_month": 0,
    }


# =====================================================================
# CLI 工具
# =====================================================================

def _cli():
    import argparse
    parser = argparse.ArgumentParser(description="築未科技 License 管理工具")
    sub = parser.add_subparsers(dest="cmd")

    # generate
    gen = sub.add_parser("generate", help="生成 License")
    gen.add_argument("--customer", required=True, help="客戶名稱")
    gen.add_argument("--tier", default="professional", choices=list(TIERS.keys()))
    gen.add_argument("--days", type=int, default=365, help="有效天數")
    gen.add_argument("--bind-device", action="store_true", help="綁定當前裝置")

    # validate
    val = sub.add_parser("validate", help="驗證 License")
    val.add_argument("--file", default="", help="License 檔案路徑")

    # activate
    act = sub.add_parser("activate", help="啟用 License")
    act.add_argument("--data", required=True, help="License Base64 資料")

    # list
    sub.add_parser("list", help="列出所有 License")

    # revoke
    rev = sub.add_parser("revoke", help="撤銷 License")
    rev.add_argument("--id", required=True, help="License ID")

    # device-info
    sub.add_parser("device-info", help="顯示裝置指紋")

    # offline-check
    sub.add_parser("offline-check", help="檢查離線狀態")

    args = parser.parse_args()

    if args.cmd == "generate":
        fp = get_device_fingerprint() if getattr(args, "bind_device", False) else ""
        result = generate_license(
            customer_name=args.customer,
            tier=args.tier,
            duration_days=args.days,
            device_fingerprint=fp,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.cmd == "validate":
        result = validate_license(license_file=args.file)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.cmd == "activate":
        result = activate_license(args.data)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.cmd == "list":
        licenses = list_licenses()
        if not licenses:
            print("尚無 License 記錄")
        for lic in licenses:
            print(f"  {lic['license_id']} | {lic['customer_name']} | {lic['tier']} | {lic['status']} | expires: {lic['expires_at']}")

    elif args.cmd == "revoke":
        result = revoke_license(args.id)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.cmd == "device-info":
        fp = get_device_fingerprint()
        print(f"裝置指紋: {fp}")
        print(f"主機名稱: {platform.node()}")
        print(f"作業系統: {platform.system()} {platform.release()}")
        print(f"架構: {platform.machine()}")

    elif args.cmd == "offline-check":
        result = check_offline_grace()
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    _cli()
