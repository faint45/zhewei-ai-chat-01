"""
selectors 模組 - 非同步 Socket Server
目標：10,000 ops/s 數據轉發，不丟包
"""
import selectors
import socket

RECV_BUF = 65536
BACKLOG = 1024


class ForwardServer:
    def __init__(self, listen_port: int, upstream_host: str, upstream_port: int):
        self.listen_port = listen_port
        self.upstream = (upstream_host, upstream_port)
        self.sel = selectors.DefaultSelector()
        self.running = True

    def _create_socket(self) -> socket.socket:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, RECV_BUF)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, RECV_BUF)
        s.setblocking(False)
        return s

    def accept(self, sock: socket.socket):
        conn, _ = sock.accept()
        conn.setblocking(False)
        conn.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, RECV_BUF)
        conn.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, RECV_BUF)
        try:
            peer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer.setblocking(False)
            peer.connect_ex(self.upstream)
        except OSError:
            conn.close()
            return
        bridge = {"conn": conn, "peer": peer, "to_peer": b"", "to_conn": b""}
        self.sel.register(conn, selectors.EVENT_READ, bridge)
        self.sel.register(peer, selectors.EVENT_READ, bridge)

    def _recv_and_forward(self, sock: socket.socket, bridge: dict, to_buf: str, to_sock: socket.socket):
        try:
            chunk = sock.recv(RECV_BUF)
        except (ConnectionResetError, BrokenPipeError):
            self._close_pair(bridge)
            return
        if not chunk:
            self._close_pair(bridge)
            return
        bridge[to_buf] += chunk
        self._drain(bridge, to_buf, to_sock)

    def _drain(self, bridge: dict, buf_key: str, sock: socket.socket):
        if sock.fileno() == -1 or not bridge[buf_key]:
            return
        try:
            sent = sock.send(bridge[buf_key])
            bridge[buf_key] = bridge[buf_key][sent:]
        except (BlockingIOError, ConnectionResetError, BrokenPipeError):
            pass
        if bridge[buf_key] and sock.fileno() != -1:
            self.sel.modify(sock, selectors.EVENT_READ | selectors.EVENT_WRITE, bridge)

    def _close_pair(self, bridge: dict):
        for s in (bridge["conn"], bridge["peer"]):
            try:
                if s.fileno() != -1:
                    self.sel.unregister(s)
                    s.close()
            except (OSError, KeyError):
                pass

    def run(self):
        server = self._create_socket()
        server.bind(("0.0.0.0", self.listen_port))
        server.listen(BACKLOG)
        self.sel.register(server, selectors.EVENT_READ, None)
        print(f"Server listening :{self.listen_port} -> {self.upstream[0]}:{self.upstream[1]}")
        while self.running:
            events = self.sel.select(timeout=0.1)
            for key, mask in events:
                bridge = key.data
                if bridge is None:
                    self.accept(key.fileobj)
                    continue
                sock = key.fileobj
                conn, peer = bridge["conn"], bridge["peer"]
                if mask & selectors.EVENT_READ:
                    if sock is conn:
                        self._recv_and_forward(conn, bridge, "to_peer", peer)
                    else:
                        self._recv_and_forward(peer, bridge, "to_conn", conn)
                elif mask & selectors.EVENT_WRITE:
                    if sock is peer:
                        self._drain(bridge, "to_peer", peer)
                        if not bridge["to_peer"]:
                            self.sel.modify(peer, selectors.EVENT_READ, bridge)
                    else:
                        self._drain(bridge, "to_conn", conn)
                        if not bridge["to_conn"]:
                            self.sel.modify(conn, selectors.EVENT_READ, bridge)


def echo_server_demo(port: int = 9999):
    """簡易 Echo Server：驗證 selectors 流程"""
    sel = selectors.DefaultSelector()

    def accept(sock):
        conn, _ = sock.accept()
        conn.setblocking(False)
        sel.register(conn, selectors.EVENT_READ, b"")

    def read(conn, data):
        try:
            chunk = conn.recv(4096)
        except (ConnectionResetError, BrokenPipeError):
            sel.unregister(conn)
            conn.close()
            return
        if not chunk:
            sel.unregister(conn)
            conn.close()
            return
        try:
            conn.send(chunk)
        except (BlockingIOError, ConnectionResetError, BrokenPipeError):
            sel.unregister(conn)
            conn.close()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", port))
    server.listen(128)
    server.setblocking(False)
    sel.register(server, selectors.EVENT_READ, None)
    print(f"Echo server :{port}")
    while True:
        for key, mask in sel.select():
            if key.data is None:
                accept(key.fileobj)
            else:
                read(key.fileobj, key.data)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "forward":
        s = ForwardServer(8888, "127.0.0.1", 9999)
        s.run()
    else:
        echo_server_demo(9999)
