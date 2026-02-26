# -*- coding: utf-8 -*-
"""
Cloudflare Tunnel 同步腳本
自動將 services.json 中的服務同步到 Cloudflare Tunnel
"""

import json
import os
import sys
import requests
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 從環境變數讀取
API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
TUNNEL_ID = "546fffc1-eb7d-4f9a-a3df-d30a1940aa0c"

def load_services():
    """載入服務配置"""
    services_file = ROOT / "services.json"
    with open(services_file, 'r', encoding='utf-8') as f:
        return json.load(f)['services']

def get_account_id(api_token):
    """自動取得 Account ID"""
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    try:
        resp = requests.get("https://api.cloudflare.com/client/v4/accounts", headers=headers)
        data = resp.json()
        
        if data.get("success") and data.get("result"):
            return data["result"][0]["id"]
        
        # 如果無法取得，嘗試從 user info 取得
        resp = requests.get("https://api.cloudflare.com/client/v4/user", headers=headers)
        data = resp.json()
        
        if data.get("success"):
            print("⚠️  無法自動取得 Account ID，請手動設定 CLOUDFLARE_ACCOUNT_ID 環境變數")
            return None
            
    except Exception as e:
        print(f"❌ 取得 Account ID 失敗: {e}")
        return None

def sync_to_cloudflare(services, api_token, account_id):
    """同步到 Cloudflare Tunnel"""
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    tunnel_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/cfd_tunnel/{TUNNEL_ID}/configurations"
    
    # 取得當前配置
    print("📋 取得當前 Tunnel 配置...")
    try:
        resp = requests.get(tunnel_url, headers=headers)
        data = resp.json()
        
        if not data.get("success"):
            print(f"❌ 無法取得配置: {data.get('errors', [])}")
            return False
        
        current_ingress = data["result"]["config"].get("ingress", [])
        existing_hostnames = {rule.get("hostname") for rule in current_ingress if rule.get("hostname")}
        
        print(f"✅ 當前已有 {len(existing_hostnames)} 個域名\n")
        
    except Exception as e:
        print(f"❌ 請求失敗: {e}")
        return False
    
    # 準備新配置
    new_ingress = []
    added_count = 0
    
    for service in services:
        if not service.get('enabled', True):
            continue
        
        subdomain = service['subdomain']
        domain = service['domain']
        hostname = f"{subdomain}.{domain}" if subdomain else domain
        
        if hostname in existing_hostnames:
            print(f"⚠️  {hostname} 已存在，跳過")
        else:
            print(f"➕ 準備添加: {hostname}")
            new_ingress.append({
                "hostname": hostname,
                "service": "http://gateway:80",
                "originRequest": {}
            })
            added_count += 1
    
    if added_count == 0:
        print("\n✅ 所有域名已存在，無需同步")
        return True
    
    # 合併配置
    final_ingress = new_ingress + [r for r in current_ingress if r.get("hostname")]
    
    # 添加默認路由
    default_route = next((r for r in current_ingress if not r.get("hostname")), None)
    if default_route:
        final_ingress.append(default_route)
    else:
        final_ingress.append({"service": "http://gateway:80"})
    
    # 更新配置
    print(f"\n📝 同步 {added_count} 個新域名到 Cloudflare...")
    
    new_config = {
        "config": {
            "ingress": final_ingress,
            "warp-routing": {"enabled": False}
        }
    }
    
    try:
        resp = requests.put(tunnel_url, headers=headers, json=new_config)
        data = resp.json()
        
        if data.get("success"):
            print("\n✅ 同步成功！\n")
            print("📋 新增的域名:")
            for service in services:
                if not service.get('enabled', True):
                    continue
                subdomain = service['subdomain']
                domain = service['domain']
                hostname = f"{subdomain}.{domain}" if subdomain else domain
                if hostname not in existing_hostnames:
                    print(f"  ✅ {hostname}")
            return True
        else:
            print(f"\n❌ 同步失敗: {data.get('errors', [])}")
            return False
            
    except Exception as e:
        print(f"❌ 請求失敗: {e}")
        return False

def main():
    print("☁️  Cloudflare Tunnel 同步工具\n")
    
    # 檢查 API Token
    if not API_TOKEN:
        print("❌ 缺少 CLOUDFLARE_API_TOKEN 環境變數")
        print("\n請設定:")
        print("  set CLOUDFLARE_API_TOKEN=your_token_here")
        print("\n或直接在 Cloudflare Zero Trust 控制台手動添加域名")
        sys.exit(1)
    
    # 取得 Account ID
    if not ACCOUNT_ID:
        print("🔍 自動取得 Account ID...")
        account_id = get_account_id(API_TOKEN)
        if not account_id:
            print("\n請手動設定 CLOUDFLARE_ACCOUNT_ID 環境變數")
            sys.exit(1)
    else:
        account_id = ACCOUNT_ID
    
    print(f"✅ Account ID: {account_id}\n")
    
    # 載入服務配置
    print("📋 載入服務配置...")
    services = load_services()
    enabled_services = [s for s in services if s.get('enabled', True)]
    print(f"✅ 找到 {len(enabled_services)} 個啟用的服務\n")
    
    # 同步到 Cloudflare
    success = sync_to_cloudflare(enabled_services, API_TOKEN, account_id)
    
    if success:
        print("\n⏱️  等待 10-30 秒 DNS 生效...")
        print("\n🔗 測試訪問:")
        for service in enabled_services[:3]:
            subdomain = service['subdomain']
            domain = service['domain']
            hostname = f"{subdomain}.{domain}" if subdomain else domain
            print(f"  https://{hostname}")
        print("\n✨ 完成！")
    else:
        print("\n❌ 同步失敗，請檢查 API Token 權限或手動添加域名")
        sys.exit(1)

if __name__ == "__main__":
    main()
