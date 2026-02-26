# -*- coding: utf-8 -*-
"""
營建自動化大腦 — 離線授權驗證
薄封裝 license_manager.py，提供 construction_brain 專用的授權檢查

複用：
  - license_manager.py: RSA/HMAC 簽章驗證、License Key 解析
"""
import logging
import os
import sys
from pathlib import Path
from typing import Optional

log = logging.getLogger("construction_brain.auth")

# 確保能 import 主專案的 license_manager
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


def validate_license(license_key: str = "") -> dict:
    """
    驗證 License Key

    Args:
        license_key: License Key 字串（空則從檔案讀取）

    Returns:
        {
            "valid": bool,
            "tier": str,           # free/professional/enterprise
            "expires": str,        # 到期日
            "features": [...],     # 可用功能列表
            "error": str,          # 錯誤訊息
        }
    """
    try:
        from license_manager import (
            validate_license_key,
            get_current_license,
            LICENSE_FILE,
        )

        # 若未提供 key，從檔案讀取
        if not license_key:
            if LICENSE_FILE.exists():
                license_key = LICENSE_FILE.read_text(encoding="utf-8").strip()
            else:
                return {
                    "valid": False,
                    "tier": "free",
                    "expires": "",
                    "features": _get_free_features(),
                    "error": "未找到 License 檔案",
                }

        result = validate_license_key(license_key)
        if result.get("valid"):
            tier = result.get("tier", "free")
            return {
                "valid": True,
                "tier": tier,
                "expires": result.get("expires", ""),
                "features": _get_features_by_tier(tier),
                "error": "",
            }
        else:
            return {
                "valid": False,
                "tier": "free",
                "expires": "",
                "features": _get_free_features(),
                "error": result.get("error", "License 無效"),
            }

    except ImportError:
        log.warning("license_manager 不可用，使用免費模式")
        return {
            "valid": False,
            "tier": "free",
            "expires": "",
            "features": _get_free_features(),
            "error": "license_manager 模組不可用",
        }
    except Exception as e:
        return {
            "valid": False,
            "tier": "free",
            "expires": "",
            "features": _get_free_features(),
            "error": str(e),
        }


def check_feature(feature: str, license_key: str = "") -> bool:
    """快速檢查某功能是否可用"""
    result = validate_license(license_key)
    return feature in result.get("features", [])


def get_tier(license_key: str = "") -> str:
    """取得目前授權等級"""
    return validate_license(license_key).get("tier", "free")


def _get_free_features() -> list:
    """免費版可用功能"""
    return [
        "daily_report_basic",       # 基礎日報
        "safety_keyword_check",     # 關鍵詞工安檢查
        "kb_query_basic",           # 基礎知識庫查詢（限 2000 筆）
        "voice_transcribe",         # 語音辨識
    ]


def _get_features_by_tier(tier: str) -> list:
    """依授權等級回傳可用功能"""
    features = {
        "free": _get_free_features(),
        "professional": [
            *_get_free_features(),
            "daily_report_full",        # 完整日報（含 LLM 生成）
            "safety_llm_check",         # LLM 深度工安分析
            "safety_photo_check",       # 照片工安偵測
            "kb_query_unlimited",       # 知識庫無限查詢
            "kb_ingest",                # 知識庫匯入
            "schedule_tracking",        # 進度追蹤
            "scurve_export",            # S-Curve 匯出
            "line_integration",         # LINE 整合
            "multi_project",            # 多工程支援（3 個）
        ],
        "enterprise": [
            *_get_free_features(),
            "daily_report_full",
            "safety_llm_check",
            "safety_photo_check",
            "kb_query_unlimited",
            "kb_ingest",
            "schedule_tracking",
            "scurve_export",
            "line_integration",
            "multi_project_unlimited",  # 無限工程
            "multi_lora",               # 多 LoRA 客製模型
            "api_access",               # 開放 API
            "custom_model",             # 自訂模型
            "priority_support",         # 優先支援
        ],
    }
    return features.get(tier, _get_free_features())
