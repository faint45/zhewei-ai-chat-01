"""
築未科技大腦 - 圖形化對話介面
強化：Loading  indicator、狀態列、清除、快捷鍵
"""
import asyncio
import base64
import json
import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, scrolledtext

# 讀取環境變數：專案 .env + 使用者 ~/.openclaw/.env
try:
    from dotenv import load_dotenv
    load_dotenv()
    _user_env = Path.home() / ".openclaw" / ".env"
    if _user_env.exists():
        load_dotenv(_user_env, override=True)
except ImportError:
    pass


def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _use_brain_core() -> bool:
    """是否使用築未大腦完整邏輯（天氣、授權、Agent、開發：），即本地機器人模式"""
    return os.environ.get("ZHEWEI_LOCAL_ROBOT", "1").strip().lower() in ("1", "true", "yes")


def get_response(prompt: str, images: list = None) -> tuple[str, str]:
    if _use_brain_core() and (not images or len(images) == 0):
        from guard_core import process_message
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        model = os.environ.get("OLLAMA_MODEL", "gemma3:4b")
        result, msg_type = process_message(prompt.strip(), "local", base_url, model)
        return result, msg_type
    from ai_brain import ask
    return run_async(ask(prompt, images))


def get_agent_response(prompt: str, on_step=None) -> tuple[str, str]:
    from agent import run_agent_sync
    return run_agent_sync(prompt, on_step)


from brain_data_config import HISTORY_FILE


class ChatGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("築未科技大腦 - Zhu Wei Tech AI")
        self.root.geometry("660x560")
        self.root.minsize(480, 400)
        self.root.configure(bg="#1e1e2e")
        self.attached_path = None
        self.attached_images = []
        self.is_loading = False
        self.setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.bind("<Control-n>", lambda e: self.clear_chat())
        self.root.bind("<Control-s>", lambda e: self.save_history())
        self._start_upgrade_daemon()

    def _start_upgrade_daemon(self):
        def _scan():
            try:
                import asyncio
                from ai_market_scanner import scan_once
                result = asyncio.run(scan_once())
                if result.get("new", 0) > 0:
                    self.root.after(0, lambda: self._on_upgrade(result))
            except Exception:
                pass

        def _schedule_next():
            t = threading.Thread(target=_scan, daemon=True)
            t.start()
            self.root.after(3600000, _schedule_next)

        _schedule_next()

    def _on_upgrade(self, result: dict):
        try:
            from ai_market_scanner import get_upgrade_suggestions
            sugs = get_upgrade_suggestions()
            if sugs:
                txt = self.provider_text + " | 發現 " + str(result.get("new", 0)) + " 項可模仿"
                self.status.config(text=txt)
        except Exception:
            pass

    def setup_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        main = tk.Frame(self.root, padx=12, pady=10, bg="#1e1e2e")
        main.grid(row=0, column=0, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(1, weight=1)

        top = tk.Frame(main, bg="#1e1e2e")
        top.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        top.columnconfigure(0, weight=1)

        title = tk.Label(top, text="築未科技大腦", fg="#cdd6f4", bg="#1e1e2e", font=("Arial", 14))
        title.grid(row=0, column=0, sticky="w")

        self.agent_mode = tk.BooleanVar(value=False)
        agent_cb = tk.Checkbutton(top, text="Agent", variable=self.agent_mode,
            fg="#f9e2af", bg="#1e1e2e", selectcolor="#313244", activebackground="#1e1e2e",
            activeforeground="#f9e2af", font=("Arial", 9))
        agent_cb.grid(row=0, column=1, padx=(12, 0))

        clear_btn = tk.Button(top, text="清除", width=5, command=self.clear_chat,
            bg="#45475a", fg="#cdd6f4", relief=tk.FLAT, cursor="hand2", font=("Arial", 9))
        clear_btn.grid(row=0, column=2, padx=(8, 0))

        cost_btn = tk.Button(top, text="花費", width=5, command=self._show_cost,
            bg="#45475a", fg="#a6e3a1", relief=tk.FLAT, cursor="hand2", font=("Arial", 9))
        cost_btn.grid(row=0, column=3, padx=(8, 0))

        learn_video_btn = tk.Button(top, text="學習影片", width=7, command=self._learn_video,
            bg="#45475a", fg="#f9e2af", relief=tk.FLAT, cursor="hand2", font=("Arial", 9))
        learn_video_btn.grid(row=0, column=4, padx=(8, 0))

        chat_frame = tk.Frame(main, bg="#313244")
        chat_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        chat_frame.columnconfigure(0, weight=1)
        chat_frame.rowconfigure(0, weight=1)

        self.chat = scrolledtext.ScrolledText(
            chat_frame, wrap=tk.WORD, state=tk.DISABLED,
            bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4",
            relief=tk.FLAT, padx=10, pady=10, font=("Arial", 10)
        )
        self.chat.grid(row=0, column=0, sticky="nsew")

        input_frame = tk.Frame(main, bg="#1e1e2e")
        input_frame.grid(row=2, column=0, sticky="ew", pady=(0, 4))
        input_frame.columnconfigure(1, weight=1)

        self.attach_btn = tk.Button(
            input_frame, text="附加", width=6, command=self.attach_file,
            bg="#45475a", fg="#cdd6f4", relief=tk.FLAT, cursor="hand2", font=("Arial", 10)
        )
        self.attach_btn.grid(row=0, column=0, padx=(0, 6), ipady=4)

        self.entry = tk.Entry(
            input_frame, font=("Arial", 11),
            bg="#45475a", fg="#cdd6f4", insertbackground="#cdd6f4", relief=tk.FLAT
        )
        self.entry.grid(row=0, column=1, sticky="ew", ipady=8, ipadx=10, padx=(0, 6))
        self.entry.bind("<Return>", lambda e: self.send())

        self.send_btn = tk.Button(
            input_frame, text="送出", width=6, command=self.send,
            bg="#89b4fa", fg="#1e1e2e", relief=tk.FLAT, cursor="hand2", font=("Arial", 10)
        )
        self.send_btn.grid(row=0, column=2, ipady=4)

        self.file_label = tk.Label(input_frame, text="", fg="#a6e3a1", bg="#1e1e2e", font=("Arial", 9))
        self.file_label.grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 0))

        try:
            from ai_brain import get_available_providers
            providers = ", ".join(get_available_providers())
        except Exception:
            providers = "Ollama"
        try:
            from ai_cost_tracker import get_total, format_cost, get_month_total_twd, format_cost_twd, BUDGET_TWD
            cost_str = format_cost(get_total())
            month_twd = get_month_total_twd()
            budget_str = format_cost_twd(BUDGET_TWD)
            twd_str = format_cost_twd(month_twd)
            self.provider_text = f"免費多AI | {providers} | 當月: {twd_str}/{budget_str} 累計: {cost_str} | Ctrl+N 清除 Ctrl+S 儲存"
        except Exception:
            try:
                from ai_cost_tracker import get_total, format_cost
                cost_str = format_cost(get_total())
                self.provider_text = f"免費多AI | {providers} | 累計花費: {cost_str} | Ctrl+N 清除 Ctrl+S 儲存"
            except Exception:
                self.provider_text = f"免費多AI | {providers} | Ctrl+N 清除 Ctrl+S 儲存"
        self.status = tk.Label(
            main, text=self.provider_text,
            fg="#6c7086", bg="#1e1e2e", font=("Arial", 9)
        )
        self.status.grid(row=3, column=0, sticky="w", pady=(4, 0))

    def set_loading(self, on: bool):
        self.is_loading = on
        state = tk.DISABLED if on else tk.NORMAL
        self.send_btn.config(state=state)
        self.attach_btn.config(state=state)
        self.entry.config(state=state)
        if on:
            self.status.config(text="處理中...")
        else:
            self._refresh_cost_status()

    def _refresh_cost_status(self):
        """更新狀態列中的當月／累計花費"""
        try:
            from ai_cost_tracker import get_total, format_cost, get_month_total_twd, format_cost_twd, BUDGET_TWD
            cost_str = format_cost(get_total())
            twd_str = format_cost_twd(get_month_total_twd())
            budget_str = format_cost_twd(BUDGET_TWD)
            base = self.provider_text.split(" | ")[0] if " | " in self.provider_text else self.provider_text
            self.provider_text = f"{base} | 當月: {twd_str}/{budget_str} 累計: {cost_str} | Ctrl+N 清除 Ctrl+S 儲存"
            self.status.config(text=self.provider_text)
        except Exception:
            try:
                from ai_cost_tracker import get_total, format_cost
                cost_str = format_cost(get_total())
                base = self.provider_text.split(" | ")[0] if " | " in self.provider_text else self.provider_text
                self.provider_text = f"{base} | 累計花費: {cost_str} | Ctrl+N 清除 Ctrl+S 儲存"
                self.status.config(text=self.provider_text)
            except Exception:
                self.status.config(text=getattr(self, "provider_text", ""))

    def _show_cost(self):
        """顯示 AI 花費明細視窗"""
        try:
            from ai_cost_tracker import get_summary, format_cost, get_month_total_twd, format_cost_twd, BUDGET_TWD, is_budget_exceeded
            s = get_summary()
        except Exception:
            s = {"total_usd": 0, "by_provider": {}, "calls": 0, "monthly_usd": {}}
        win = tk.Toplevel(self.root)
        win.title("AI 使用花費")
        win.geometry("360x280")
        win.configure(bg="#1e1e2e")
        win.transient(self.root)
        txt = scrolledtext.ScrolledText(win, wrap=tk.WORD, font=("Arial", 10),
            bg="#313244", fg="#cdd6f4", relief=tk.FLAT, padx=12, pady=10)
        txt.pack(fill=tk.BOTH, expand=True)
        total = s.get("total_usd", 0)
        calls = s.get("calls", 0)
        try:
            month_twd = get_month_total_twd()
            budget_str = format_cost_twd(BUDGET_TWD)
            twd_str = format_cost_twd(month_twd)
            over = "（已達上限，僅使用免費 AI）" if is_budget_exceeded() else ""
            txt.insert(tk.END, f"當月花費: {twd_str} / 預算 {budget_str} {over}\n", "title")
        except Exception:
            pass
        txt.insert(tk.END, f"累計花費: {format_cost(total)}\n", "title")
        txt.insert(tk.END, f"總呼叫次數: {calls}\n\n", "sub")
        txt.insert(tk.END, "各提供者明細:\n", "title")
        for prov, data in s.get("by_provider", {}).items():
            u = data.get("usd", 0)
            c = data.get("calls", 0)
            txt.insert(tk.END, f"  {prov}: {format_cost(u)} ({c} 次)\n")
        txt.insert(tk.END, "\n※ 費用為估算值，依 token 數推算。當月超過預算後僅使用免費提供者。", "note")
        txt.tag_config("title", foreground="#89b4fa")
        txt.tag_config("sub", foreground="#a6e3a1")
        txt.tag_config("note", foreground="#6c7086")
        txt.config(state=tk.DISABLED)

    def _learn_video(self):
        """選擇影片並學習（轉字幕存入知識庫）"""
        ok, msg = self._check_video_learn_ready()
        if not ok:
            self.append(f"築未 > {msg}", "bot")
            return
        path = filedialog.askopenfilename(
            title="選擇要學習的影片",
            filetypes=[
                ("影片", "*.mp4 *.webm *.mov *.mkv *.avi *.m4v"),
                ("所有檔案", "*.*"),
            ],
        )
        if not path:
            return
        self.set_loading(True)
        self.append("築未 > 正在轉錄影片…請稍候（較長影片需數分鐘）", "bot")
        self.root.update()

        def do():
            try:
                from video_learner import ingest_video
                success, result = ingest_video(path)
                self.root.after(0, lambda: self._on_learn_done(success, result))
            except Exception as e:
                self.root.after(0, lambda: self._on_learn_done(False, str(e)))

        threading.Thread(target=do, daemon=True).start()

    def _check_video_learn_ready(self):
        try:
            from video_learner import can_learn_video
            return can_learn_video()
        except Exception:
            return False, "需安裝: pip install faster-whisper，以及 ffmpeg"

    def _on_learn_done(self, success: bool, msg: str):
        self.set_loading(False)
        self.append(f"築未 > {'✅ ' if success else '❌ '}{msg}", "bot")

    def attach_file(self):
        path = filedialog.askopenfilename(
            title="選擇檔案或圖片",
            filetypes=[
                ("圖片", "*.png *.jpg *.jpeg *.gif *.webp"),
                ("影片", "*.mp4 *.webm *.mov *.mkv"),
                ("文字檔", "*.txt *.md *.json"),
                ("所有檔案", "*.*"),
            ],
        )
        if path:
            self.attached_path = path
            name = os.path.basename(path)
            self.file_label.config(text=f"已附加: {name}")
            ext = os.path.splitext(path)[1].lower()
            self.attached_images = []
            if ext in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
                try:
                    with open(path, "rb") as f:
                        self.attached_images = [base64.b64encode(f.read()).decode()]
                except Exception:
                    self.file_label.config(text=f"讀取失敗: {name}")

    def clear_attach(self):
        self.attached_path = None
        self.attached_images = []
        self.file_label.config(text="")

    def append(self, text: str, tag: str = None):
        self.chat.config(state=tk.NORMAL)
        if tag:
            self.chat.insert(tk.END, text + "\n", tag)
        else:
            self.chat.insert(tk.END, text + "\n")
        self.chat.see(tk.END)
        self.chat.config(state=tk.DISABLED)

    def clear_chat(self):
        self.chat.config(state=tk.NORMAL)
        self.chat.delete(1.0, tk.END)
        self.chat.config(state=tk.DISABLED)
        self.append("築未科技大腦 已就緒。可點「附加」上傳圖片或文字檔，「學習影片」可餵影片學會內容。", "bot")

    def save_history(self):
        try:
            content = self.chat.get(1.0, tk.END)
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump({"content": content}, f, ensure_ascii=False)
            self.status.config(text="已儲存對話")
            self.root.after(2000, lambda: self.status.config(text=""))
        except Exception:
            pass

    def load_history(self):
        if HISTORY_FILE.exists():
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.chat.config(state=tk.NORMAL)
                    self.chat.delete(1.0, tk.END)
                    self.chat.insert(tk.END, data.get("content", ""))
                    self.chat.config(state=tk.DISABLED)
            except Exception:
                pass

    def send(self):
        msg = self.entry.get().strip()
        images = list(self.attached_images)
        if not msg and not images:
            return
        self.entry.delete(0, tk.END)
        if msg.lower() in ("/exit", "exit", "quit"):
            self.root.quit()
            return
        if msg:
            self.append(f"你 > {msg}", "user")
        attached_path = self.attached_path
        if attached_path:
            self.append(f"  [檔案] {os.path.basename(attached_path)}", "user")
        self.clear_attach()
        self.set_loading(True)
        self.root.update()

        def do():
            try:
                prompt = msg
                if attached_path and not images:
                    ext = os.path.splitext(attached_path)[1].lower()
                    if ext in (".txt", ".md"):
                        try:
                            with open(attached_path, "r", encoding="utf-8", errors="ignore") as f:
                                content = f.read()
                                prompt = f"[檔案內容]\n{content}\n\n[我的問題] {msg or '請分析以上內容'}"
                                try:
                                    from brain_knowledge import add
                                    add(content[:8000], source=f"檔案：{os.path.basename(attached_path)}")
                                except Exception:
                                    pass
                        except Exception:
                            prompt = prompt or "請分析附加的檔案"
                if not prompt and not images:
                    prompt = "你好"

                _no_meta = "請直接回答，勿輸出自我介紹、LLM 本質分析、意識論述。\n\n"
                if self.agent_mode.get():
                    prompt = _no_meta + prompt
                    if images:
                        self.root.after(0, lambda: self._on_response("[Agent] 圖片模式暫不支援，請關閉 Agent。", "無"))
                        self.root.after(0, lambda: self.set_loading(False))
                        return
                    def on_step(result, _):
                        self.root.after(0, lambda: self.append(f"  [工具] {result[:200]}{'...' if len(result) > 200 else ''}", "agent"))
                    resp, provider = get_agent_response(prompt, on_step)
                    self.root.after(0, lambda: self._on_response(resp, f"Agent + {provider}"))
                else:
                    if not msg and images:
                        prompt = "請描述這張圖片。"
                    prompt = _no_meta + prompt
                    resp, provider = get_response(prompt, images if images else None)
                    self.root.after(0, lambda: self._on_response(resp, provider))
            except Exception as e:
                self.root.after(0, lambda: self._on_response(f"[錯誤] {e}", "無"))

        threading.Thread(target=do, daemon=True).start()

    def _on_response(self, resp: str, provider: str):
        self.set_loading(False)
        self.append(f"築未 > {resp}\n  └ {provider}", "bot")

    def on_close(self):
        self.root.destroy()

    def run(self):
        self.chat.tag_config("user", foreground="#a6e3a1")
        self.chat.tag_config("bot", foreground="#89b4fa")
        self.chat.tag_config("agent", foreground="#f9e2af")
        self.load_history()
        if not self.chat.get(1.0, tk.END).strip():
            if _use_brain_core():
                self.append("築未科技大腦（本地機器人）已就緒。支援：天氣、授權、開發：、Agent、一般對話。點「學習影片」可餵影片。勾選 Agent 可執行工具。", "bot")
            else:
                self.append("築未科技大腦 已就緒。免費多 AI 一起思考、不斷學習（對話自動記住）。點「學習影片」可餵影片學會內容。勾選 Agent 可執行工具。", "bot")
        self.root.mainloop()


if __name__ == "__main__":
    app = ChatGUI()
    app.run()
