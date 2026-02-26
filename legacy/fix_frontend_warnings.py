#!/usr/bin/env python3
"""
自動修正前端警告的腳本
"""
import re
from pathlib import Path
from typing import List, Tuple

class FrontendFixer:
    def __init__(self):
        self.fixes_applied = []
        
    def fix_promise_catch(self, content: str, filepath: str) -> Tuple[str, int]:
        """修正 Promise 缺少 .catch() 的問題"""
        fixes = 0
        
        # 匹配 .then() 後沒有 .catch() 的情況
        # 只處理明確的 fetch 和 Promise 調用
        patterns = [
            # fetch().then().then() 沒有 catch
            (r'(fetch\([^)]+\)(?:\s*\.then\([^}]+\}?\))+)(?!\s*\.catch)', 
             r'\1.catch(err => console.error("請求錯誤:", err))'),
            
            # Promise.then() 沒有 catch（單行）
            (r'(\w+\.then\([^}]+\))(?=\s*;)(?!\s*\.catch)',
             r'\1.catch(err => console.error("錯誤:", err))'),
        ]
        
        for pattern, replacement in patterns:
            new_content, count = re.subn(pattern, replacement, content)
            if count > 0:
                content = new_content
                fixes += count
                self.fixes_applied.append({
                    'file': filepath,
                    'type': 'Promise .catch()',
                    'count': count
                })
        
        return content, fixes
    
    def fix_queryselector_null(self, content: str, filepath: str) -> Tuple[str, int]:
        """修正 querySelector 可能返回 null 的問題"""
        fixes = 0
        
        # 匹配 querySelector 後直接訪問屬性的情況
        patterns = [
            # querySelector().property
            (r'(document\.querySelector\([^)]+\))\.(\w+)',
             r'\1?.\2'),
            
            # querySelectorAll().forEach
            (r'(document\.querySelectorAll\([^)]+\))\.forEach',
             r'Array.from(\1 || []).forEach'),
        ]
        
        for pattern, replacement in patterns:
            new_content, count = re.subn(pattern, replacement, content)
            if count > 0:
                content = new_content
                fixes += count
                self.fixes_applied.append({
                    'file': filepath,
                    'type': 'querySelector null check',
                    'count': count
                })
        
        return content, fixes
    
    def fix_console_log(self, content: str, filepath: str) -> Tuple[str, int]:
        """清理 console.log（僅在 Service Worker 中）"""
        fixes = 0
        
        if 'sw.js' in str(filepath):
            # 將 console.log 改為條件式
            pattern = r'console\.log\('
            replacement = 'if (self.DEBUG) console.log('
            
            # 先在檔案開頭加入 DEBUG 標誌
            if 'self.DEBUG' not in content:
                content = '// Debug mode\nconst DEBUG = false;\n\n' + content
            
            new_content, count = re.subn(pattern, replacement, content)
            if count > 0:
                content = new_content
                fixes += count
                self.fixes_applied.append({
                    'file': filepath,
                    'type': 'console.log cleanup',
                    'count': count
                })
        
        return content, fixes
    
    def process_file(self, filepath: Path):
        """處理單一檔案"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            total_fixes = 0
            
            # 應用所有修正
            content, fixes = self.fix_promise_catch(content, str(filepath))
            total_fixes += fixes
            
            content, fixes = self.fix_queryselector_null(content, str(filepath))
            total_fixes += fixes
            
            content, fixes = self.fix_console_log(content, str(filepath))
            total_fixes += fixes
            
            # 如果有修改，寫回檔案
            if content != original_content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✅ 修正 {filepath.name}: {total_fixes} 處")
                return total_fixes
            
            return 0
            
        except Exception as e:
            print(f"❌ 處理 {filepath} 時發生錯誤: {e}")
            return 0
    
    def scan_and_fix(self, directories: List[str]):
        """掃描並修正所有檔案"""
        print("\n" + "="*60)
        print("🔧 開始自動修正前端警告")
        print("="*60)
        
        total_files = 0
        total_fixes = 0
        
        for directory in directories:
            path = Path(directory)
            if not path.exists():
                continue
            
            print(f"\n📁 掃描目錄: {directory}")
            
            for pattern in ['*.html', '*.js']:
                for filepath in path.rglob(pattern):
                    if 'node_modules' in str(filepath) or '.git' in str(filepath):
                        continue
                    
                    fixes = self.process_file(filepath)
                    if fixes > 0:
                        total_files += 1
                        total_fixes += fixes
        
        print("\n" + "="*60)
        print("📊 修正完成")
        print("="*60)
        print(f"修正檔案數: {total_files}")
        print(f"修正總數: {total_fixes}")
        
        if self.fixes_applied:
            print("\n詳細修正列表:")
            for fix in self.fixes_applied:
                print(f"  • {Path(fix['file']).name}: {fix['type']} ({fix['count']} 處)")

if __name__ == "__main__":
    fixer = FrontendFixer()
    
    directories = [
        "d:/zhe-wei-tech/bridge_workspace/static",
        "d:/zhe-wei-tech/brain_workspace/static",
        "d:/zhe-wei-tech/portal",
        "d:/AI_Vision_Recognition/web_static",
    ]
    
    fixer.scan_and_fix(directories)
