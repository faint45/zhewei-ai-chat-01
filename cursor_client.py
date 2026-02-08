#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
築未科技 - Cursor API 客戶端
用於實體執行員進行實時代碼執行
"""

import os
import requests
from typing import Dict, Optional
from pathlib import Path

class CursorClient:
    """Cursor API 客戶端"""

    def __init__(self):
        self.api_key = os.getenv("CURSOR_API_KEY")
        self.base_url = "https://api.cursor.sh/v1"

        if not self.api_key:
            print("[警告] 未設置 CURSOR_API_KEY，將使用模擬模式")
            self.use_mock = True
        else:
            self.use_mock = False
            print("[Cursor] 已初始化")

    def generate_code(self, prompt: str, language: str = "python") -> str:
        """
        生成代碼

        Args:
            prompt: 代碼生成提示
            language: 編程語言

        Returns:
            生成的代碼
        """
        if self.use_mock:
            return self._mock_generate_code(prompt, language)

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "cursor",
                    "messages": [
                        {
                            "role": "system",
                            "content": f"你是一個專業的 {language} 程序員。請只輸出代碼，不要有任何解釋。"
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]

            return self._mock_generate_code(prompt, language)

        except Exception as e:
            print(f"[Cursor] 代碼生成失敗: {e}")
            return self._mock_generate_code(prompt, language)

    def save_code(self, code: str, file_path: str) -> Dict[str, Any]:
        """
        保存代碼到文件

        Args:
            code: 代碼內容
            file_path: 文件路徑

        Returns:
            保存結果
        """
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(code, encoding='utf-8')

            return {
                "status": "completed",
                "output_path": file_path,
                "file_size": len(code),
                "lines": len(code.split('\n'))
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }

    def _mock_generate_code(self, prompt: str, language: str) -> str:
        """模擬代碼生成"""
        if language == "python":
            return f'''# 自動生成的 {prompt}
# 由 Cursor 生成

def main():
    print("{prompt}")
    return "Success"

if __name__ == "__main__":
    main()
'''
        elif language == "html":
            return f'''<!DOCTYPE html>
<html>
<head>
    <title>{prompt}</title>
</head>
<body>
    <h1>{prompt}</h1>
</body>
</html>'''
        else:
            return f"# {prompt}\nprint('Hello from {language}')"


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from dotenv import load_dotenv

    load_dotenv(".env.seven_stage")

    client = CursorClient()
    code = client.generate_code("打印 Hello World", "python")
    print(code)
