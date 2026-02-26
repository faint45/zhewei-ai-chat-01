# -*- coding: utf-8 -*-
"""
直接添加所有域名到 Cloudflare Tunnel
使用 Cloudflare API 直接操作
"""

import requests
import json

API_TOKEN = "EZA_rywc_4zlocHy9ltdLTaW3AjoCed59RdykQOK"
TUNNEL_ID = "546fffc1-eb7d-4f9a-a3df-d30a1940aa0c"

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

print("🌐 Cloudflare Tunnel 域名批量添加\n")

# 1. 先嘗試從 zones 獲取 account_id
print("🔍 取得 Account ID...")
try:
    # 方法1: 從 zones 取得
    resp = requests.get("https://api.cloudflare.com/client/v4/zones", headers=headers)
    data = resp.json()
    
    if data.get("success") and data.get("result"):
        account_id = data["result"][0]["account"]["id"]
        print(f"✅ Account ID: {account_id}\n")
    else:
        print("❌ 無法從 zones 取得 Account ID")
        print("請提供 Account ID 或使用手動方式添加域名")
        print("\n手動添加步驟:")
        print("1. 訪問 https://one.dash.cloudflare.com/")
        print("2. Access → Tunnels → Configure")
        print("3. 添加以下域名，全部指向 gateway:80:")
        
        domains = [
            "zhe-wei.net (Subdomain 留空)",
            "www.zhe-wei.net",
            "jarvis.zhe-wei.net",
            "bridge.zhe-wei.net",
            "dify.zhe-wei.net",
            "cms.zhe-wei.net",
            "vision.zhe-wei.net",
            "codesim.zhe-wei.net"
        ]
        
        for i, domain in enumerate(domains, 1):
            print(f"   {i}. {domain}")
        
        exit(1)

except Exception as e:
    print(f"❌ 請求失敗: {e}")
    exit(1)

# 2. 取得當前 Tunnel 配置
print("📋 取得當前 Tunnel 配置...")
tunnel_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/cfd_tunnel/{TUNNEL_ID}/configurations"

try:
    resp = requests.get(tunnel_url, headers=headers)
    data = resp.json()
    
    if not data.get("success"):
        print(f"❌ 無法取得配置: {data.get('errors', [])}")
        exit(1)
    
    current_ingress = data["result"]["config"].get("ingress", [])
    existing_hostnames = {rule.get("hostname") for rule in current_ingress if rule.get("hostname")}
    
    print(f"✅ 當前已有 {len(existing_hostnames)} 個域名\n")
    
except Exception as e:
    print(f"❌ 請求失敗: {e}")
    exit(1)

# 3. 準備要添加的域名
domains_to_add = [
    {"hostname": "zhe-wei.net", "desc": "Portal 主入口"},
    {"hostname": "www.zhe-wei.net", "desc": "Portal WWW"},
    {"hostname": "jarvis.zhe-wei.net", "desc": "Jarvis AI"},
    {"hostname": "bridge.zhe-wei.net", "desc": "Smart Bridge"},
    {"hostname": "dify.zhe-wei.net", "desc": "Dify"},
    {"hostname": "cms.zhe-wei.net", "desc": "CMS"},
    {"hostname": "vision.zhe-wei.net", "desc": "Vision"},
    {"hostname": "codesim.zhe-wei.net", "desc": "CodeSim"}
]

new_ingress = []
added_count = 0

for domain in domains_to_add:
    hostname = domain["hostname"]
    if hostname in existing_hostnames:
        print(f"⚠️  {hostname} 已存在，跳過")
    else:
        print(f"➕ 準備添加: {hostname} ({domain['desc']})")
        new_ingress.append({
            "hostname": hostname,
            "service": "http://gateway:80",
            "originRequest": {}
        })
        added_count += 1

if added_count == 0:
    print("\n✅ 所有域名已存在，無需添加")
    exit(0)

# 4. 合併配置
final_ingress = new_ingress + [r for r in current_ingress if r.get("hostname")]

# 添加默認路由
default_route = next((r for r in current_ingress if not r.get("hostname")), None)
if default_route:
    final_ingress.append(default_route)
else:
    final_ingress.append({"service": "http://gateway:80"})

# 5. 更新配置
print(f"\n📝 添加 {added_count} 個新域名到 Cloudflare Tunnel...")

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
        print("\n✅ 域名添加成功！\n")
        print("📋 新增的域名:")
        for domain in domains_to_add:
            if domain["hostname"] not in existing_hostnames:
                print(f"  ✅ {domain['hostname']:30} ({domain['desc']})")
        
        print("\n⏱️  等待 10-30 秒 DNS 生效...")
        print("\n🔗 測試訪問:")
        print("  https://zhe-wei.net")
        print("  https://jarvis.zhe-wei.net")
        print("  https://bridge.zhe-wei.net")
        print("\n✨ 完成！")
    else:
        print(f"\n❌ 域名添加失敗: {data.get('errors', [])}")
        print(f"完整回應: {json.dumps(data, indent=2)}")
        exit(1)
        
except Exception as e:
    print(f"❌ 請求失敗: {e}")
    exit(1)
