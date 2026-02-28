"""
築未科技 — 一鍵服務啟動器（含即時 LOG 串流）
雙擊執行，無 console 視窗（.pyw）
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import subprocess, threading, time, os, io
from pathlib import Path

# ── 顏色主題 ──────────────────────────────────────────────────
BG      = "#1a1a2e"
CARD    = "#16213e"
BORDER  = "#0f3460"
GREEN   = "#00d4aa"
RED     = "#e94560"
YELLOW  = "#f5a623"
BLUE    = "#58a6ff"
FG      = "#e0e0e0"
FG2     = "#888"

# ── 服務定義 ─────────────────────────────────────────────────
SERVICES = [
    {
        "id": "docker",
        "name": "Docker / 容器群",
        "desc": "Nginx + Open WebUI + Dify + CMS",
        "check": lambda: _check_port(80) or _check_docker(),
        "start": lambda: _run("docker compose up -d", cwd="D:/zhe-wei-tech"),
        "stop":  lambda: _run("docker compose stop", cwd="D:/zhe-wei-tech"),
        "url":   None,
    },
    {
        "id": "ollama",
        "name": "Ollama",
        "desc": "本地 LLM 推理引擎 (port 11460)",
        "check": lambda: _check_port(11460),
        "start": lambda: _start_proc(
            r"C:\Users\user\AppData\Local\Programs\Ollama\ollama.exe", ["serve"]
        ),
        "stop":  lambda: _kill_name("ollama.exe"),
        "url":   "http://localhost:11460",
    },
    {
        "id": "brain",
        "name": "Brain Server",
        "desc": "主 AI 伺服器 (port 8002)",
        "check": lambda: _check_port(8002),
        "start": lambda: _start_proc(
            r"D:\zhe-wei-tech\ai_engines\.venv\Scripts\python.exe",
            ["brain_server.py"],
            cwd="D:/zhe-wei-tech",
        ),
        "stop":  lambda: _kill_port(8002),
        "url":   "http://localhost:8002/hub",
    },
    {
        "id": "vision",
        "name": "Vision AI",
        "desc": "AI 視覺辨識系統 (port 8030)",
        "check": lambda: _check_port(8030),
        "start": lambda: _start_proc(
            r"D:\zhe-wei-tech\Jarvis_Training\.venv312\Scripts\python.exe",
            ["web_server.py"],
            cwd="D:/AI_Vision_Recognition",
        ),
        "stop":  lambda: _kill_port(8030),
        "url":   "http://localhost:8030",
    },
    {
        "id": "forge",
        "name": "Forge 生圖",
        "desc": "SD WebUI Forge (port 7860)  — 按需啟動",
        "check": lambda: _check_port(7860),
        "start": lambda: _run(
            r"D:\zhe-wei-tech\stable-diffusion-webui-forge\webui-user.bat",
            cwd="D:/zhe-wei-tech/stable-diffusion-webui-forge",
        ),
        "stop":  lambda: _kill_port(7860),
        "url":   "http://localhost:7860",
    },
]

# ── 工具函式 ─────────────────────────────────────────────────
def _check_port(port: int) -> bool:
    import socket
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except Exception:
        return False

def _check_docker() -> bool:
    try:
        r = subprocess.run(["docker", "info"], capture_output=True, timeout=3)
        return r.returncode == 0
    except Exception:
        return False

def _kill_name(name: str):
    subprocess.run(["taskkill", "/F", "/IM", name],
                   capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)

def _kill_port(port: int):
    try:
        r = subprocess.run(
            f'netstat -ano | findstr ":{port}.*LISTEN"',
            shell=True, capture_output=True, text=True,
        )
        for line in r.stdout.strip().splitlines():
            parts = line.split()
            if parts:
                pid = parts[-1]
                subprocess.run(["taskkill", "/F", "/PID", pid],
                               capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception:
        pass

def _open_url(url):
    import webbrowser
    webbrowser.open(url)

# ── LOG 顏色對應 ─────────────────────────────────────────────
LOG_COLORS = {
    "docker":  "#3fb950",
    "ollama":  "#bc8cff",
    "brain":   "#58a6ff",
    "vision":  "#39d353",
    "forge":   "#f5a623",
    "system":  "#888888",
    "error":   "#f85149",
    "warn":    "#d29922",
}

# ── 主視窗 ───────────────────────────────────────────────────
class ZheweiLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("築未科技 服務啟動器")
        self.geometry("560x880")
        self.minsize(480, 600)
        self.configure(bg=BG)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self._rows    = {}   # id -> {dot, card}
        self._procs   = {}   # id -> Popen
        self._running = True

        self._build_ui()
        threading.Thread(target=self._poll_loop, daemon=True).start()

    # ── UI 建立 ──────────────────────────────────────────────
    def _build_ui(self):
        # 頂部標題
        hdr = tk.Frame(self, bg=BG)
        hdr.pack(fill="x", padx=20, pady=(14, 4))
        tk.Label(hdr, text="⚙  築未科技", font=("Segoe UI", 16, "bold"),
                 bg=BG, fg=BLUE).pack(side="left")
        tk.Label(hdr, text="服務啟動器", font=("Segoe UI", 12),
                 bg=BG, fg=FG2).pack(side="left", padx=8)

        # 一鍵按鈕列
        btn_row = tk.Frame(self, bg=BG)
        btn_row.pack(fill="x", padx=20, pady=(4, 8))
        tk.Button(btn_row, text="▶  全部啟動", bg=GREEN, fg="#111",
                  font=("Segoe UI", 10, "bold"), bd=0, padx=14, pady=5,
                  cursor="hand2", activebackground="#00b894",
                  command=self.start_all).pack(side="left", padx=(0, 8))
        tk.Button(btn_row, text="⏹  全部停止", bg=RED, fg="white",
                  font=("Segoe UI", 10, "bold"), bd=0, padx=14, pady=5,
                  cursor="hand2", activebackground="#c0392b",
                  command=self.stop_all).pack(side="left", padx=(0, 8))
        self._last_refresh = tk.Label(btn_row, text="", font=("Segoe UI", 9),
                                      bg=BG, fg=FG2)
        self._last_refresh.pack(side="right")

        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", padx=20)

        # ── PanedWindow：上半服務卡片 / 下半 LOG ──
        pane = tk.PanedWindow(self, orient=tk.VERTICAL, bg=BORDER,
                              sashwidth=5, sashrelief=tk.FLAT,
                              handlesize=0)
        pane.pack(fill="both", expand=True, padx=0, pady=0)

        # 上半：服務卡片
        top_frame = tk.Frame(pane, bg=BG)
        pane.add(top_frame, minsize=300, stretch="always")

        svc_frame = tk.Frame(top_frame, bg=BG)
        svc_frame.pack(fill="both", expand=True, padx=20, pady=8)
        for svc in SERVICES:
            self._add_service_row(svc_frame, svc)

        # 快速連結
        tk.Frame(top_frame, bg=BORDER, height=1).pack(fill="x", padx=20)
        foot = tk.Frame(top_frame, bg=BG)
        foot.pack(fill="x", padx=20, pady=8)
        for label, url in [
            ("🏠 Hub",        "http://localhost:8002/hub"),
            ("🤖 Agent",      "http://localhost:8002/agent"),
            ("🎨 生圖",        "http://localhost:8002/forge-easy"),
            ("🌐 Jarvis外網",  "https://jarvis.zhe-wei.net"),
        ]:
            tk.Button(foot, text=label, bg=CARD, fg=BLUE,
                      font=("Segoe UI", 9), bd=0, padx=10, pady=4,
                      cursor="hand2", activebackground=BORDER,
                      command=lambda u=url: _open_url(u)).pack(side="left", padx=3)

        # 下半：LOG 面板
        log_frame = tk.Frame(pane, bg="#0d1117")
        pane.add(log_frame, minsize=160, stretch="always")

        log_hdr = tk.Frame(log_frame, bg="#161b22")
        log_hdr.pack(fill="x")
        tk.Label(log_hdr, text="📋  即時日誌", font=("Segoe UI", 10, "bold"),
                 bg="#161b22", fg=FG2, padx=10, pady=5).pack(side="left")
        tk.Button(log_hdr, text="清除", bg="#161b22", fg=FG2,
                  font=("Segoe UI", 8), bd=0, padx=8, pady=4,
                  cursor="hand2", activebackground=BORDER,
                  command=self._clear_log).pack(side="right", padx=6)

        self._log_text = tk.Text(
            log_frame, bg="#0d1117", fg=FG, font=("Consolas", 9),
            insertbackground=FG, selectbackground=BORDER,
            wrap=tk.WORD, state=tk.DISABLED,
            relief=tk.FLAT, padx=8, pady=4,
        )
        log_sb = tk.Scrollbar(log_frame, command=self._log_text.yview,
                              bg="#161b22", troughcolor="#0d1117", width=8)
        self._log_text.configure(yscrollcommand=log_sb.set)
        log_sb.pack(side="right", fill="y")
        self._log_text.pack(fill="both", expand=True)

        # 設定顏色 tag
        for tag, color in LOG_COLORS.items():
            self._log_text.tag_configure(tag, foreground=color)
        self._log_text.tag_configure("ts", foreground="#444")
        self._log_text.tag_configure("bold", font=("Consolas", 9, "bold"))

        self.log("系統", "啟動器就緒，等待指令...", "system")

    def _add_service_row(self, parent, svc):
        card = tk.Frame(parent, bg=CARD, bd=0, highlightthickness=1,
                        highlightbackground=BORDER)
        card.pack(fill="x", pady=4)
        inner = tk.Frame(card, bg=CARD, padx=12, pady=8)
        inner.pack(fill="x")

        dot = tk.Label(inner, text="●", font=("Segoe UI", 13), bg=CARD, fg=FG2)
        dot.pack(side="left")

        info = tk.Frame(inner, bg=CARD)
        info.pack(side="left", padx=(8, 0), fill="x", expand=True)
        tk.Label(info, text=svc["name"], font=("Segoe UI", 10, "bold"),
                 bg=CARD, fg=FG, anchor="w").pack(fill="x")
        tk.Label(info, text=svc["desc"], font=("Segoe UI", 8),
                 bg=CARD, fg=FG2, anchor="w").pack(fill="x")

        btns = tk.Frame(inner, bg=CARD)
        btns.pack(side="right")

        if svc.get("url"):
            tk.Button(btns, text="🌐", bg=CARD, fg=BLUE, font=("Segoe UI", 10),
                      bd=0, cursor="hand2", activebackground=BORDER,
                      command=lambda u=svc["url"]: _open_url(u)).pack(side="left")

        tk.Button(btns, text="啟動", bg="#1a472a", fg=GREEN,
                  font=("Segoe UI", 9, "bold"), bd=0, padx=10, pady=3,
                  cursor="hand2", activebackground="#2d6a4f",
                  command=lambda s=svc: self._do_start(s)).pack(side="left", padx=3)
        tk.Button(btns, text="停止", bg="#4a1521", fg=RED,
                  font=("Segoe UI", 9, "bold"), bd=0, padx=10, pady=3,
                  cursor="hand2", activebackground="#6d2030",
                  command=lambda s=svc: self._do_stop(s)).pack(side="left")

        self._rows[svc["id"]] = {"dot": dot, "card": card}

    # ── LOG 方法 ─────────────────────────────────────────────
    def log(self, svc_id: str, msg: str, tag: str = None):
        """線程安全地寫入 log 面板"""
        def _write():
            ts = time.strftime("%H:%M:%S")
            t = self._log_text
            t.configure(state=tk.NORMAL)
            t.insert(tk.END, f"[{ts}] ", "ts")
            t.insert(tk.END, f"{svc_id:<10} ", tag or "system")
            # 錯誤/警告高亮
            line_tag = tag or "system"
            lo = msg.lower()
            if any(k in lo for k in ("error", "exception", "traceback", "failed", "errno")):
                line_tag = "error"
            elif any(k in lo for k in ("warning", "warn", "deprecated")):
                line_tag = "warn"
            t.insert(tk.END, msg.rstrip() + "\n", line_tag)
            t.configure(state=tk.DISABLED)
            t.see(tk.END)
        self.after(0, _write)

    def _clear_log(self):
        self._log_text.configure(state=tk.NORMAL)
        self._log_text.delete("1.0", tk.END)
        self._log_text.configure(state=tk.DISABLED)
        self.log("系統", "日誌已清除", "system")

    def _stream_proc(self, svc_id: str, proc):
        """在背景執行緒讀取 proc 的 stdout+stderr 並寫入 log"""
        tag = svc_id if svc_id in LOG_COLORS else "system"
        try:
            for raw in iter(proc.stdout.readline, b""):
                try:
                    line = raw.decode("utf-8", errors="replace").rstrip()
                except Exception:
                    line = repr(raw)
                if line:
                    self.log(svc_id, line, tag)
        except Exception:
            pass
        ret = proc.wait()
        self.log(svc_id, f"[程序結束，exit={ret}]", "warn" if ret else "system")
        self._procs.pop(svc_id, None)
        self.after(1000, self._refresh)

    def _launch(self, svc_id: str, cmd, cwd=None, shell=False):
        """啟動進程並開始 log 串流"""
        try:
            proc = subprocess.Popen(
                cmd, cwd=cwd, shell=shell,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            self._procs[svc_id] = proc
            self.log(svc_id, f"[已啟動 PID={proc.pid}]", svc_id if svc_id in LOG_COLORS else "system")
            threading.Thread(target=self._stream_proc, args=(svc_id, proc),
                             daemon=True).start()
        except Exception as e:
            self.log(svc_id, f"[啟動失敗] {e}", "error")

    # ── 操作 ─────────────────────────────────────────────────
    def _do_start(self, svc):
        sid = svc["id"]
        self.log(sid, f"正在啟動 {svc['name']}...", sid if sid in LOG_COLORS else "system")
        threading.Thread(target=self._start_svc, args=(svc,), daemon=True).start()

    def _do_stop(self, svc):
        sid = svc["id"]
        self.log(sid, f"正在停止 {svc['name']}...", "warn")
        proc = self._procs.pop(sid, None)
        if proc:
            try:
                proc.terminate()
            except Exception:
                pass
        threading.Thread(target=svc["stop"], daemon=True).start()
        self.after(2000, self._refresh)

    def _start_svc(self, svc):
        sid = svc["id"]
        if sid == "docker":
            self._launch("docker", "docker compose up -d", cwd="D:/zhe-wei-tech", shell=True)
        elif sid == "ollama":
            self._launch("ollama",
                [r"C:\Users\user\AppData\Local\Programs\Ollama\ollama.exe", "serve"])
        elif sid == "brain":
            self._launch("brain",
                [r"D:\zhe-wei-tech\ai_engines\.venv\Scripts\python.exe", "brain_server.py"],
                cwd="D:/zhe-wei-tech")
        elif sid == "vision":
            self._launch("vision",
                [r"D:\zhe-wei-tech\Jarvis_Training\.venv312\Scripts\python.exe", "web_server.py"],
                cwd="D:/AI_Vision_Recognition")
        elif sid == "forge":
            self._launch("forge",
                r"D:\zhe-wei-tech\stable-diffusion-webui-forge\webui-user.bat",
                cwd="D:/zhe-wei-tech/stable-diffusion-webui-forge", shell=True)
        self.after(3000, self._refresh)

    def start_all(self):
        def _go():
            for svc in SERVICES:
                if svc["id"] == "forge":
                    continue
                if not svc["check"]():
                    self._start_svc(svc)
                    time.sleep(3)
            time.sleep(2)
            self.after(0, self._refresh)
        threading.Thread(target=_go, daemon=True).start()

    def stop_all(self):
        if not messagebox.askyesno("確認", "停止所有服務（Docker 除外）？"):
            return
        def _go():
            for svc in SERVICES:
                if svc["id"] == "docker":
                    continue
                self._do_stop(svc)
            self.after(2000, self._refresh)
        threading.Thread(target=_go, daemon=True).start()

    # ── 狀態輪詢 ─────────────────────────────────────────────
    def _poll_loop(self):
        while self._running:
            self.after(0, self._refresh)
            time.sleep(8)

    def _refresh(self):
        for svc in SERVICES:
            ok = svc["check"]()
            row = self._rows.get(svc["id"])
            if row:
                color = GREEN if ok else RED
                row["dot"].configure(fg=color)
                row["card"].configure(highlightbackground=color if ok else BORDER)
        now = time.strftime("%H:%M:%S")
        self._last_refresh.configure(text=f"更新 {now}")

    def on_close(self):
        self._running = False
        self.destroy()


if __name__ == "__main__":
    app = ZheweiLauncher()
    app.mainloop()
