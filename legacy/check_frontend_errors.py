#!/usr/bin/env python3
"""
前端 JavaScript 錯誤檢查工具
檢查所有 HTML/JS 檔案中的常見低端錯誤
"""
import re
from pathlib import Path
from collections import defaultdict

class FrontendErrorChecker:
    def __init__(self):
        self.errors = defaultdict(list)
        self.warnings = defaultdict(list)
        
    def check_html_file(self, filepath):
        """檢查單一 HTML 檔案"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取所有 getElementById 調用
            get_by_id_pattern = r"getElementById\(['\"]([^'\"]+)['\"]\)"
            get_by_id_calls = re.findall(get_by_id_pattern, content)
            
            # 提取所有 id 定義
            id_definitions = re.findall(r'id=["\']([^"\']+)["\']', content)
            
            # 檢查未定義的 ID
            for element_id in get_by_id_calls:
                if element_id not in id_definitions:
                    self.errors[filepath].append({
                        "type": "未定義的元素 ID",
                        "id": element_id,
                        "severity": "high"
                    })
            
            # 檢查 onclick 引用的函數
            onclick_pattern = r'onclick=["\']([^"\'(]+)\('
            onclick_functions = re.findall(onclick_pattern, content)
            
            # 提取所有函數定義
            function_pattern = r'function\s+(\w+)\s*\('
            function_definitions = re.findall(function_pattern, content)
            
            for func in onclick_functions:
                if func not in function_definitions:
                    self.warnings[filepath].append({
                        "type": "未定義的函數",
                        "function": func,
                        "severity": "medium"
                    })
            
            # 檢查 querySelector 空值處理
            queryselector_pattern = r'(querySelector[All]*\([^)]+\))(?!\s*\?\.)'
            queryselector_calls = re.findall(queryselector_pattern, content)
            
            if queryselector_calls:
                self.warnings[filepath].append({
                    "type": "querySelector 可能返回 null",
                    "count": len(queryselector_calls),
                    "severity": "low"
                })
            
            # 檢查未處理的 Promise
            promise_pattern = r'\.then\([^)]+\)(?!\s*\.catch)'
            unhandled_promises = re.findall(promise_pattern, content)
            
            if unhandled_promises:
                self.warnings[filepath].append({
                    "type": "Promise 缺少 .catch() 錯誤處理",
                    "count": len(unhandled_promises),
                    "severity": "medium"
                })
            
            # 檢查 console.log (生產環境應移除)
            console_logs = len(re.findall(r'console\.log\(', content))
            if console_logs > 5:
                self.warnings[filepath].append({
                    "type": "過多 console.log",
                    "count": console_logs,
                    "severity": "low"
                })
            
        except Exception as e:
            self.errors[filepath].append({
                "type": "檔案讀取錯誤",
                "error": str(e),
                "severity": "critical"
            })
    
    def scan_directory(self, directory, patterns=['*.html', '*.js']):
        """掃描目錄"""
        path = Path(directory)
        
        for pattern in patterns:
            for filepath in path.rglob(pattern):
                # 跳過 node_modules 和 .git
                if 'node_modules' in str(filepath) or '.git' in str(filepath):
                    continue
                
                self.check_html_file(filepath)
    
    def generate_report(self):
        """生成報告"""
        print("\n" + "="*60)
        print("🔍 前端 JavaScript 錯誤檢查報告")
        print("="*60)
        
        total_errors = sum(len(errs) for errs in self.errors.values())
        total_warnings = sum(len(warns) for warns in self.warnings.values())
        
        print(f"\n📊 總計:")
        print(f"   ❌ 錯誤: {total_errors}")
        print(f"   ⚠️  警告: {total_warnings}")
        
        # 顯示錯誤
        if self.errors:
            print("\n" + "="*60)
            print("❌ 嚴重錯誤（需立即修正）")
            print("="*60)
            
            for filepath, errors in self.errors.items():
                if errors:
                    print(f"\n📄 {filepath}")
                    for error in errors:
                        print(f"   ❌ {error['type']}")
                        if 'id' in error:
                            print(f"      元素 ID: {error['id']}")
                        if 'function' in error:
                            print(f"      函數名: {error['function']}")
                        if 'error' in error:
                            print(f"      錯誤: {error['error']}")
        
        # 顯示警告
        if self.warnings:
            print("\n" + "="*60)
            print("⚠️  警告（建議修正）")
            print("="*60)
            
            for filepath, warnings in self.warnings.items():
                if warnings:
                    print(f"\n📄 {filepath}")
                    for warning in warnings:
                        print(f"   ⚠️  {warning['type']}")
                        if 'count' in warning:
                            print(f"      數量: {warning['count']}")
        
        # 總結
        print("\n" + "="*60)
        if total_errors == 0 and total_warnings == 0:
            print("✅ 未發現明顯錯誤！")
        elif total_errors == 0:
            print(f"✅ 未發現嚴重錯誤，但有 {total_warnings} 個警告")
        else:
            print(f"⚠️  發現 {total_errors} 個錯誤和 {total_warnings} 個警告")
        print("="*60)

if __name__ == "__main__":
    checker = FrontendErrorChecker()
    
    # 檢查主要前端檔案
    print("🔍 掃描前端檔案...")
    
    directories = [
        "d:/zhe-wei-tech/bridge_workspace/static",
        "d:/zhe-wei-tech/brain_workspace/static",
        "d:/zhe-wei-tech/portal",
        "d:/AI_Vision_Recognition/web_static",
        "d:/zhe-wei-tech/construction_mgmt/templates",
    ]
    
    for directory in directories:
        if Path(directory).exists():
            print(f"   掃描: {directory}")
            checker.scan_directory(directory)
    
    checker.generate_report()
