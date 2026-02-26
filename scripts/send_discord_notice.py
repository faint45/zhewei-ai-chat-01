#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import sys
import asyncio
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "Jarvis_Training"))
from env_loader import load_env_file  # type: ignore


def _post(channel_id: str, token: str, content: str) -> bool:
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    data = json.dumps({"content": content}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Authorization": f"Bot {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return 200 <= int(resp.status) < 300
    except urllib.error.HTTPError:
        return False
    except Exception:
        return False


def main() -> int:
    load_env_file(ROOT / ".env")
    load_env_file(ROOT / "Jarvis_Training" / ".env")
    token = (os.environ.get("DISCORD_BOT_TOKEN") or "").strip()
    channel_id = (os.environ.get("DISCORD_CHANNEL_ID") or "").strip()
    content = "✅ 已處理完成：直連容錯已修復，可用 !direct mode cursor 後直接對話。"

    if not token:
        print(f"NO_TOKEN token_len={len(token)} channel_len={len(channel_id)}")
        return 2

    if channel_id and _post(channel_id, token, content):
        print(f"SENT:{channel_id}")
        return 0

    # fallback 1: use discord.py to post to first writable text channel
    try:
        import discord
    except Exception:
        discord = None

    if discord is not None:
        async def _send_with_discordpy() -> str:
            intents = discord.Intents.default()
            intents.guilds = True
            intents.messages = True
            client = discord.Client(intents=intents)
            result = "NO_CHANNEL_DISCORDPY"

            @client.event
            async def on_ready():
                nonlocal result
                try:
                    # prefer configured channel id if exists
                    if channel_id:
                        ch = client.get_channel(int(channel_id))
                        if ch is not None and hasattr(ch, "send"):
                            await ch.send(content)
                            result = f"SENT:{channel_id}"
                            await client.close()
                            return
                    for ch in client.get_all_channels():
                        if isinstance(ch, discord.TextChannel):
                            perms = ch.permissions_for(ch.guild.me)
                            if perms.send_messages:
                                await ch.send(content)
                                result = f"SENT:{ch.id}"
                                break
                except Exception as e:
                    result = f"DISCORDPY_ERR_{type(e).__name__}"
                await client.close()

            await client.start(token)
            return result

        try:
            r = asyncio.run(_send_with_discordpy())
            if r.startswith("SENT:"):
                print(r)
                return 0
        except Exception:
            pass

    # fallback 2: try first writable text channel across guilds via REST
    h = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}
    req = urllib.request.Request("https://discord.com/api/v10/users/@me/guilds", headers=h, method="GET")
    try:
        guilds = json.loads(urllib.request.urlopen(req, timeout=20).read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"NO_GUILDS_HTTP_{e.code}")
        return 3
    except Exception as e:
        print(f"NO_GUILDS_ERR_{type(e).__name__}")
        return 3

    for g in guilds:
        gid = str(g.get("id") or "").strip()
        if not gid:
            continue
        reqc = urllib.request.Request(f"https://discord.com/api/v10/guilds/{gid}/channels", headers=h, method="GET")
        try:
            channels = json.loads(urllib.request.urlopen(reqc, timeout=20).read().decode("utf-8"))
        except Exception:
            continue
        for c in channels:
            if int(c.get("type", -1)) != 0:
                continue
            cid = str(c.get("id") or "").strip()
            if cid and _post(cid, token, content):
                print(f"SENT:{cid}")
                return 0

    print("NO_WRITABLE_CHANNEL")
    return 4


if __name__ == "__main__":
    raise SystemExit(main())
