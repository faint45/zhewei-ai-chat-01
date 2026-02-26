"""
TCP 雙向轉發器 - asyncio 實作，0 丟包
"""
import asyncio

RECV_BUF = 65536


async def bridge(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    try:
        while True:
            data = await reader.read(RECV_BUF)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except (ConnectionResetError, BrokenPipeError, asyncio.CancelledError):
        pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except OSError:
            pass


async def handle_client(local_reader, local_writer, remote_host: str, remote_port: int):
    try:
        remote_reader, remote_writer = await asyncio.open_connection(remote_host, remote_port)
    except OSError as e:
        local_writer.close()
        await local_writer.wait_closed()
        return
    await asyncio.gather(
        bridge(local_reader, remote_writer),
        bridge(remote_reader, local_writer),
    )


async def start_forwarder(local_port: int, remote_host: str, remote_port: int, bind_host: str = "127.0.0.1"):
    async def on_connect(r, w):
        asyncio.create_task(handle_client(r, w, remote_host, remote_port))

    server = await asyncio.start_server(on_connect, bind_host, local_port, backlog=1024)
    print(f"Forward: {bind_host}:{local_port} -> {remote_host}:{remote_port}")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 4:
        port = int(sys.argv[1])
        host = sys.argv[2]
        rport = int(sys.argv[3])
        asyncio.run(start_forwarder(port, host, rport))
    else:
        print("Usage: python tcp_forwarder.py LOCAL_PORT REMOTE_HOST REMOTE_PORT")
