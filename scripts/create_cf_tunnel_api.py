#!/usr/bin/env python3
"""
用 Cloudflare API 建立 failover tunnel
從現有 tunnel token 解析 account ID，然後用 API 建立新 tunnel
"""
import json
import base64
import os
import sys
import requests

def decode_tunnel_token(token):
    """解碼 tunnel token 取得 account ID"""
    try:
        # token 是 base64 encoded JSON
        padding = 4 - len(token) % 4
        if padding != 4:
            token += "=" * padding
        decoded = base64.b64decode(token)
        data = json.loads(decoded)
        return data
    except Exception as e:
        print(f"解碼失敗: {e}")
        return None

def main():
    # 讀取 .env 取得現有 tunnel token
    env_path = r"D:\zhe-wei-tech\.env"
    token_value = None
    
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("CLOUDFLARE_TOKEN="):
                token_value = line.strip().split("=", 1)[1]
                break
    
    if not token_value:
        print("找不到 CLOUDFLARE_TOKEN")
        sys.exit(1)
    
    # 解碼 token
    token_data = decode_tunnel_token(token_value)
    if token_data:
        print(f"現有 Tunnel 資訊:")
        print(f"  Account ID: {token_data.get('a', 'N/A')}")
        print(f"  Tunnel ID:  {token_data.get('t', 'N/A')}")
        account_id = token_data.get('a')
    else:
        print("無法解碼 token")
        sys.exit(1)
    
    print(f"\n要用 Cloudflare API 建立新 tunnel，需要 API Token。")
    print(f"Account ID: {account_id}")
    print(f"\n請到以下網址建立 API Token:")
    print(f"  https://dash.cloudflare.com/profile/api-tokens")
    print(f"\n選擇 'Create Custom Token':")
    print(f"  - Token name: zhewei-tunnel-api")
    print(f"  - Permissions: Account > Cloudflare Tunnel > Edit")
    print(f"  - Account Resources: Include > 你的帳號")
    print(f"\n或者更簡單的方式 — 用 Global API Key:")
    print(f"  https://dash.cloudflare.com/profile/api-tokens")
    print(f"  頁面最下方 'Global API Key' > View")
    print()
    
    api_token = input("請貼上 API Token (或 Global API Key): ").strip()
    if not api_token:
        print("未提供 token，退出")
        sys.exit(1)
    
    email = input("Cloudflare 帳號 email (如果用 Global API Key): ").strip()
    
    # 設定 headers
    if email:
        # Global API Key
        headers = {
            "X-Auth-Email": email,
            "X-Auth-Key": api_token,
            "Content-Type": "application/json",
        }
    else:
        # API Token
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }
    
    # 建立 tunnel
    print(f"\n建立 tunnel: zhewei-failover...")
    import secrets
    tunnel_secret = base64.b64encode(secrets.token_bytes(32)).decode()
    
    resp = requests.post(
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}/cfd_tunnel",
        headers=headers,
        json={
            "name": "zhewei-failover",
            "tunnel_secret": tunnel_secret,
        }
    )
    
    if resp.status_code in (200, 201):
        result = resp.json()
        if result.get("success"):
            tunnel = result["result"]
            tunnel_id = tunnel["id"]
            print(f"\n✅ Tunnel 建立成功!")
            print(f"  Name: {tunnel['name']}")
            print(f"  ID:   {tunnel_id}")
            
            # 建立 tunnel token
            new_token_data = {
                "a": account_id,
                "t": tunnel_id,
                "s": tunnel_secret,
            }
            new_token = base64.b64encode(json.dumps(new_token_data).encode()).decode().rstrip("=")
            
            print(f"\n  Token: {new_token[:60]}...")
            
            # 儲存 token
            token_file = r"D:\zhe-wei-tech\scripts\failover_tunnel_token.txt"
            with open(token_file, "w") as f:
                f.write(new_token)
            print(f"  已儲存到: {token_file}")
            
            # 設定 DNS ingress
            print(f"\n設定 tunnel ingress...")
            ingress_config = {
                "config": {
                    "ingress": [
                        {"hostname": "zhe-wei.net", "service": "http://gateway:80"},
                        {"hostname": "www.zhe-wei.net", "service": "http://gateway:80"},
                        {"hostname": "jarvis.zhe-wei.net", "service": "http://gateway:80"},
                        {"hostname": "cms.zhe-wei.net", "service": "http://gateway:80"},
                        {"hostname": "codesim.zhe-wei.net", "service": "http://gateway:80"},
                        {"hostname": "bridge.zhe-wei.net", "service": "http://gateway:80"},
                        {"hostname": "predict.zhe-wei.net", "service": "http://gateway:80"},
                        {"service": "http_status:404"},
                    ]
                }
            }
            
            resp2 = requests.put(
                f"https://api.cloudflare.com/client/v4/accounts/{account_id}/cfd_tunnel/{tunnel_id}/configurations",
                headers=headers,
                json=ingress_config,
            )
            
            if resp2.status_code == 200 and resp2.json().get("success"):
                print("✅ Ingress 設定成功!")
            else:
                print(f"⚠️ Ingress 設定失敗: {resp2.text}")
                print("可以稍後在 Dashboard 手動設定")
            
            # 輸出結果
            print(f"\n{'='*60}")
            print(f"FAILOVER TUNNEL TOKEN:")
            print(f"{new_token}")
            print(f"{'='*60}")
            print(f"\n下一步: 將此 token 加入 VPS .env:")
            print(f"  CLOUDFLARE_FAILOVER_TOKEN={new_token}")
            
            return new_token
        else:
            print(f"❌ API 錯誤: {result.get('errors')}")
    else:
        print(f"❌ HTTP {resp.status_code}: {resp.text}")
    
    return None

if __name__ == "__main__":
    main()
