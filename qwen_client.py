#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通義千問/元寶 API 客戶端
Qianwen / Yuanbao API Client for Seven-Stage System
"""

import os
import json
import httpx
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class QwenMessage:
    role: str
    content: str


class QwenClient:
    """通義千問 API 客戶端"""

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化通義千問客戶端

        Args:
            api_key: DashScope API 密鑰，默認從環境變量讀取
        """
        # 從 .openclaw/.env 讀取 API 密鑰
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            # 嘗試從 .openclaw/.env 文件讀取
            openclaw_env = os.path.expanduser("~/.openclaw/.env")
            if os.path.exists(openclaw_env):
                with open(openclaw_env, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith('DASHSCOPE_API_KEY='):
                            self.api_key = line.split('=', 1)[1].strip()
                            break

        if not self.api_key:
            raise ValueError("未找到 DASHSCOPE_API_KEY，請設置環境變量或確保 .openclaw/.env 文件存在")

        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        self.client = httpx.Client(timeout=60.0)

        print("[通義千問] 已初始化 API 客戶端")

    def chat(
        self,
        messages: List[QwenMessage],
        model: str = "qwen-plus",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        發送聊天請求

        Args:
            messages: 消息列表
            model: 模型名稱 (qwen-plus, qwen-turbo)
            temperature: 溫度參數
            max_tokens: 最大 token 數
            stream: 是否流式輸出

        Returns:
            API 響應結果
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ],
            "temperature": temperature,
            "stream": stream
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        response = self.client.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload
        )

        response.raise_for_status()
        return response.json()

    def generate(
        self,
        prompt: str,
        model: str = "qwen-plus",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        生成文本（便捷方法）

        Args:
            prompt: 提示詞
            model: 模型名稱
            temperature: 溫度參數
            max_tokens: 最大 token 數

        Returns:
            生成的文本
        """
        messages = [QwenMessage(role="user", content=prompt)]
        response = self.chat(messages, model, temperature, max_tokens)

        return response["choices"][0]["message"]["content"]

    def code_review(
        self,
        code: str,
        language: str = "python"
    ) -> Dict[str, Any]:
        """
        代碼審查（工程術語檢核）

        Args:
            code: 代碼內容
            language: 編程語言

        Returns:
            審查結果
        """
        prompt = f"""你是一個專業的代碼審查專家。請審查以下 {language} 代碼。

代碼：
```{language}
{code}
```

請檢查以下方面：
1. 語法錯誤
2. 邏輯問題
3. 性能優化
4. 安全性問題
5. 代碼風格

請以 JSON 格式返回審查結果：
{{
  "status": "passed|needs_revision|failed",
  "confidence": 0.95,
  "issues": [
    {{
      "type": "syntax|logic|performance|security|style",
      "description": "問題描述",
      "line": 10,
      "severity": "critical|high|medium|low"
    }}
  ],
  "suggestions": ["改進建議"]
}}

只返回 JSON，不要其他內容。"""

        try:
            result = self.generate(prompt, model="qwen-plus")
            # 解析 JSON
            return json.loads(result)
        except json.JSONDecodeError:
            return {
                "status": "failed",
                "confidence": 0.0,
                "issues": [],
                "suggestions": ["解析失敗，請重試"]
            }

    def retrieve_info(
        self,
        query: str,
        context: Optional[str] = None
    ) -> str:
        """
        中文信息檢索

        Args:
            query: 查詢問題
            context: 額外上下文

        Returns:
            檢索結果
        """
        prompt = f"""請用繁體中文回答以下問題。

問題：{query}

{f"上下文：{context}" if context else ""}

請提供準確、詳細的回答。如果不知道答案，請說明。"""

        return self.generate(prompt, model="qwen-plus")

    def verify_result(
        self,
        task_description: str,
        result: Any
    ) -> Dict[str, Any]:
        """
        異構驗證（第二意見）

        Args:
            task_description: 任務描述
            result: 執行結果

        Returns:
            驗證結果
        """
        result_str = json.dumps(result, indent=2, ensure_ascii=False) if isinstance(result, dict) else str(result)

        prompt = f"""你是一個嚴格的驗證專家。請驗證以下任務的執行結果。

任務描述：{task_description}

執行結果：
{result_str}

請評估：
1. 結果是否完整
2. 結果是否準確
3. 是否存在邏輯錯誤
4. 是否需要退回重做

請以 JSON 格式返回驗證結果：
{{
  "status": "approved|needs_revision|rejected",
  "confidence": 0.95,
  "issues": [
    {{
      "type": "completeness|accuracy|logic|other",
      "description": "問題描述",
      "severity": "critical|high|medium|low"
    }}
  ],
  "revision_required": false,
  "suggestions": ["改進建議"]
}}

只返回 JSON，不要其他內容。"""

        try:
            result_text = self.generate(prompt, model="qwen-plus")
            return json.loads(result_text)
        except json.JSONDecodeError:
            return {
                "status": "approved",
                "confidence": 0.5,
                "issues": [],
                "revision_required": False,
                "suggestions": []
            }

    def close(self):
        """關閉客戶端"""
        self.client.close()


# 測試代碼
if __name__ == "__main__":
    print("測試通義千問 API...\n")

    # 初始化客戶端
    client = QwenClient()

    # 測試 1：基本對話
    print("=" * 50)
    print("測試 1：基本對話")
    print("=" * 50)
    response = client.generate("你好，請簡單自我介紹")
    print(f"回應：{response}\n")

    # 測試 2：代碼審查
    print("=" * 50)
    print("測試 2：代碼審查")
    print("=" * 50)
    test_code = """
def add(a, b):
    return a + b

x = add(5, 10)
print(x)
"""
    review = client.code_review(test_code, language="python")
    print(f"審查結果：{json.dumps(review, indent=2, ensure_ascii=False)}\n")

    # 測試 3：信息檢索
    print("=" * 50)
    print("測試 3：中文信息檢索")
    print("=" * 50)
    info = client.retrieve_info("什麼是人工智能？")
    print(f"檢索結果：{info}\n")

    # 測試 4：異構驗證
    print("=" * 50)
    print("測試 4：異構驗證")
    print("=" * 50)
    verification = client.verify_result(
        task_description="計算 5 + 3",
        result={"result": 8, "method": "addition"}
    )
    print(f"驗證結果：{json.dumps(verification, indent=2, ensure_ascii=False)}\n")

    # 關閉客戶端
    client.close()

    print("=" * 50)
    print("測試完成！")
    print("=" * 50)
