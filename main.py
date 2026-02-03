import tkinter as tk
from tkinter import ttk
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from single_process.single_processing import SingleProcessingTab
from advanced_settings.advanced_settings import AdvancedSettingsTab
from batch_process.batch_processing import BatchProcessingTab
from reanalysis.reanalysis_tab import ReAnalysisTab
from config import APP_CONFIG


class AIRecognitionSystem:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_CONFIG['title'])
        self.root.geometry(APP_CONFIG['window_size'])
        self.root.configure(bg="#2b2b2b")
        
        self.status_text = tk.StringVar(value="就緒")
        self.progress_var = tk.DoubleVar(value=0)
        
        self.setup_ui()
        
    def setup_ui(self):
        # 标题
        title_frame = tk.Frame(self.root, bg="#1a1a1a", height=50)
        title_frame.pack(fill=tk.X)
        
        title_label = tk.Label(
            title_frame,
            text=APP_CONFIG['title'],
            bg="#1a1a1a",
            fg="#00ffcc",
            font=("Microsoft JhengHei", 14, "bold")
        )
        title_label.pack(pady=10)

        # 标签页
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 單一處理標籤頁（右側垂直捲軸，內容多時可往下捲）
        single_tab_container = tk.Frame(notebook, bg="#2b2b2b")
        notebook.add(single_tab_container, text="單一處理")
        single_canvas = tk.Canvas(single_tab_container, bg="#2b2b2b", highlightthickness=0)
        single_scrollbar = tk.Scrollbar(single_tab_container, orient="vertical", command=single_canvas.yview,
                                        bg="#444444", activebackground="#555555", troughcolor="#333333")
        self.single_tab = tk.Frame(single_canvas, bg="#2b2b2b")
        self.single_tab.bind("<Configure>", lambda e: single_canvas.configure(scrollregion=single_canvas.bbox("all")))
        single_win_id = single_canvas.create_window((0, 0), window=self.single_tab, anchor="nw")
        single_canvas.configure(yscrollcommand=single_scrollbar.set)

        def _on_canvas_configure(evt):
            if evt.width > 0:
                single_canvas.itemconfig(single_win_id, width=evt.width)
        single_canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(evt):
            single_canvas.yview_scroll(int(-1 * (evt.delta / 120)), "units")
        single_canvas.bind("<Enter>", lambda e: single_canvas.bind_all("<MouseWheel>", _on_mousewheel))
        single_canvas.bind("<Leave>", lambda e: single_canvas.unbind_all("<MouseWheel>"))

        single_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        single_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.single_processor = SingleProcessingTab(self.single_tab, self.status_text, self.progress_var)

        def _refresh_scrollregion():
            single_canvas.configure(scrollregion=single_canvas.bbox("all"))
        self.root.after(300, _refresh_scrollregion)

        # 二次辨識标签页
        self.reanalysis_tab = tk.Frame(notebook, bg="#2b2b2b")
        notebook.add(self.reanalysis_tab, text="二次辨識")
        self.reanalysis_processor = ReAnalysisTab(self.reanalysis_tab, self.status_text, self.progress_var)

        # 进阶设置标签页
        self.advanced_tab = tk.Frame(notebook, bg="#2b2b2b")
        notebook.add(self.advanced_tab, text="進階設定")
        self.advanced_settings = AdvancedSettingsTab(self.advanced_tab)

        # 批次处理标签页
        self.batch_tab = tk.Frame(notebook, bg="#2b2b2b")
        notebook.add(self.batch_tab, text="批次處理")
        self.batch_processor = BatchProcessingTab(self.batch_tab)

        # 状态栏
        self.setup_status_bar()
        
    def setup_status_bar(self):
        status_frame = tk.Frame(self.root, bg="#1a1a1a", height=30)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        tk.Label(status_frame, text="狀態：", bg="#1a1a1a", fg="#888888").pack(side=tk.LEFT, padx=5)
        self.status_label = tk.Label(status_frame, textvariable=self.status_text, bg="#1a1a1a", fg="#00ffcc")
        self.status_label.pack(side=tk.LEFT)
        
        tk.Label(status_frame, text="  |  進度：", bg="#1a1a1a", fg="#888888").pack(side=tk.LEFT, padx=5)
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var, maximum=100, length=200)
        self.progress_bar.pack(side=tk.LEFT, padx=5)


def main():
    root = tk.Tk()
    app = AIRecognitionSystem(root)
    root.mainloop()


if __name__ == "__main__":
    main()
