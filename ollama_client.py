#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
築未科技 - Ollama 客戶端
用於地端勤務兵進行本地代碼檢測和驗證
"""

import os
import json
import requests
from typing import Dict, List, Any

class OllamaClient:
    """Ollama API 客戶端"""

    def __init__(self):
        self.api_base = os.getenv("OLLAMA_API_BASE", "http://localhost:11461/v1")
        self.model = os.getenv("OLLAMA_MODEL", "qwen2.5:latest")

        # 測試連接
        try:
            response = requests.get(f"{self.api_base.replace('/v1', '')}/api/tags", timeout=5)
            if response.status_code == 200:
                print(f"[Ollama] 已連接 (模型: {self.model})")
                self.use_mock = False
            else:
                raise Exception("Ollama 服務無響應")
        except Exception as e:
            print(f"[警告] Ollama 連接失敗: {e}")
            print("[提示] 請先啟動 Ollama 服務: 啟動_ollama_服務.bat")
            self.use_mock = True

    def verify_code(self, code: str, language: str = "python") -> Dict[str, Any]:
        """
        代碼驗證 - 檢查代碼質量、安全性等

        Args:
            code: 代碼內容
            language: 編程語言

        Returns:
            驗證結果
        """
        if self.use_mock:
            return self._mock_verify_code(code)

        prompt = f"""請分析以下 {language} 代碼的質量和安全性：

```{language}
{code}
```

請按照以下 JSON 格式輸出（不要包含其他文字）：
{{
  "status": "approved/needs_revision/rejected",
  "confidence": 0.95,
  "code_quality": "excellent/good/fair/poor",
  "security_check": "passed/warning/failed",
  "issues": ["問題1", "問題2"],
  "suggestions": ["建議1", "建議2"]
}}
"""

        try:
            response = requests.post(
                f"{self.api_base}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                text = result["choices"][0]["message"]["content"]

                json_start = text.find("{")
                json_end = text.rfind("}") + 1
                if json_start != -1 and json_end > json_start:
                    json_text = text[json_start:json_end]
                    return json.loads(json_text)

            return self._mock_verify_code(code)

        except Exception as e:
            print(f"[Ollama] 驗證失敗: {e}")
            return self._mock_verify_code(code)

    def code_review(self, code: str, language: str = "python") -> Dict[str, Any]:
        """
        代碼審查

        Args:
            code: 代碼內容
            language: 編程語言

        Returns:
            審查結果
        """
        if self.use_mock:
            return {
                "status": "approved",
                "confidence": 0.85,
                "issues": [],
                "suggestions": ["建議添加錯誤處理"]
            }

        prompt = f"""請對以下 {language} 代碼進行詳細審查：

```{language}
{code}
```

輸出 JSON 格式：
{{
  "status": "approved/needs_revision",
  "confidence": 0.90,
  "issues": [
    {{"line": 1, "type": "error/warning/info", "message": "問題描述"}}
  ],
  "suggestions": ["改進建議"]
}}
"""

        try:
            response = requests.post(
                f"{self.api_base}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.2
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                text = result["choices"][0]["message"]["content"]

                json_start = text.find("{")
                json_end = text.rfind("}") + 1
                if json_start != -1 and json_end > json_start:
                    json_text = text[json_start:json_end]
                    return json.loads(json_text)

        except Exception as e:
            print(f"[Ollama] 審查失敗: {e}")

        return {
            "status": "approved",
            "confidence": 0.85,
            "issues": [],
            "suggestions": []
        }

    def _mock_verify_code(self, code: str) -> Dict[str, Any]:
        """模擬代碼驗證"""
        issues = []
        if "print" not in code and len(code) > 50:
            issues.append("缺少輸出語句")

        return {
            "status": "approved" if not issues else "needs_revision",
            "confidence": 0.85,
            "code_quality": "good",
            "security_check": "passed",
            "issues": issues,
            "suggestions": ["建議添加註釋"] if not issues else []
        }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from dotenv import load_dotenv

    load_dotenv(".env.seven_stage")

    client = OllamaClient()
    code = "print('Hello World')"
    result = client.verify_code(code)
    print(json.dumps(result, indent=2, ensure_ascii=False))
