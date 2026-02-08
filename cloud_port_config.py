#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
築未科技 - 雲端口配置系統
統一API系統的雲端部署配置
"""

import os
import json
import yaml
from typing import Dict, Any

class CloudPortConfig:
    """雲端口配置管理器"""
    
    def __init__(self):
        self.configs = {
            "vercel": {
                "port": "自動分配（80/443）",
                "protocol": "https",
                "domain": "自定義域名或默認域名",
                "features": ["自動SSL", "全球CDN", "無需端口配置"]
            },
            "cloudbase": {
                "port": "自動分配（80/443）",
                "protocol": "https", 
                "domain": "自定義域名或騰訊雲域名",
                "features": ["國內加速", "自動備份", "無需端口配置"]
            },
            "netlify": {
                "port": "自動分配（80/443）",
                "protocol": "https",
                "domain": "自定義域名或netlify.app域名",
                "features": ["自動部署", "無服務器函數", "無需端口配置"]
            },
            "railway": {
                "port": "動態分配（$PORT環境變量）",
                "protocol": "https",
                "domain": "自定義域名或railway.app域名",
                "features": ["Docker支持", "自動擴展", "數據庫集成"]
            }
        }
    
    def generate_vercel_config(self, port: int = 8006) -> Dict[str, Any]:
        """生成Vercel部署配置"""
        return {
            "version": 2,
            "builds": [
                {
                    "src": "remote_control_server.py",
                    "use": "@vercel/python",
                    "config": {
                        "maxLambdaSize": "50mb",
                        "runtime": "python3.9"
                    }
                },
                {
                    "src": "unified_api_dashboard.py", 
                    "use": "@vercel/python",
                    "config": {
                        "maxLambdaSize": "50mb",
                        "runtime": "python3.9"
                    }
                },
                {
                    "src": "static/**",
                    "use": "@vercel/static"
                }
            ],
            "routes": [
                {
                    "src": "/v1/execute",
                    "dest": "/remote_control_server.py"
                },
                {
                    "src": "/dashboard",
                    "dest": "/unified_api_dashboard.py"
                },
                {
                    "src": "/static/(.*)",
                    "dest": "/static/$1"
                },
                {
                    "src": "/(.*)",
                    "dest": "/remote_control_server.py"
                }
            ],
            "env": {
                "PYTHONPATH": ".",
                "CLOUD_PORT": str(port),
                "CLOUD_DEPLOYMENT": "true"
            },
            "functions": {
                "remote_control_server.py": {
                    "maxDuration": 60
                },
                "unified_api_dashboard.py": {
                    "maxDuration": 30
                }
            }
        }
    
    def generate_cloudbase_config(self) -> Dict[str, Any]:
        """生成騰訊雲CloudBase配置"""
        return {
            "cloudbase": {
                "envId": "zhewei-ai-system",
                "framework": {
                    "name": "zhewei-unified-api",
                    "plugins": {
                        "server": {
                            "use": "@cloudbase/framework-plugin-node",
                            "inputs": {
                                "entry": "./remote_control_server.py",
                                "path": "/api",
                                "name": "zhewei-api",
                                "wrapExpress": True
                            }
                        },
                        "dashboard": {
                            "use": "@cloudbase/framework-plugin-node", 
                            "inputs": {
                                "entry": "./unified_api_dashboard.py",
                                "path": "/dashboard",
                                "name": "zhewei-dashboard",
                                "wrapExpress": True
                            }
                        }
                    }
                }
            }
        }
    
    def generate_railway_config(self, port: int = 8006) -> Dict[str, Any]:
        """生成Railway配置"""
        return {
            "build": {
                "builder": "NIXPACKS"
            },
            "deploy": {
                "startCommand": f"python remote_control_server.py --port {port}",
                "healthcheckPath": "/health",
                "restartPolicyType": "ON_FAILURE"
            },
            "services": [
                {
                    "name": "zhewei-api",
                    "source": {
                        "type": "image",
                        "image": "python:3.9"
                    },
                    "env": {
                        "PORT": str(port),
                        "PYTHONPATH": "."
                    }
                }
            ]
        }
    
    def create_cloud_deployment_files(self):
        """創建雲部署配置文件"""
        
        # Vercel配置
        vercel_config = self.generate_vercel_config()
        with open('vercel_api.json', 'w', encoding='utf-8') as f:
            json.dump(vercel_config, f, indent=2, ensure_ascii=False)
        
        # CloudBase配置
        cloudbase_config = self.generate_cloudbase_config()
        with open('cloudbase.json', 'w', encoding='utf-8') as f:
            json.dump(cloudbase_config, f, indent=2, ensure_ascii=False)
        
        # Railway配置
        railway_config = self.generate_railway_config()
        with open('railway.toml', 'w', encoding='utf-8') as f:
            f.write("# Railway部署配置\n")
            f.write(f"port = {8006}\n\n")
            f.write("[build]\n")
            f.write('builder = "NIXPACKS"\n\n')
            f.write("[deploy]\n")
            f.write(f'startCommand = "python remote_control_server.py --port {8006}"\n')
        
        # 環境變量文件
        env_content = """# 築未科技雲端配置
CLOUD_DEPLOYMENT=true
PORT=8006
PYTHONPATH=.
API_BASE_URL=https://your-domain.vercel.app
DASHBOARD_URL=https://your-domain.vercel.app/dashboard

# 安全配置
JWT_SECRET=your-secret-key-here
CORS_ORIGINS=https://your-domain.vercel.app

# 數據庫配置（可選）
# DATABASE_URL=your-database-url
"""
        
        with open('.env.cloud', 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        print("雲端口配置文件已創建")
        print("生成的文件:")
        print("   - vercel_api.json (Vercel配置)")
        print("   - cloudbase.json (騰訊雲配置)")
        print("   - railway.toml (Railway配置)")
        print("   - .env.cloud (環境變量)")
    
    def show_cloud_port_info(self):
        """顯示雲端口信息"""
        print("築未科技 - 雲端口配置指南")
        print("=" * 50)
        print()
        
        for platform, config in self.configs.items():
            print(f"{platform.upper()}:")
            print(f"   端口: {config['port']}")
            print(f"   協議: {config['protocol']}")
            print(f"   域名: {config['domain']}")
            print(f"   特性: {', '.join(config['features'])}")
            print()
        
        print("雲端部署優勢:")
        print("   • 無需手動配置端口轉發")
        print("   • 自動SSL證書（HTTPS）")
        print("   • 全球CDN加速")
        print("   • 99.9% 服務可用性")
        print("   • 自動擴展和負載均衡")
        print()
        print("推薦部署流程:")
        print("   1. 選擇雲服務提供商")
        print("   2. 上傳項目文件")
        print("   3. 配置自定義域名（可選）")
        print("   4. 獲取永久訪問地址")

if __name__ == "__main__":
    config = CloudPortConfig()
    config.create_cloud_deployment_files()
    print("\n" + "="*50)
    config.show_cloud_port_info()