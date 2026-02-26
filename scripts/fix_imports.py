#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修復移動後的Python導入語句
"""
import os
import re
from pathlib import Path

# 定義舊路徑到新路徑的映射
IMPORT_MAPPINGS = {
    # brain_core (不需要改，因為這些是入口文件)
    
    # brain_modules
    'brain_knowledge': 'brain_modules.brain_knowledge',
    'brain_learner': 'brain_modules.brain_learner',
    'brain_rag': 'brain_modules.brain_rag',
    'brain_retrieve': 'brain_modules.brain_retrieve',
    'brain_self_learner': 'brain_modules.brain_self_learner',
    'brain_github_learner': 'brain_modules.brain_github_learner',
    
    # ai_modules
    'ai_brain': 'ai_modules.ai_brain',
    'ai_brain_pro': 'ai_modules.ai_brain_pro',
    'ai_cost_tracker': 'ai_modules.ai_cost_tracker',
    'ai_creative_tools': 'ai_modules.ai_creative_tools',
    'ai_market_scanner': 'ai_modules.ai_market_scanner',
    'ai_providers': 'ai_modules.ai_providers',
    'ai_vision_monitor': 'ai_modules.ai_vision_monitor',
    'ai_vision_tools': 'ai_modules.ai_vision_tools',
    
    # agents (已歸檔至 archive/agents_legacy/)
    
    # tools
    'code_writer': 'tools.code_writer',
    'connection_monitor': 'tools.connection_monitor',
    'cursor_watcher': 'tools.cursor_watcher',
    'dashboard': 'tools.dashboard',
    'data_archiver': 'tools.data_archiver',
    'edge_compute': 'tools.edge_compute',
    'get_api_keys': 'tools.get_api_keys',
    'guard_core': 'tools.guard_core',
    'integration_gateway': 'tools.integration_gateway',
    'memory_mem0': 'tools.memory_mem0',
    'ollama_client': 'tools.ollama_client',
    'proxy_switcher': 'tools.proxy_switcher',
    'reasoning_tracer': 'tools.reasoning_tracer',
    'storage_manager': 'tools.storage_manager',
    'tcp_forwarder': 'tools.tcp_forwarder',
    'url_tree': 'tools.url_tree',
    'video_learner': 'tools.video_learner',
    'codebuddy_integration': 'tools.codebuddy_integration',
    'dev_output': 'tools.dev_output',
    'hls_parser_example': 'tools.hls_parser_example',
    'power_test': 'tools.power_test',
    'selector_server': 'tools.selector_server',
    'shadow_monitor': 'tools.shadow_monitor',
    'simple_dashboard': 'tools.simple_dashboard',
    'skill_dispatch': 'tools.skill_dispatch',
    'chat_console': 'tools.chat_console',
    'chat_gui': 'tools.chat_gui',
    'aes_decrypt_example': 'tools.aes_decrypt_example',
    'messenger_dashboard': 'tools.messenger_dashboard',
    'messenger_probe': 'tools.messenger_probe',
    'messenger_switcher': 'tools.messenger_switcher',
    'run_bot': 'tools.run_bot',
    'run_bot_final': 'tools.run_bot_final',
    'run_bot_live_view': 'tools.run_bot_live_view',
    'run_bot_secure': 'tools.run_bot_secure',
    'run_bot_v3': 'tools.run_bot_v3',
}

def fix_imports_in_file(file_path):
    """修復單個文件中的導入語句"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 修復 from imports
        for old_import, new_import in IMPORT_MAPPINGS.items():
            # from old_import import ... → from new_import import ...
            pattern = rf'from\s+{old_import}\.?(\w*)\s+import'
            replacement = rf'from {new_import}.\1 import'
            content = re.sub(pattern, replacement, content)
            
            # import old_import → import new_import
            pattern = rf'^import\s+{old_import}\b'
            replacement = f'import {new_import}'
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        # 如果內容有改變，寫回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[更新] 已更新: {file_path}")
            return True
        else:
            print(f"[跳過] 無需更新: {file_path}")
            return False
            
    except Exception as e:
        print(f"[錯誤] 處理 {file_path}: {e}")
        return False

def main():
    """主函數"""
    project_root = Path('D:/zhe-wei-tech')
    
    # 要處理的目錄（排除scripts和public）
    target_dirs = ['brain_core', 'brain_modules', 'ai_modules', 'tools', 'config']
    
    total_files = 0
    updated_files = 0
    
    for dir_name in target_dirs:
        dir_path = project_root / dir_name
        if not dir_path.exists():
            continue
            
        # 找到所有.py文件
        py_files = list(dir_path.glob('*.py'))
        total_files += len(py_files)
        
        print(f"\n[目錄] 處理: {dir_name} ({len(py_files)} 個文件)")
        
        for py_file in py_files:
            if fix_imports_in_file(py_file):
                updated_files += 1
    
    print(f"\n" + "="*60)
    print(f"[總結] 處理 {total_files} 個文件，更新 {updated_files} 個文件")
    print("="*60)

if __name__ == '__main__':
    main()
