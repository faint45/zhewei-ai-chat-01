"""
築未科技 - 開啟各 AI 服務的 API Key 取得頁面
API Key 需本人註冊取得，無法自動生成
"""
import sys
import webbrowser
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LINKS = [
    ("Gemini", "GEMINI_API_KEY", "https://aistudio.google.com/app/apikey"),
    ("Groq", "GROQ_API_KEY", "https://console.groq.com/keys"),
    ("OpenRouter", "OPENROUTER_API_KEY", "https://openrouter.ai/keys"),
    ("DeepSeek", "DEEPSEEK_API_KEY", "https://platform.deepseek.com/api_keys"),
    ("Mistral", "MISTRAL_API_KEY", "https://console.mistral.ai/api-keys/"),
    ("千尋", "DASHSCOPE_API_KEY", "https://dashscope.console.aliyun.com/apiKey"),
    ("混元", "HUNYUAN_API_KEY", "https://console.cloud.tencent.com/hunyuan/api-key"),
    ("豆包", "DOUBAO_API_KEY", "https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey"),
]

def main():
    missing = []
    for name, key, url in LINKS:
        val = os.environ.get(key, "")
        if not val or val.startswith("your-") or len(val) < 10:
            missing.append((name, url))
            print(f"  [X] {name} 尚未設定")
        else:
            print(f"  [OK] {name} 已設定")

    if missing:
        print(f"\n開啟 {len(missing)} 個取得頁面...")
        for name, url in missing:
            webbrowser.open(url)
    else:
        print("\n所有 Key 皆已設定。")

if __name__ == "__main__":
    main()
