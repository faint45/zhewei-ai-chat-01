#!/usr/bin/env python3
"""
自動在 Cloudflare Zero Trust Dashboard 建立 failover tunnel
使用已登入的 Chrome profile
"""
import sys
import time
import re
import os

def main():
    from playwright.sync_api import sync_playwright
    
    tunnel_name = "zhewei-failover"
    
    # 找到 Chrome user data 目錄
    chrome_user_data = os.path.expanduser("~") + r"\AppData\Local\Google\Chrome\User Data"
    
    with sync_playwright() as p:
        # 使用已登入的 Chrome profile
        context = p.chromium.launch_persistent_context(
            user_data_dir=chrome_user_data,
            headless=False,
            channel="chrome",
            viewport={"width": 1280, "height": 900},
            args=["--profile-directory=Default"],
        )
        
        page = context.new_page()
        
        print("[1/6] 導航到 Cloudflare Tunnels...")
        page.goto("https://one.dash.cloudflare.com/7a7f6e0f1b170e1b74c038b1b1fef6be/networks/tunnels", timeout=60000)
        time.sleep(5)
        page.wait_for_load_state("networkidle", timeout=30000)
        
        page.screenshot(path="d:/zhe-wei-tech/scripts/cf_step1.png")
        print("截圖: cf_step1.png")
        
        # 檢查是否已登入
        if "login" in page.url.lower() or "sign" in page.url.lower():
            print("需要登入！請在打開的瀏覽器中手動登入 Cloudflare...")
            print("登入完成後按 Enter 繼續...")
            input()
            page.goto("https://one.dash.cloudflare.com/7a7f6e0f1b170e1b74c038b1b1fef6be/networks/tunnels", timeout=60000)
            time.sleep(5)
        
        print("[2/6] 點擊 Add a tunnel...")
        time.sleep(3)
        
        # 嘗試多種選擇器
        clicked = False
        for selector in [
            "button:has-text('Add a tunnel')",
            "a:has-text('Add a tunnel')",
            "button:has-text('Create a tunnel')",
            "a:has-text('Create a tunnel')",
            "[data-testid='add-tunnel-button']",
            "text=Add a tunnel",
            "text=Create a tunnel",
        ]:
            try:
                el = page.locator(selector).first
                if el.is_visible(timeout=2000):
                    el.click()
                    clicked = True
                    print(f"  點擊成功: {selector}")
                    break
            except:
                continue
        
        if not clicked:
            page.screenshot(path="d:/zhe-wei-tech/scripts/cf_step2_fail.png")
            print("找不到按鈕，截圖: cf_step2_fail.png")
            print("請手動點擊 'Add a tunnel' 按鈕，然後按 Enter...")
            input()
        
        time.sleep(3)
        page.screenshot(path="d:/zhe-wei-tech/scripts/cf_step2.png")
        
        print("[3/6] 選擇 Cloudflared...")
        time.sleep(2)
        for selector in [
            "text=Cloudflared",
            "label:has-text('Cloudflared')",
            "[data-testid='cloudflared-option']",
        ]:
            try:
                el = page.locator(selector).first
                if el.is_visible(timeout=2000):
                    el.click()
                    print(f"  選擇成功: {selector}")
                    break
            except:
                continue
        
        time.sleep(1)
        # 點 Next
        for selector in ["button:has-text('Next')", "button:has-text('下一步')"]:
            try:
                el = page.locator(selector).first
                if el.is_visible(timeout=2000):
                    el.click()
                    break
            except:
                continue
        
        time.sleep(3)
        page.screenshot(path="d:/zhe-wei-tech/scripts/cf_step3.png")
        
        print(f"[4/6] 輸入名稱: {tunnel_name}")
        # 找輸入框
        filled = False
        for selector in [
            "input[placeholder*='tunnel']",
            "input[placeholder*='name']",
            "input[name*='name']",
            "input[type='text']",
        ]:
            try:
                el = page.locator(selector).first
                if el.is_visible(timeout=2000):
                    el.fill(tunnel_name)
                    filled = True
                    print(f"  填入成功: {selector}")
                    break
            except:
                continue
        
        if not filled:
            print("找不到輸入框，請手動輸入名稱，然後按 Enter...")
            input()
        
        time.sleep(1)
        # 點 Save tunnel
        for selector in [
            "button:has-text('Save tunnel')",
            "button:has-text('Save')",
            "button:has-text('儲存')",
            "button:has-text('Next')",
        ]:
            try:
                el = page.locator(selector).first
                if el.is_visible(timeout=2000):
                    el.click()
                    print(f"  點擊: {selector}")
                    break
            except:
                continue
        
        time.sleep(5)
        page.screenshot(path="d:/zhe-wei-tech/scripts/cf_step4.png")
        
        print("[5/6] 提取 token...")
        # 點 Docker tab
        for selector in ["text=Docker", "button:has-text('Docker')", "[data-testid='docker-tab']"]:
            try:
                el = page.locator(selector).first
                if el.is_visible(timeout=2000):
                    el.click()
                    time.sleep(2)
                    break
            except:
                continue
        
        # 提取 token
        token = None
        page_text = page.content()
        matches = re.findall(r'(eyJ[A-Za-z0-9+/=]{50,})', page_text)
        if matches:
            token = matches[0]
            print(f"\nTOKEN 找到！")
            print(f"Token: {token[:60]}...")
            
            with open("d:/zhe-wei-tech/scripts/failover_tunnel_token.txt", "w") as f:
                f.write(token)
            print("已儲存到: scripts/failover_tunnel_token.txt")
        else:
            page.screenshot(path="d:/zhe-wei-tech/scripts/cf_step5_notoken.png")
            print("未自動找到 token，截圖: cf_step5_notoken.png")
            print("請從頁面複製 token 並貼到這裡:")
            token = input("Token: ").strip()
            if token:
                with open("d:/zhe-wei-tech/scripts/failover_tunnel_token.txt", "w") as f:
                    f.write(token)
        
        if token:
            print(f"\n[6/6] 設定 Public Hostnames...")
            # 點 Next 進入 hostname 設定
            for selector in ["button:has-text('Next')", "button:has-text('下一步')"]:
                try:
                    el = page.locator(selector).first
                    if el.is_visible(timeout=3000):
                        el.click()
                        time.sleep(3)
                        break
                except:
                    continue
            
            page.screenshot(path="d:/zhe-wei-tech/scripts/cf_step6.png")
            print("截圖: cf_step6.png")
            print("\nPublic Hostnames 需要手動設定（UI 較複雜）")
            print("請在瀏覽器中添加以下 hostnames:")
            print("  zhe-wei.net        → http://gateway:80")
            print("  jarvis.zhe-wei.net → http://gateway:80")
            print("  cms.zhe-wei.net    → http://gateway:80")
            print("  codesim.zhe-wei.net→ http://gateway:80")
            print("  bridge.zhe-wei.net → http://gateway:80")
            print("  predict.zhe-wei.net→ http://gateway:80")
        
        print("\n完成！按 Enter 關閉瀏覽器...")
        input()
        context.close()

if __name__ == "__main__":
    main()
