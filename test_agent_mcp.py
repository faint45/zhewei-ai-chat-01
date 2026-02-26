#!/usr/bin/env python3
"""
Agent 系統和 MCP 工具測試腳本
"""
import requests
import json
from pathlib import Path
from datetime import datetime

class AgentMCPTester:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "agent_tests": [],
            "mcp_tests": []
        }
        
    def test_agent_api(self, name, endpoint, method="GET", data=None):
        """測試 Agent API"""
        url = f"http://localhost:8002{endpoint}"
        try:
            if method == "GET":
                resp = requests.get(url, timeout=10)
            elif method == "POST":
                resp = requests.post(url, json=data, timeout=30)
            
            success = resp.status_code in [200, 201]
            result = {
                "name": name,
                "endpoint": endpoint,
                "status": resp.status_code,
                "success": success,
                "response": resp.text[:200] if not success else "✅"
            }
        except Exception as e:
            result = {
                "name": name,
                "endpoint": endpoint,
                "status": "ERROR",
                "success": False,
                "response": str(e)[:200]
            }
        
        self.results["agent_tests"].append(result)
        status = "✅" if result["success"] else "❌"
        print(f"{status} {name}")
        return result["success"]
    
    def check_mcp_config(self):
        """檢查 MCP 配置檔案"""
        mcp_config_path = Path("d:/zhe-wei-tech/.cursor/mcp.json")
        
        if not mcp_config_path.exists():
            print("❌ MCP 配置檔案不存在")
            return None
        
        try:
            with open(mcp_config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            servers = config.get("mcpServers", {})
            print(f"\n✅ 找到 {len(servers)} 個 MCP 工具")
            
            for name, server_config in servers.items():
                command = server_config.get("command", "unknown")
                args = server_config.get("args", [])
                
                self.results["mcp_tests"].append({
                    "name": name,
                    "command": command,
                    "args": args[:2] if len(args) > 2 else args,
                    "configured": True
                })
                
                print(f"  ✅ {name} ({command})")
            
            return servers
        except Exception as e:
            print(f"❌ 讀取 MCP 配置失敗: {e}")
            return None
    
    def run_tests(self):
        """執行所有測試"""
        print("\n" + "="*60)
        print("🧪 Agent 系統和 MCP 工具測試")
        print("="*60)
        
        # ===== Agent 系統測試 =====
        print("\n📋 1. Agent 系統 API 測試")
        print("="*60)
        
        # Agent Hub UI
        self.test_agent_api(
            "Agent Hub UI",
            "/static/agent_hub.html"
        )
        
        # Agent 任務 API（需要認證，預期 401）
        print("\n⚠️  以下測試預期需要認證（401 正常）：")
        self.test_agent_api(
            "建立任務（需認證）",
            "/api/agent/tasks",
            method="POST",
            data={"task_type": "llm", "description": "測試任務"}
        )
        
        self.test_agent_api(
            "語意路由（需認證）",
            "/api/agent/tasks/semantic-route",
            method="POST",
            data={"instruction": "幫我截圖"}
        )
        
        # ===== MCP 工具測試 =====
        print("\n📋 2. MCP 工具配置測試")
        print("="*60)
        
        mcp_servers = self.check_mcp_config()
        
        # 生成報告
        self.generate_report(mcp_servers)
    
    def generate_report(self, mcp_servers):
        """生成測試報告"""
        print("\n" + "="*60)
        print("📊 測試報告")
        print("="*60)
        
        # Agent 測試統計
        agent_passed = sum(1 for t in self.results["agent_tests"] if t["success"])
        agent_total = len(self.results["agent_tests"])
        
        print(f"\n🤖 Agent 系統:")
        print(f"   測試數: {agent_total}")
        print(f"   通過: {agent_passed}")
        print(f"   失敗: {agent_total - agent_passed}")
        
        # MCP 工具統計
        mcp_total = len(self.results["mcp_tests"])
        
        print(f"\n🔧 MCP 工具:")
        print(f"   配置數: {mcp_total}")
        
        if mcp_servers:
            print(f"\n📦 MCP 工具列表:")
            
            # 分類顯示
            categories = {
                "自建工具": [],
                "npm 套件": [],
                "其他": []
            }
            
            for name, config in mcp_servers.items():
                command = config.get("command", "")
                if "yahoo_finance" in str(config) or "ffmpeg" in str(config):
                    categories["自建工具"].append(name)
                elif command in ["npx", "node"]:
                    categories["npm 套件"].append(name)
                else:
                    categories["其他"].append(name)
            
            for category, tools in categories.items():
                if tools:
                    print(f"\n   {category} ({len(tools)} 個):")
                    for tool in tools:
                        print(f"     • {tool}")
        
        # 儲存詳細報告
        report_file = "agent_mcp_test_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 詳細報告已儲存至 {report_file}")
        
        # Agent 系統狀態
        print("\n" + "="*60)
        print("🎯 Agent 系統功能")
        print("="*60)
        print("""
Agent 系統提供以下功能：
1. 遠端任務執行 - POST /api/agent/tasks
2. 語意路由 - POST /api/agent/tasks/semantic-route
3. VLM 智慧 GUI - POST /api/agent/tasks/smart-gui
4. 全螢幕 VLM - POST /api/agent/tasks/screen-vlm
5. LINE 訊息讀取 - POST /api/agent/tasks/line-read-vlm
6. WebSocket 即時對話 - /ws
7. Agent Hub UI - /static/agent_hub.html

⚠️  注意：Agent API 需要 JWT 認證才能使用
        """)

if __name__ == "__main__":
    tester = AgentMCPTester()
    tester.run_tests()
