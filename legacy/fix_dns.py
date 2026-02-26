# -*- coding: utf-8 -*-
"""修復 zhe-wei.net 和 www.zhe-wei.net 的 DNS CNAME 記錄"""
import requests
import json

API_TOKEN = "EZA_rywc_4zlocHy9ltdLTaW3AjoCed59RdykQOK"
TUNNEL_ID = "546fffc1-eb7d-4f9a-a3df-d30a1940aa0c"
ZONE_ID = "8ba45d8905b38792b061bdcadac6dd39"

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

print("🔧 修復 DNS CNAME 記錄\n")

# 先列出現有 DNS 記錄
print("📋 查詢現有 DNS 記錄...")
r = requests.get(
    f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records",
    headers=headers
)
data = r.json()

if not data.get("success"):
    print(f"❌ 無法查詢 DNS: {data.get('errors')}")
    print("可能需要 Zone DNS Read 權限")
    print("\n嘗試直接創建 CNAME 記錄...")
else:
    existing = {}
    for rec in data.get("result", []):
        existing[rec["name"]] = rec
        print(f"  {rec['type']:6} {rec['name']:35} -> {rec['content'][:60]}  proxied={rec.get('proxied')}")
    print()

# 需要添加的 CNAME 記錄
tunnel_cname = f"{TUNNEL_ID}.cfargotunnel.com"
records_to_add = [
    {"type": "CNAME", "name": "zhe-wei.net", "content": tunnel_cname, "proxied": True},
    {"type": "CNAME", "name": "www", "content": tunnel_cname, "proxied": True},
    {"type": "CNAME", "name": "bridge", "content": tunnel_cname, "proxied": True},
    {"type": "CNAME", "name": "codesim", "content": tunnel_cname, "proxied": True},
]

for record in records_to_add:
    name = record["name"]
    full_name = f"{name}.zhe-wei.net" if "." not in name else name
    
    print(f"➕ 添加 CNAME: {full_name} -> {tunnel_cname[:40]}...")
    
    r = requests.post(
        f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records",
        headers=headers,
        json=record
    )
    result = r.json()
    
    if result.get("success"):
        print(f"  ✅ 成功")
    else:
        errors = result.get("errors", [])
        for err in errors:
            if err.get("code") == 81053 or "already exists" in str(err.get("message", "")):
                print(f"  ⚠️  已存在，跳過")
            else:
                print(f"  ❌ 失敗: {err}")

print("\n✨ DNS 修復完成！")
print("⏱️  等待 30 秒 DNS 生效後測試...")
