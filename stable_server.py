#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
築未科技穩定遠程控制服務器
確保端口和連接穩定性
"""

import socket
import time
import sys
from fastapi import FastAPI
import uvicorn

# 檢查端口是否可用
def check_port_available(port):
    """檢查端口是否可用"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        result = sock.bind(('0.0.0.0', port))
        sock.close()
        return True
    except:
        return False

# 找到可用的端口
def find_available_port(start_port=8000, max_port=8010):
    """找到可用的端口"""
    for port in range(start_port, max_port + 1):
        if check_port_available(port):
            return port
    return None

app = FastAPI(title="築未科技穩定遠程控制服務器")

@app.get("/")
async def root():
    return {
        "message": "築未科技穩定服務器運行正常", 
        "status": "stable",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "uptime": "stable",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

@app.get("/port-info")
async def port_info():
    return {
        "current_port": "自動檢測",
        "status": "stable",
        "description": "自動檢測可用端口，確保連接穩定"
    }

if __name__ == "__main__":
    print("啟動築未科技穩定遠程控制服務器...")
    
    # 自動檢測可用端口
    available_port = find_available_port(8000, 8010)
    
    if available_port is None:
        print("錯誤: 找不到可用端口 (8000-8010)")
        sys.exit(1)
    
    print(f"找到可用端口: {available_port}")
    print(f"訪問地址: http://localhost:{available_port}")
    print(f"健康檢查: http://localhost:{available_port}/health")
    
    # 配置服務器
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=available_port,
        log_level="info",
        access_log=True,
        timeout_keep_alive=60,
        timeout_graceful_shutdown=30
    )
    
    server = uvicorn.Server(config)
    
    try:
        server.run()
    except KeyboardInterrupt:
        print("服務器正常關閉")
    except Exception as e:
        print(f"服務器錯誤: {e}")
        print("嘗試重啟服務器...")
        time.sleep(5)
        server.run()