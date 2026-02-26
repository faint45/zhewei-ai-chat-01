# -*- coding: utf-8 -*-
import requests
import json

API_TOKEN = "krhoOLvL34AzrfF2FtnGuYHd0AP0UMdeIiNDSVtj"
TUNNEL_ID = "546fffc1-eb7d-4f9a-a3df-d30a1940aa0c"

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

print("🌐 Cloudflare Tunnel 域名自動添加\n")

# 1. 取得 Account ID
print("🔍 取得 Account ID...")
try:
    resp = requests.get("https://api.cloudflare.com/client/v4/accounts", headers=headers)
    data = resp.json()
    
    if not data.get("success"):
        print(f"❌ API 錯誤: {data.get('errors', [])}")
        print(f"完整回應: {json.dumps(data, indent=2)}")
        exit(1)
    
    if not data.get("result"):
        print("❌ 沒有找到 Account")
        exit(1)
    
    ACCOUNT_ID = data["result"][0]["id"]
    print(f"✅ Account ID: {ACCOUNT_ID}\n")
    
except Exception as e:
    print(f"❌ 請求失敗: {e}")
    exit(1)

# 2. 取得當前 Tunnel 配置
print("📋 取得當前 Tunnel 配置...")
tunnel_url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/cfd_tunnel/{TUNNEL_ID}/configurations"

try:
    resp = requests.get(tunnel_url, headers=headers)
    data = resp.json()
    
    if not data.get("success"):
        print(f"❌ 無法取得配置: {data.get('errors', [])}")
        exit(1)
    
    config = data["result"]["config"]
    ingress = config.get("ingress", [])
    version = data["result"].get("version", "unknown")
    
    print(f"✅ 當前配置版本: {version}")
    
    existing_hostnames = {rule.get("hostname") for rule in ingress if rule.get("hostname")}
    print(f"📊 現有域名數量: {len(existing_hostnames)}\n")
    
except Exception as e:
    print(f"❌ 請求失敗: {e}")
    exit(1)

# 3. 準備新域名
domains_to_add = [
    {"hostname": "zhe-wei.net", "service": "http://gateway:80"},
    {"hostname": "www.zhe-wei.net", "service": "http://gateway:80"}
]

new_ingress = []
added_count = 0

for domain in domains_to_add:
    hostname = domain["hostname"]
    if hostname in existing_hostnames:
        print(f"⚠️  {hostname} 已存在，跳過")
    else:
        print(f"➕ 準備添加: {hostname}")
        new_ingress.append({
            "hostname": hostname,
            "service": domain["service"],
            "originRequest": {}
        })
        added_count += 1

if added_count == 0:
    print("\n✅ 所有域名已存在，無需添加")
    exit(0)

# 4. 合併配置
final_ingress = new_ingress + [r for r in ingress if r.get("hostname")]

# 添加默認路由
default_route = next((r for r in ingress if not r.get("hostname")), None)
if default_route:
    final_ingress.append(default_route)
else:
    final_ingress.append({"service": "http://gateway:80"})

# 5. 更新配置
print(f"\n📝 更新 Tunnel 配置，新增 {added_count} 個域名...")

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
                print(f"  ✅ {domain['hostname']} → {domain['service']}")
        
        print("\n⏱️  等待 10-30 秒 DNS 生效...")
        print("\n🔗 測試訪問:")
        print("  https://zhe-wei.net")
        print("  https://www.zhe-wei.net")
        print()
    else:
        print(f"\n❌ 域名添加失敗: {data.get('errors', [])}")
        print(f"完整回應: {json.dumps(data, indent=2)}")
        exit(1)
        
except Exception as e:
    print(f"❌ 請求失敗: {e}")
    exit(1)
