import httpx
import asyncio
from typing import Optional


class AutonomousAgent:
    def __init__(self):
        self.limits = httpx.Limits(max_connections=100, max_keepalive_connections=20)
        self.base_headers = {
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0",
        }

    async def probe_endpoint(self, url: str, custom_headers: Optional[dict] = None) -> dict:
        headers = {**self.base_headers, **(custom_headers or {})}
        async with httpx.AsyncClient(headers=headers, limits=self.limits) as client:
            try:
                response = await client.get(url)
                return {
                    "status": response.status_code,
                    "auth_type": response.headers.get("WWW-Authenticate"),
                    "server": response.headers.get("Server"),
                }
            except httpx.HTTPError as e:
                return {"error": str(e)}
            except Exception as e:
                return {"error": str(e)}


if __name__ == "__main__":
    agent = AutonomousAgent()
    result = asyncio.run(agent.probe_endpoint("https://example.com/api"))
    print(result)
