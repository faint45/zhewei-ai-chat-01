# -*- mode: python ; coding: utf-8 -*-
"""
築未科技大腦 - PyInstaller 打包配置
Build: pyinstaller brain_server.spec
"""

import sys
import os
from pathlib import Path

block_cipher = None
BASE_DIR = os.path.dirname(os.path.abspath('brain_server.py'))

# 收集數據文件
datas_list = [
    ('.env.example', '.'),
]

# 添加靜態資源（如果存在）
if os.path.exists('brain_workspace/static'):
    datas_list.append(('brain_workspace/static', 'brain_workspace/static'))

# 添加 JSON 配置文件
import glob
for json_file in glob.glob('*.json'):
    if os.path.isfile(json_file):
        datas_list.append((json_file, '.'))

# 收集所有 Python 源文件
a = Analysis(
    ['brain_server.py'],
    pathex=[BASE_DIR],
    binaries=[],
    datas=datas_list,
    hiddenimports=[
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'fastapi',
        'fastapi.staticfiles',
        'fastapi.middleware',
        'fastapi.middleware.cors',
        'google.generativeai',
        'anthropic',
        'httpx',
        'dotenv',
        'multipart',
        'ai_service',
        'agent_logic',
        'agent_tools',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'pytest',
        'PIL',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ZheweiTechBrain',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # 保留控制台以顯示日誌
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可添加 icon='icon.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ZheweiTechBrain',
)
