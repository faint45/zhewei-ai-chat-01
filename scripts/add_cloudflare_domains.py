# -*- coding: utf-8 -*-
"""
Cloudflare Tunnel 域名自動添加腳本
使用 Cloudflare API 添加主域名到 Tunnel
"""

import os
import sys
import json
import requests
from pathlib import Path

# Cloudflare API 配置
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")  # 需要 API Token (不是 Tunnel Token)
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
TUNNEL_ID = "546fffc1-eb7d-4f9a-a3df-d30a1940aa0c"  # 從日誌中提取

# 需要添加的域名
DOMAINS_TO_ADD = [
    {
        "hostname": "zhe-wei.net",
        "service": "http://gateway:80",
        "description": "Portal PWA 主入口"
    },
    {
        "hostname": "www.zhe-wei.net",
        "service": "http://gateway:80",
        "description": "Portal PWA WWW 別名"
    }
]

def check_env():
    """檢查環境變數"""
    if not CLOUDFLARE_API_TOKEN:
        print("❌ 缺少 CLOUDFLARE_API_TOKEN 環境變數")
        print("\n請設定 Cloudflare API Token:")
        print("1. 訪問 https://dash.cloudflare.com/profile/api-tokens")
        print("2. 創建 Token，權限需要：")
        print("   - Account.Cloudflare Tunnel: Edit")
        print("   - Zone.DNS: Edit")
        print("3. 設定環境變數：")
        print("   set CLOUDFLARE_API_TOKEN=your_token_here")
        return False
    
    if not CLOUDFLARE_ACCOUNT_ID:
        print("❌ 缺少 CLOUDFLARE_ACCOUNT_ID 環境變數")
        print("\n請設定 Cloudflare Account ID:")
        print("1. 訪問 https://dash.cloudflare.com/")
        print("2. 選擇你的帳號，從 URL 複製 Account ID")
        print("3. 設定環境變數：")
        print("   set CLOUDFLARE_ACCOUNT_ID=your_account_id")
        return False
    
    return True

def get_tunnel_config():
    """取得 Tunnel 當前配置"""
    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/cfd_tunnel/{TUNNEL_ID}/configurations"
    
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ 取得 Tunnel 配置失敗: {e}")
        return None

def update_tunnel_config(config):
    """更新 Tunnel 配置"""
    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/cfd_tunnel/{TUNNEL_ID}/configurations"
    
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.put(url, headers=headers, json=config)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ 更新 Tunnel 配置失敗: {e}")
        if hasattr(e, 'response'):
            print(f"錯誤詳情: {e.response.text}")
        return None

def add_domains():
    """添加域名到 Tunnel"""
    print("🌐 Cloudflare Tunnel 域名添加工具\n")
    
    # 檢查環境變數
    if not check_env():
        return False
    
    print(f"📋 Tunnel ID: {TUNNEL_ID}")
    print(f"📋 Account ID: {CLOUDFLARE_ACCOUNT_ID}\n")
    
    # 取得當前配置
    print("🔍 取得當前 Tunnel 配置...")
    current_config = get_tunnel_config()
    
    if not current_config or not current_config.get("success"):
        print("❌ 無法取得當前配置")
        return False
    
    config_data = current_config.get("result", {}).get("config", {})
    ingress = config_data.get("ingress", [])
    
    print(f"✅ 當前配置版本: {current_config.get('result', {}).get('version', 'unknown')}")
    print(f"📊 當前域名數量: {len([i for i in ingress if 'hostname' in i])}\n")
    
    # 檢查域名是否已存在
    existing_hostnames = {i.get("hostname") for i in ingress if "hostname" in i}
    
    new_ingress = []
    added_count = 0
    
    for domain in DOMAINS_TO_ADD:
        hostname = domain["hostname"]
        
        if hostname in existing_hostnames:
            print(f"⚠️  {hostname} 已存在，跳過")
            continue
        
        print(f"➕ 添加域名: {hostname}")
        new_ingress.append({
            "hostname": hostname,
            "service": domain["service"],
            "originRequest": {}
        })
        added_count += 1
    
    if added_count == 0:
        print("\n✅ 所有域名已存在，無需添加")
        return True
    
    # 合併配置（新域名 + 現有域名 + 默認路由）
    final_ingress = new_ingress + [i for i in ingress if "hostname" in i]
    
    # 確保最後有默認路由
    default_route = next((i for i in ingress if "hostname" not in i), None)
    if default_route:
        final_ingress.append(default_route)
    else:
        final_ingress.append({"service": "http://gateway:80"})
    
    # 更新配置
    new_config = {
        "config": {
            "ingress": final_ingress,
            "warp-routing": {"enabled": False}
        }
    }
    
    print(f"\n📝 準備更新配置，新增 {added_count} 個域名...")
    print("⏳ 正在更新...")
    
    result = update_tunnel_config(new_config)
    
    if result and result.get("success"):
        print("\n✅ 域名添加成功！\n")
        print("📋 新增的域名:")
        for domain in DOMAINS_TO_ADD:
            if domain["hostname"] not in existing_hostnames:
                print(f"  ✅ {domain['hostname']} → {domain['service']}")
        
        print("\n⏱️  等待 10-30 秒 DNS 生效...")
        print("\n🔗 測試訪問:")
        print("  https://zhe-wei.net")
        print("  https://www.zhe-wei.net")
        
        return True
    else:
        print("\n❌ 域名添加失敗")
        return False

def main():
    """主函數"""
    try:
        success = add_domains()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 發生錯誤: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
