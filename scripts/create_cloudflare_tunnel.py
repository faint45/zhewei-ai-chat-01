#!/usr/bin/env python3
"""
自動在 Cloudflare Zero Trust Dashboard 建立 failover tunnel
使用 Playwright 操作瀏覽器
"""
import sys
import time
import json
import re

def main():
    from playwright.sync_api import sync_playwright
    
    tunnel_name = "zhewei-failover"
    hostnames = [
        ("", "zhe-wei.net", "http://gateway:80"),
        ("jarvis", "zhe-wei.net", "http://gateway:80"),
        ("cms", "zhe-wei.net", "http://gateway:80"),
        ("codesim", "zhe-wei.net", "http://gateway:80"),
        ("bridge", "zhe-wei.net", "http://gateway:80"),
        ("predict", "zhe-wei.net", "http://gateway:80"),
    ]
    
    with sync_playwright() as p:
        # 使用真實 Chrome（已登入 Cloudflare）
        browser = p.chromium.launch(
            headless=False,
            channel="chrome",
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 900}
        )
        page = context.new_page()
        
        print("[1/5] 打開 Cloudflare Zero Trust...")
        page.goto("https://one.dash.cloudflare.com/")
        
        # 等待登入（如果需要）
        print("如果需要登入，請在瀏覽器中完成登入...")
        print("等待頁面載入...")
        
        # 等待直到看到 Zero Trust dashboard
        try:
            page.wait_for_url("**/one.dash.cloudflare.com/**", timeout=120000)
            time.sleep(3)
        except:
            pass
        
        print("[2/5] 導航到 Tunnels 頁面...")
        page.goto("https://one.dash.cloudflare.com/networks/tunnels")
        time.sleep(5)
        
        # 等待頁面載入
        page.wait_for_load_state("networkidle", timeout=30000)
        time.sleep(2)
        
        # 截圖看看當前狀態
        page.screenshot(path="d:/zhe-wei-tech/scripts/cf_tunnels_page.png")
        print("已截圖: scripts/cf_tunnels_page.png")
        
        print("[3/5] 點擊 Create a tunnel...")
        # 嘗試找到 Create tunnel 按鈕
        create_btn = page.locator("text=Create a tunnel").first
        if create_btn.is_visible():
            create_btn.click()
            time.sleep(3)
        else:
            # 嘗試其他選擇器
            create_btn = page.locator("button:has-text('Add a tunnel')").first
            if create_btn.is_visible():
                create_btn.click()
                time.sleep(3)
            else:
                page.screenshot(path="d:/zhe-wei-tech/scripts/cf_no_create_btn.png")
                print("找不到 Create tunnel 按鈕，已截圖")
                print("請手動檢查截圖")
                input("按 Enter 繼續...")
        
        # 選擇 Cloudflared
        time.sleep(2)
        cloudflared_option = page.locator("text=Cloudflared").first
        if cloudflared_option.is_visible():
            cloudflared_option.click()
            time.sleep(1)
        
        # 點 Next
        next_btn = page.locator("button:has-text('Next')").first
        if next_btn.is_visible():
            next_btn.click()
            time.sleep(2)
        
        print(f"[4/5] 輸入 tunnel 名稱: {tunnel_name}")
        # 輸入 tunnel 名稱
        name_input = page.locator("input[placeholder*='tunnel']").first
        if not name_input.is_visible():
            name_input = page.locator("input[name*='name']").first
        if not name_input.is_visible():
            name_input = page.locator("input").first
        
        name_input.fill(tunnel_name)
        time.sleep(1)
        
        # 點 Save / Next
        save_btn = page.locator("button:has-text('Save')").first
        if not save_btn.is_visible():
            save_btn = page.locator("button:has-text('Next')").first
        if save_btn.is_visible():
            save_btn.click()
            time.sleep(5)
        
        # 截圖看 token 頁面
        page.screenshot(path="d:/zhe-wei-tech/scripts/cf_tunnel_token.png")
        print("已截圖 token 頁面: scripts/cf_tunnel_token.png")
        
        # 嘗試提取 token
        print("[5/5] 提取 tunnel token...")
        page_content = page.content()
        
        # 找 Docker 安裝指令中的 token
        docker_tab = page.locator("text=Docker").first
        if docker_tab.is_visible():
            docker_tab.click()
            time.sleep(2)
        
        # 嘗試從頁面提取 token
        code_blocks = page.locator("code, pre, .code-snippet")
        for i in range(code_blocks.count()):
            text = code_blocks.nth(i).inner_text()
            if "eyJ" in text:
                # 找到 token
                match = re.search(r'(eyJ[A-Za-z0-9+/=]+)', text)
                if match:
                    token = match.group(1)
                    print(f"\n{'='*60}")
                    print(f"TUNNEL TOKEN 已找到!")
                    print(f"{'='*60}")
                    print(f"Token: {token[:50]}...")
                    
                    # 寫入檔案
                    with open("d:/zhe-wei-tech/scripts/failover_tunnel_token.txt", "w") as f:
                        f.write(token)
                    print(f"Token 已儲存到: scripts/failover_tunnel_token.txt")
                    break
        
        page.screenshot(path="d:/zhe-wei-tech/scripts/cf_tunnel_final.png")
        print("\n完成！請檢查截圖確認結果。")
        print("按 Enter 關閉瀏覽器...")
        input()
        
        browser.close()

if __name__ == "__main__":
    main()
