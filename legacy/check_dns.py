# -*- coding: utf-8 -*-
import requests

API_TOKEN = "EZA_rywc_4zlocHy9ltdLTaW3AjoCed59RdykQOK"
headers = {"Authorization": f"Bearer {API_TOKEN}"}

# 取得 zone ID
r = requests.get("https://api.cloudflare.com/client/v4/zones?name=zhe-wei.net", headers=headers)
zones = r.json()
if zones["success"] and zones["result"]:
    zone_id = zones["result"][0]["id"]
    print(f"Zone ID: {zone_id}")
    
    # 取得 DNS 記錄
    r2 = requests.get(f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records", headers=headers)
    if r2.json()["success"]:
        for rec in r2.json()["result"]:
            name = rec["name"]
            rtype = rec["type"]
            content = rec["content"][:80]
            proxied = rec.get("proxied", False)
            print(f"{rtype:6} {name:35} -> {content}  proxied={proxied}")
    else:
        print("Cannot get DNS records")
else:
    print("Cannot get zone")
