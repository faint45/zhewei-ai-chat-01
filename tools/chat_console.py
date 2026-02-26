"""
民雄監控中心 - 對話式 AI 介面
"""
import asyncio

from ollama_client import stream_local_intelligence

SYSTEM_PROMPT = (
    "你是民雄監控中心 (Minxiong Monitor - CL3) 的 AI 助手。"
    "你可以協助：戰情看板、追蹤系統、網路監控、節點狀態等。"
    "請用繁體中文簡潔回覆。嚴禁自我介紹、LLM 本質分析、意識論述。\n\n使用者: "
)
PROMPT_SUFFIX = "\n\n助手:"


async def chat_with_gemma():
    print("\n" + "=" * 50)
    print(" 民雄監控中心 - Minxiong Monitor CL3")
    print(" 與我對話，輸入 exit 或 quit 結束")
    print("=" * 50)

    while True:
        try:
            user_msg = input("\n你 > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if user_msg.lower() in ("exit", "quit", ""):
            break

        prompt = SYSTEM_PROMPT + user_msg + PROMPT_SUFFIX
        print("\n民雄 > ", end="", flush=True)
        try:
            async for chunk in stream_local_intelligence(prompt):
                print(chunk, end="", flush=True)
            print()
        except Exception as e:
            print(f"\n[系統異常] {e}")

    print("\n民雄監控中心 已關閉。")


if __name__ == "__main__":
    asyncio.run(chat_with_gemma())
