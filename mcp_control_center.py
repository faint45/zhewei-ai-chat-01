# -*- coding: utf-8 -*-
"""
MCP 控制中心 - 總指揮代理人工具
管理和控制所有 26 個 MCP 服務器
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional
import httpx

ROOT = Path(__file__).resolve().parent
MCP_CONFIG = ROOT / ".cursor" / "mcp.json"

class MCPControlCenter:
    """MCP 控制中心"""
    
    def __init__(self):
        self.config = self._load_config()
        self.servers = self.config.get("mcpServers", {})
        
    def _load_config(self) -> dict:
        """載入 MCP 配置"""
        if MCP_CONFIG.exists():
            with open(MCP_CONFIG, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"mcpServers": {}}
    
    def list_servers(self) -> List[Dict]:
        """列出所有 MCP 服務器"""
        servers = []
        for name, config in self.servers.items():
            server_type = "Python" if "python" in config["command"].lower() else "Node.js"
            servers.append({
                "name": name,
                "type": server_type,
                "command": config["command"],
                "args": config.get("args", []),
                "env": config.get("env", {})
            })
        return servers
    
    def get_server_info(self, name: str) -> Optional[Dict]:
        """取得特定服務器資訊"""
        if name in self.servers:
            config = self.servers[name]
            return {
                "name": name,
                "command": config["command"],
                "args": config.get("args", []),
                "env": config.get("env", {})
            }
        return None
    
    def categorize_servers(self) -> Dict[str, List[str]]:
        """分類 MCP 服務器"""
        categories = {
            "AI & 搜尋": ["brave-search", "open-web-search", "sequential-thinking", "memory-service", "arxiv-research"],
            "資料庫": ["sqlite-local", "postgres-dify", "redis-local", "weaviate-mcp", "qdrant-mcp"],
            "開發工具": ["github", "git", "docker-mcp", "playwright", "puppeteer"],
            "檔案系統": ["filesystem-restricted", "windows-mcp"],
            "地圖 & 導航": ["google-maps", "osm-geocode-mcp", "osrm-route-mcp"],
            "金融 & 數據": ["yahoo-finance"],
            "多媒體": ["ffmpeg-video"],
            "專業領域": ["construction-law-mcp", "dify-mcp", "sentry-mcp"],
            "網路工具": ["fetch"]
        }
        return categories
    
    def get_python_servers(self) -> List[str]:
        """取得所有 Python MCP 服務器"""
        python_servers = []
        for name, config in self.servers.items():
            if "python" in config["command"].lower():
                python_servers.append(name)
        return python_servers
    
    def get_nodejs_servers(self) -> List[str]:
        """取得所有 Node.js MCP 服務器"""
        nodejs_servers = []
        for name, config in self.servers.items():
            if "npx" in config["command"].lower():
                nodejs_servers.append(name)
        return nodejs_servers
    
    async def test_server(self, name: str) -> Dict:
        """測試 MCP 服務器是否可用"""
        if name not in self.servers:
            return {"ok": False, "error": "Server not found"}
        
        config = self.servers[name]
        command = config["command"]
        args = config.get("args", [])
        
        try:
            # 檢查 Python 服務器檔案是否存在
            if "python" in command.lower() and len(args) > 0:
                script_path = Path(args[0])
                if not script_path.exists():
                    return {
                        "ok": False,
                        "error": f"Script not found: {script_path}"
                    }
            
            return {
                "ok": True,
                "message": "Server configuration valid"
            }
        except Exception as e:
            return {
                "ok": False,
                "error": str(e)
            }
    
    def generate_usage_guide(self) -> str:
        """生成使用指南"""
        categories = self.categorize_servers()
        
        guide = "# MCP 工具使用指南\n\n"
        guide += f"## 總覽\n\n"
        guide += f"- **總計**: {len(self.servers)} 個 MCP 服務器\n"
        guide += f"- **Python**: {len(self.get_python_servers())} 個\n"
        guide += f"- **Node.js**: {len(self.get_nodejs_servers())} 個\n\n"
        
        for category, servers in categories.items():
            guide += f"## {category}\n\n"
            for server in servers:
                if server in self.servers:
                    config = self.servers[server]
                    guide += f"### {server}\n"
                    guide += f"- **類型**: {'Python' if 'python' in config['command'].lower() else 'Node.js'}\n"
                    guide += f"- **指令**: `{config['command']}`\n"
                    
                    # 環境變數
                    env = config.get("env", {})
                    if env:
                        guide += f"- **環境變數**:\n"
                        for key, value in env.items():
                            guide += f"  - `{key}`: {value}\n"
                    guide += "\n"
        
        return guide
    
    def check_dependencies(self) -> Dict[str, bool]:
        """檢查依賴是否安裝"""
        deps = {
            "mcp": False,
            "yfinance": False,
            "httpx": False,
            "node": False,
            "npx": False
        }
        
        # 檢查 Python 套件
        try:
            import mcp
            deps["mcp"] = True
        except ImportError:
            pass
        
        try:
            import yfinance
            deps["yfinance"] = True
        except ImportError:
            pass
        
        try:
            import httpx
            deps["httpx"] = True
        except ImportError:
            pass
        
        # 檢查 Node.js
        try:
            result = subprocess.run(["node", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                deps["node"] = True
        except FileNotFoundError:
            pass
        
        try:
            result = subprocess.run(["npx", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                deps["npx"] = True
        except FileNotFoundError:
            pass
        
        return deps
    
    def get_status_report(self) -> Dict:
        """取得狀態報告"""
        deps = self.check_dependencies()
        python_servers = self.get_python_servers()
        nodejs_servers = self.get_nodejs_servers()
        
        # 檢查 Python 服務器檔案
        python_files_ok = 0
        for server in python_servers:
            config = self.servers[server]
            args = config.get("args", [])
            if len(args) > 0:
                script_path = Path(args[0])
                if script_path.exists():
                    python_files_ok += 1
        
        return {
            "total_servers": len(self.servers),
            "python_servers": len(python_servers),
            "nodejs_servers": len(nodejs_servers),
            "python_files_ok": python_files_ok,
            "dependencies": deps,
            "ready": all([
                deps["mcp"],
                deps["httpx"],
                deps["node"],
                deps["npx"]
            ])
        }

# CLI 介面
async def main():
    center = MCPControlCenter()
    
    if len(sys.argv) < 2:
        print("🎯 MCP 控制中心 - 總指揮代理人工具")
        print("\n用法:")
        print("  python mcp_control_center.py list          # 列出所有服務器")
        print("  python mcp_control_center.py categories    # 顯示分類")
        print("  python mcp_control_center.py status        # 狀態報告")
        print("  python mcp_control_center.py guide         # 生成使用指南")
        print("  python mcp_control_center.py test <name>   # 測試服務器")
        print("  python mcp_control_center.py deps          # 檢查依賴")
        return
    
    command = sys.argv[1]
    
    if command == "list":
        servers = center.list_servers()
        print(f"\n📋 共 {len(servers)} 個 MCP 服務器:\n")
        for server in servers:
            print(f"  [{server['type']:8}] {server['name']}")
    
    elif command == "categories":
        categories = center.categorize_servers()
        print("\n📂 MCP 服務器分類:\n")
        for category, servers in categories.items():
            print(f"  {category}:")
            for server in servers:
                print(f"    - {server}")
            print()
    
    elif command == "status":
        status = center.get_status_report()
        print("\n📊 MCP 系統狀態:\n")
        print(f"  總服務器數: {status['total_servers']}")
        print(f"  Python 服務器: {status['python_servers']} ({status['python_files_ok']} 個檔案存在)")
        print(f"  Node.js 服務器: {status['nodejs_servers']}")
        print(f"\n  依賴狀態:")
        for dep, installed in status['dependencies'].items():
            status_icon = "✅" if installed else "❌"
            print(f"    {status_icon} {dep}")
        print(f"\n  系統就緒: {'✅ 是' if status['ready'] else '❌ 否'}")
    
    elif command == "guide":
        guide = center.generate_usage_guide()
        guide_path = ROOT / "docs" / "mcp_usage_guide.md"
        guide_path.parent.mkdir(exist_ok=True)
        guide_path.write_text(guide, encoding="utf-8")
        print(f"\n📖 使用指南已生成: {guide_path}")
    
    elif command == "test":
        if len(sys.argv) < 3:
            print("❌ 請指定服務器名稱")
            return
        
        server_name = sys.argv[2]
        result = await center.test_server(server_name)
        
        if result["ok"]:
            print(f"✅ {server_name}: {result['message']}")
        else:
            print(f"❌ {server_name}: {result['error']}")
    
    elif command == "deps":
        deps = center.check_dependencies()
        print("\n🔍 依賴檢查:\n")
        for dep, installed in deps.items():
            status_icon = "✅" if installed else "❌"
            print(f"  {status_icon} {dep}")

if __name__ == "__main__":
    asyncio.run(main())
