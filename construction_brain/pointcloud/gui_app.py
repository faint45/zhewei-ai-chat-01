"""
築未科技 — 點雲斷面分析桌面軟件
本地運行，本地模型分析，指定位置即時斷面生成。

功能：
  1. 載入點雲（LAS/PLY/XYZ/PTS）+ 3D 散點預覽
  2. 滑桿/輸入框指定切面位置 → 即時斷面生成
  3. 尺寸標註自動生成
  4. 座標套匯（TWD97/WGS84 + 控制點）
  5. 本地 Ollama AI 斷面分析
  6. 匯出 DXF / SVG
"""
import logging
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
from typing import Optional

import numpy as np

# 確保模組可 import
_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from construction_brain.pointcloud.loader import PointCloud, load_pointcloud, scan_directory, SUPPORTED_FORMATS
from construction_brain.pointcloud.section_extractor import (
    SectionParams, SectionType, SectionResult, extract_section,
)
from construction_brain.pointcloud.exporter import export_dxf, export_svg
from construction_brain.pointcloud.coordinate import (
    ControlPoint, wgs84_to_twd97, twd97_to_wgs84,
    transform_by_control_points, apply_offset,
    batch_wgs84_to_twd97,
)
from construction_brain.pointcloud.dimension import measure_contour, measure_distance
from construction_brain.pointcloud.ai_analyzer import analyze_section, compare_sections

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

# ── 顏色方案 ────────────────────────────────────────────
BG = "#1a1a2e"
BG2 = "#16213e"
FG = "#e0e0e0"
ACCENT = "#0f3460"
HIGHLIGHT = "#53d8fb"
BTN_BG = "#0f3460"
BTN_FG = "#ffffff"
WARN = "#e94560"
SUCCESS = "#00d2d3"
GRID_COLOR = "#2a2a4a"

DEFAULT_OUTPUT = str(Path.home() / "Desktop" / "PointCloud_Output")


class PointCloudApp:
    """主應用程式"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("築未科技 — 點雲斷面分析系統 v2.0")
        self.root.geometry("1400x900")
        self.root.configure(bg=BG)
        self.root.minsize(1100, 700)

        # 狀態
        self.pcd: Optional[PointCloud] = None
        self.filepath: str = ""
        self.current_result: Optional[SectionResult] = None
        self.results_history: list[SectionResult] = []
        self.control_points: list[ControlPoint] = []
        self.output_dir = DEFAULT_OUTPUT

        # 點雲統計
        self.info: dict = {}

        self._build_ui()
        self._bind_keys()

    # ── UI 構建 ───────────────────────────────────────
    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=FG, font=("Microsoft JhengHei UI", 10))
        style.configure("TButton", background=BTN_BG, foreground=BTN_FG, font=("Microsoft JhengHei UI", 10, "bold"))
        style.map("TButton", background=[("active", HIGHLIGHT)])
        style.configure("Header.TLabel", font=("Microsoft JhengHei UI", 14, "bold"), foreground=HIGHLIGHT)
        style.configure("Info.TLabel", font=("Microsoft JhengHei UI", 9), foreground="#aaa")
        style.configure("Accent.TButton", background=HIGHLIGHT, foreground="#000")
        style.configure("TLabelframe", background=BG, foreground=HIGHLIGHT)
        style.configure("TLabelframe.Label", background=BG, foreground=HIGHLIGHT,
                        font=("Microsoft JhengHei UI", 10, "bold"))
        style.configure("TNotebook", background=BG)
        style.configure("TNotebook.Tab", background=BG2, foreground=FG, padding=[12, 4],
                        font=("Microsoft JhengHei UI", 10))
        style.map("TNotebook.Tab", background=[("selected", ACCENT)], foreground=[("selected", HIGHLIGHT)])
        style.configure("TScale", background=BG, troughcolor=BG2)

        # ── 頂部標題列 ──
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill="x", padx=10, pady=(10, 5))

        ttk.Label(top_frame, text="🏗️ 點雲斷面分析系統", style="Header.TLabel").pack(side="left")
        self.status_label = ttk.Label(top_frame, text="就緒 — 請載入點雲檔案", style="Info.TLabel")
        self.status_label.pack(side="right")

        # ── 主區域 ──
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # 左側：控制面板
        left = ttk.Frame(main_frame, width=380)
        left.pack(side="left", fill="y", padx=(0, 5))
        left.pack_propagate(False)

        self._build_file_panel(left)
        self._build_section_panel(left)
        self._build_coordinate_panel(left)
        self._build_export_panel(left)

        # 右側：預覽 + AI 分析
        right = ttk.Frame(main_frame)
        right.pack(side="left", fill="both", expand=True)

        notebook = ttk.Notebook(right)
        notebook.pack(fill="both", expand=True)

        # Tab 1: 2D 斷面預覽
        self.preview_frame = ttk.Frame(notebook)
        notebook.add(self.preview_frame, text="  📐 斷面預覽  ")
        self._build_preview(self.preview_frame)

        # Tab 2: 3D 點雲視圖
        self.cloud_frame = ttk.Frame(notebook)
        notebook.add(self.cloud_frame, text="  ☁️ 點雲總覽  ")
        self._build_cloud_view(self.cloud_frame)

        # Tab 3: AI 分析
        self.ai_frame = ttk.Frame(notebook)
        notebook.add(self.ai_frame, text="  🤖 AI 分析  ")
        self._build_ai_panel(self.ai_frame)

        # Tab 4: 歷史記錄
        self.history_frame = ttk.Frame(notebook)
        notebook.add(self.history_frame, text="  📋 歷史  ")
        self._build_history(self.history_frame)

    # ── 檔案面板 ──────────────────────────────────────
    def _build_file_panel(self, parent):
        f = ttk.LabelFrame(parent, text="📁 點雲檔案")
        f.pack(fill="x", padx=5, pady=5)

        row0 = ttk.Frame(f)
        row0.pack(fill="x", padx=5, pady=3)
        ttk.Button(row0, text="載入檔案", command=self._load_file).pack(side="left", padx=2)
        ttk.Button(row0, text="掃描資料夾", command=self._scan_dir).pack(side="left", padx=2)

        self.file_label = ttk.Label(f, text="尚未載入", style="Info.TLabel", wraplength=350)
        self.file_label.pack(fill="x", padx=5, pady=2)

        # 下採樣設定
        row1 = ttk.Frame(f)
        row1.pack(fill="x", padx=5, pady=3)
        ttk.Label(row1, text="體素大小(m):").pack(side="left")
        self.voxel_var = tk.DoubleVar(value=0.1)
        ttk.Entry(row1, textvariable=self.voxel_var, width=8).pack(side="left", padx=5)
        ttk.Label(row1, text="(0=不下採樣)", style="Info.TLabel").pack(side="left")

        # 點雲資訊
        self.info_text = tk.Text(f, height=5, bg=BG2, fg=FG, font=("Consolas", 9),
                                 relief="flat", borderwidth=0)
        self.info_text.pack(fill="x", padx=5, pady=3)

    # ── 斷面控制面板 ─────────────────────────────────
    def _build_section_panel(self, parent):
        f = ttk.LabelFrame(parent, text="✂️ 斷面設定")
        f.pack(fill="x", padx=5, pady=5)

        # 類型選擇
        row0 = ttk.Frame(f)
        row0.pack(fill="x", padx=5, pady=3)
        ttk.Label(row0, text="切面類型:").pack(side="left")
        self.section_type_var = tk.StringVar(value="plan")
        types = [("平面圖(Z)", "plan"), ("X立面", "elev_x"), ("Y立面", "elev_y"), ("剖面", "cross")]
        for text, val in types:
            ttk.Radiobutton(row0, text=text, variable=self.section_type_var, value=val).pack(side="left", padx=3)

        # 位置滑桿
        row1 = ttk.Frame(f)
        row1.pack(fill="x", padx=5, pady=3)
        ttk.Label(row1, text="位置:").pack(side="left")
        self.position_var = tk.DoubleVar(value=0.0)
        self.pos_entry = ttk.Entry(row1, textvariable=self.position_var, width=10)
        self.pos_entry.pack(side="left", padx=3)
        self.pos_unit_label = ttk.Label(row1, text="m", style="Info.TLabel")
        self.pos_unit_label.pack(side="left")

        self.pos_slider = ttk.Scale(f, from_=-50, to=50, variable=self.position_var,
                                    orient="horizontal", command=self._on_slider_change)
        self.pos_slider.pack(fill="x", padx=5, pady=2)

        self.slider_range_label = ttk.Label(f, text="範圍: 未載入", style="Info.TLabel")
        self.slider_range_label.pack(fill="x", padx=5)

        # 厚度 + 角度
        row2 = ttk.Frame(f)
        row2.pack(fill="x", padx=5, pady=3)
        ttk.Label(row2, text="厚度(m):").pack(side="left")
        self.thickness_var = tk.DoubleVar(value=0.5)
        ttk.Entry(row2, textvariable=self.thickness_var, width=8).pack(side="left", padx=3)
        ttk.Label(row2, text="角度(°):").pack(side="left", padx=(10, 0))
        self.angle_var = tk.DoubleVar(value=0.0)
        ttk.Entry(row2, textvariable=self.angle_var, width=8).pack(side="left", padx=3)

        # 降噪參數
        row3 = ttk.Frame(f)
        row3.pack(fill="x", padx=5, pady=3)
        ttk.Label(row3, text="降噪半徑:").pack(side="left")
        self.denoise_r_var = tk.DoubleVar(value=0.5)
        ttk.Entry(row3, textvariable=self.denoise_r_var, width=6).pack(side="left", padx=3)
        ttk.Label(row3, text="鄰居數:").pack(side="left")
        self.denoise_n_var = tk.IntVar(value=3)
        ttk.Entry(row3, textvariable=self.denoise_n_var, width=4).pack(side="left", padx=3)

        # 生成按鈕
        btn_row = ttk.Frame(f)
        btn_row.pack(fill="x", padx=5, pady=5)
        ttk.Button(btn_row, text="⚡ 生成斷面", style="Accent.TButton",
                   command=self._generate_section).pack(side="left", padx=2)
        ttk.Button(btn_row, text="🔄 自動多斷面", command=self._auto_sections).pack(side="left", padx=2)

    # ── 座標套匯面板 ─────────────────────────────────
    def _build_coordinate_panel(self, parent):
        f = ttk.LabelFrame(parent, text="🌐 座標套匯")
        f.pack(fill="x", padx=5, pady=5)

        row0 = ttk.Frame(f)
        row0.pack(fill="x", padx=5, pady=3)
        ttk.Label(row0, text="偏移量:").pack(side="left")
        ttk.Label(row0, text="ΔE:").pack(side="left", padx=(5, 0))
        self.dx_var = tk.DoubleVar(value=0.0)
        ttk.Entry(row0, textvariable=self.dx_var, width=10).pack(side="left", padx=2)
        ttk.Label(row0, text="ΔN:").pack(side="left")
        self.dy_var = tk.DoubleVar(value=0.0)
        ttk.Entry(row0, textvariable=self.dy_var, width=10).pack(side="left", padx=2)

        row1 = ttk.Frame(f)
        row1.pack(fill="x", padx=5, pady=3)
        ttk.Label(row1, text="ΔH:").pack(side="left")
        self.dz_var = tk.DoubleVar(value=0.0)
        ttk.Entry(row1, textvariable=self.dz_var, width=10).pack(side="left", padx=2)

        btn_row = ttk.Frame(f)
        btn_row.pack(fill="x", padx=5, pady=3)
        ttk.Button(btn_row, text="套用偏移", command=self._apply_offset).pack(side="left", padx=2)
        ttk.Button(btn_row, text="匯入控制點CSV", command=self._import_control_points).pack(side="left", padx=2)
        ttk.Button(btn_row, text="WGS84→TWD97", command=self._convert_wgs84).pack(side="left", padx=2)

        self.coord_info = ttk.Label(f, text="", style="Info.TLabel")
        self.coord_info.pack(fill="x", padx=5, pady=2)

    # ── 匯出面板 ─────────────────────────────────────
    def _build_export_panel(self, parent):
        f = ttk.LabelFrame(parent, text="💾 匯出")
        f.pack(fill="x", padx=5, pady=5)

        row0 = ttk.Frame(f)
        row0.pack(fill="x", padx=5, pady=3)
        ttk.Button(row0, text="匯出 DXF", command=lambda: self._export("dxf")).pack(side="left", padx=2)
        ttk.Button(row0, text="匯出 SVG", command=lambda: self._export("svg")).pack(side="left", padx=2)
        ttk.Button(row0, text="匯出全部", command=self._export_all).pack(side="left", padx=2)

        row1 = ttk.Frame(f)
        row1.pack(fill="x", padx=5, pady=3)
        self.show_grid_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(row1, text="座標網格", variable=self.show_grid_var).pack(side="left")
        self.show_dim_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(row1, text="尺寸標註", variable=self.show_dim_var).pack(side="left")
        self.show_pts_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(row1, text="散點圖", variable=self.show_pts_var).pack(side="left")

        self.export_label = ttk.Label(f, text=f"輸出目錄: {DEFAULT_OUTPUT}", style="Info.TLabel", wraplength=350)
        self.export_label.pack(fill="x", padx=5, pady=2)

    # ── 2D 預覽 Canvas ───────────────────────────────
    def _build_preview(self, parent):
        self.preview_canvas = tk.Canvas(parent, bg=BG2, highlightthickness=0)
        self.preview_canvas.pack(fill="both", expand=True, padx=5, pady=5)
        self.preview_info = ttk.Label(parent, text="載入點雲後，設定位置並生成斷面", style="Info.TLabel")
        self.preview_info.pack(fill="x", padx=5, pady=2)

    # ── 3D 點雲視圖 ──────────────────────────────────
    def _build_cloud_view(self, parent):
        self.cloud_canvas = tk.Canvas(parent, bg="#0a0a1a", highlightthickness=0)
        self.cloud_canvas.pack(fill="both", expand=True, padx=5, pady=5)
        ctrl = ttk.Frame(parent)
        ctrl.pack(fill="x", padx=5, pady=2)
        ttk.Label(ctrl, text="投影:").pack(side="left")
        self.view_var = tk.StringVar(value="top")
        for text, val in [("俯視(XY)", "top"), ("前視(XZ)", "front"), ("側視(YZ)", "side")]:
            ttk.Radiobutton(ctrl, text=text, variable=self.view_var, value=val,
                            command=self._draw_cloud).pack(side="left", padx=3)
        self.cloud_info = ttk.Label(parent, text="", style="Info.TLabel")
        self.cloud_info.pack(fill="x", padx=5)

    # ── AI 分析面板 ──────────────────────────────────
    def _build_ai_panel(self, parent):
        top = ttk.Frame(parent)
        top.pack(fill="x", padx=5, pady=5)
        ttk.Button(top, text="🤖 AI 分析當前斷面", style="Accent.TButton",
                   command=self._ai_analyze).pack(side="left", padx=2)
        ttk.Button(top, text="📊 比較所有斷面", command=self._ai_compare).pack(side="left", padx=2)

        ttk.Label(top, text="模型:").pack(side="left", padx=(10, 0))
        self.model_var = tk.StringVar(value="zhewei-brain-v5-structured")
        model_combo = ttk.Combobox(top, textvariable=self.model_var, width=18,
                                   values=["zhewei-brain-v5-structured", "zhewei-brain-v5", "zhewei-brain-v4", "zhewei-brain-v3", "qwen3:4b"])
        model_combo.pack(side="left", padx=3)

        self.ai_text = scrolledtext.ScrolledText(parent, bg=BG2, fg=FG, font=("Consolas", 10),
                                                  wrap="word", relief="flat")
        self.ai_text.pack(fill="both", expand=True, padx=5, pady=5)

    # ── 歷史記錄面板 ─────────────────────────────────
    def _build_history(self, parent):
        cols = ("type", "position", "points", "contours", "width", "height")
        self.history_tree = ttk.Treeview(parent, columns=cols, show="headings", height=15)
        for col, hdr, w in [
            ("type", "類型", 100), ("position", "位置(m)", 80), ("points", "點數", 80),
            ("contours", "輪廓", 60), ("width", "寬度(m)", 80), ("height", "高度(m)", 80),
        ]:
            self.history_tree.heading(col, text=hdr)
            self.history_tree.column(col, width=w, anchor="center")
        self.history_tree.pack(fill="both", expand=True, padx=5, pady=5)
        self.history_tree.bind("<Double-1>", self._on_history_select)

        btn_row = ttk.Frame(parent)
        btn_row.pack(fill="x", padx=5, pady=3)
        ttk.Button(btn_row, text="清除歷史", command=self._clear_history).pack(side="left")
        ttk.Button(btn_row, text="匯出選取的 DXF", command=lambda: self._export_selected("dxf")).pack(side="left", padx=5)

    # ── 快捷鍵 ────────────────────────────────────────
    def _bind_keys(self):
        self.root.bind("<Control-o>", lambda e: self._load_file())
        self.root.bind("<Return>", lambda e: self._generate_section())
        self.root.bind("<Control-s>", lambda e: self._export("dxf"))
        self.root.bind("<Control-e>", lambda e: self._export_all())

    # ══════════════════════════════════════════════════
    # 核心功能
    # ══════════════════════════════════════════════════

    def _set_status(self, msg: str, color: str = FG):
        self.status_label.configure(text=msg, foreground=color)
        self.root.update_idletasks()

    def _load_file(self):
        exts = " ".join(f"*{e}" for e in SUPPORTED_FORMATS)
        filepath = filedialog.askopenfilename(
            title="選擇點雲檔案",
            filetypes=[("點雲檔案", exts), ("LAS/LAZ", "*.las *.laz"),
                       ("PLY", "*.ply"), ("XYZ", "*.xyz"), ("PTS", "*.pts"), ("所有檔案", "*.*")]
        )
        if not filepath:
            return

        self._set_status(f"載入中: {Path(filepath).name} ...", HIGHLIGHT)

        def _do_load():
            try:
                voxel = self.voxel_var.get()
                self.pcd = load_pointcloud(filepath, voxel_size=voxel if voxel > 0 else None)
                self.filepath = filepath
                self.info = self._compute_info()
                self.root.after(0, self._on_loaded)
            except Exception as e:
                self.root.after(0, lambda: self._on_load_error(str(e)))

        threading.Thread(target=_do_load, daemon=True).start()

    def _on_loaded(self):
        name = Path(self.filepath).name
        n = len(self.pcd)
        self.file_label.configure(text=f"✅ {name} ({n:,} 點)")
        self._set_status(f"已載入 {name} — {n:,} 點", SUCCESS)

        # 更新資訊
        self.info_text.delete("1.0", "end")
        for k, v in self.info.items():
            if isinstance(v, float):
                self.info_text.insert("end", f"{k}: {v:.3f}\n")
            else:
                self.info_text.insert("end", f"{k}: {v}\n")

        # 更新滑桿範圍
        self._update_slider_range()
        self._draw_cloud()

    def _on_load_error(self, msg: str):
        self._set_status(f"載入失敗: {msg}", WARN)
        messagebox.showerror("載入失敗", msg)

    def _compute_info(self) -> dict:
        pts = self.pcd.points
        return {
            "檔案": Path(self.filepath).name,
            "點數": f"{len(pts):,}",
            "X 範圍": f"{pts[:, 0].min():.2f} ~ {pts[:, 0].max():.2f}",
            "Y 範圍": f"{pts[:, 1].min():.2f} ~ {pts[:, 1].max():.2f}",
            "Z 範圍": f"{pts[:, 2].min():.2f} ~ {pts[:, 2].max():.2f}",
            "寬度(X)": float(pts[:, 0].max() - pts[:, 0].min()),
            "深度(Y)": float(pts[:, 1].max() - pts[:, 1].min()),
            "高度(Z)": float(pts[:, 2].max() - pts[:, 2].min()),
        }

    def _update_slider_range(self):
        sec = self.section_type_var.get()
        pts = self.pcd.points
        if sec == "plan":
            lo, hi = float(pts[:, 2].min()), float(pts[:, 2].max())
            label = f"Z: {lo:.1f} ~ {hi:.1f} m"
        elif sec == "elev_x":
            lo, hi = float(pts[:, 0].min()), float(pts[:, 0].max())
            label = f"X: {lo:.1f} ~ {hi:.1f} m"
        elif sec == "elev_y":
            lo, hi = float(pts[:, 1].min()), float(pts[:, 1].max())
            label = f"Y: {lo:.1f} ~ {hi:.1f} m"
        else:
            lo, hi = -100, 100
            label = "任意位置"

        self.pos_slider.configure(from_=lo, to=hi)
        mid = (lo + hi) / 2
        self.position_var.set(round(mid, 2))
        self.slider_range_label.configure(text=f"範圍: {label}")

    def _on_slider_change(self, _=None):
        pass  # position_var 已綁定

    def _scan_dir(self):
        d = filedialog.askdirectory(title="選擇點雲資料夾")
        if not d:
            return
        files = scan_directory(d)
        if not files:
            messagebox.showinfo("掃描結果", "未找到支援的點雲檔案")
            return

        # 選擇檔案對話框
        win = tk.Toplevel(self.root)
        win.title("選擇點雲檔案")
        win.geometry("500x400")
        win.configure(bg=BG)

        listbox = tk.Listbox(win, bg=BG2, fg=FG, font=("Consolas", 10), selectmode="single")
        listbox.pack(fill="both", expand=True, padx=10, pady=10)
        for f in files:
            listbox.insert("end", f"{f['name']}  ({f['size_mb']} MB, {f['format']})")

        def _select():
            sel = listbox.curselection()
            if sel:
                path = files[sel[0]]["path"]
                win.destroy()
                self.voxel_var.set(0.1)
                self._set_status(f"載入中: {Path(path).name} ...", HIGHLIGHT)

                def _do():
                    try:
                        v = self.voxel_var.get()
                        self.pcd = load_pointcloud(path, voxel_size=v if v > 0 else None)
                        self.filepath = path
                        self.info = self._compute_info()
                        self.root.after(0, self._on_loaded)
                    except Exception as e:
                        self.root.after(0, lambda: self._on_load_error(str(e)))

                threading.Thread(target=_do, daemon=True).start()

        ttk.Button(win, text="載入", command=_select).pack(pady=5)

    # ── 斷面生成 ─────────────────────────────────────
    def _generate_section(self):
        if self.pcd is None:
            messagebox.showwarning("提示", "請先載入點雲檔案")
            return

        sec_type_map = {
            "plan": SectionType.PLAN,
            "elev_x": SectionType.ELEVATION_X,
            "elev_y": SectionType.ELEVATION_Y,
            "cross": SectionType.CROSS,
        }
        sec_type = sec_type_map[self.section_type_var.get()]
        position = self.position_var.get()
        thickness = self.thickness_var.get()
        angle = self.angle_var.get()

        self._set_status(f"生成斷面: {sec_type.value} @ {position:.2f}m ...", HIGHLIGHT)

        params = SectionParams(
            section_type=sec_type,
            position=position,
            thickness=thickness,
            angle=angle,
            denoise_radius=self.denoise_r_var.get(),
            denoise_neighbors=self.denoise_n_var.get(),
        )

        def _do():
            try:
                result = extract_section(self.pcd, params)
                self.root.after(0, lambda: self._on_section_done(result))
            except Exception as e:
                self.root.after(0, lambda: self._set_status(f"生成失敗: {e}", WARN))

        threading.Thread(target=_do, daemon=True).start()

    def _on_section_done(self, result: SectionResult):
        self.current_result = result
        self.results_history.append(result)

        n = result.n_points
        nc = len(result.contours)
        self._set_status(f"✅ 斷面完成: {n:,} 點, {nc} 輪廓", SUCCESS)

        self._draw_section(result)
        self._add_to_history(result)

    def _auto_sections(self):
        if self.pcd is None:
            messagebox.showwarning("提示", "請先載入點雲檔案")
            return

        from construction_brain.pointcloud.section_extractor import auto_sections
        thickness = self.thickness_var.get()
        self._set_status("自動生成多斷面...", HIGHLIGHT)

        def _do():
            try:
                results = auto_sections(self.pcd, n_plans=3, n_elevations=4, thickness=thickness)
                self.root.after(0, lambda: self._on_auto_done(results))
            except Exception as e:
                self.root.after(0, lambda: self._set_status(f"自動生成失敗: {e}", WARN))

        threading.Thread(target=_do, daemon=True).start()

    def _on_auto_done(self, results: list[SectionResult]):
        valid = [r for r in results if r.n_points > 0]
        self.results_history.extend(valid)
        if valid:
            self.current_result = valid[0]
            self._draw_section(valid[0])
        for r in valid:
            self._add_to_history(r)
        self._set_status(f"✅ 自動生成 {len(valid)}/{len(results)} 個斷面", SUCCESS)

    # ── 繪圖 ─────────────────────────────────────────
    def _draw_section(self, result: SectionResult):
        canvas = self.preview_canvas
        canvas.delete("all")

        if result.n_points == 0:
            canvas.create_text(canvas.winfo_width() / 2, canvas.winfo_height() / 2,
                               text="此切面無資料\n請調整位置或增加厚度",
                               fill=WARN, font=("Microsoft JhengHei UI", 14))
            return

        cw = canvas.winfo_width() or 800
        ch = canvas.winfo_height() or 600
        margin = 60

        pts = result.points_2d
        bounds = result.bounds
        if not bounds:
            return

        data_w = bounds["max_x"] - bounds["min_x"]
        data_h = bounds["max_y"] - bounds["min_y"]
        if data_w == 0 or data_h == 0:
            return

        view_w = cw - margin * 2
        view_h = ch - margin * 2
        scale = min(view_w / data_w, view_h / data_h)
        ox = margin + (view_w - data_w * scale) / 2
        oy = margin + (view_h - data_h * scale) / 2

        def tx(x, y):
            sx = (x - bounds["min_x"]) * scale + ox
            sy = ch - ((y - bounds["min_y"]) * scale + oy)
            return sx, sy

        # 網格
        grid_sp = self._auto_grid(max(data_w, data_h))
        x = bounds["min_x"] - (bounds["min_x"] % grid_sp)
        while x <= bounds["max_x"] + grid_sp:
            sx, _ = tx(x, 0)
            canvas.create_line(sx, margin, sx, ch - margin, fill=GRID_COLOR, dash=(2, 4))
            canvas.create_text(sx, ch - margin + 12, text=f"{x:.1f}", fill="#555",
                               font=("Consolas", 7))
            x += grid_sp

        y = bounds["min_y"] - (bounds["min_y"] % grid_sp)
        while y <= bounds["max_y"] + grid_sp:
            _, sy = tx(0, y)
            canvas.create_line(margin, sy, cw - margin, sy, fill=GRID_COLOR, dash=(2, 4))
            canvas.create_text(margin - 5, sy, text=f"{y:.1f}", fill="#555",
                               font=("Consolas", 7), anchor="e")
            y += grid_sp

        # 散點
        max_draw = min(len(pts), 3000)
        if len(pts) > max_draw:
            idx = np.random.choice(len(pts), max_draw, replace=False)
            draw_pts = pts[idx]
        else:
            draw_pts = pts
        for p in draw_pts:
            sx, sy = tx(p[0], p[1])
            canvas.create_oval(sx - 1, sy - 1, sx + 1, sy + 1, fill="#4488cc", outline="")

        # 輪廓
        for contour in result.contours:
            if len(contour) < 2:
                continue
            coords = []
            for x, y in contour:
                sx, sy = tx(x, y)
                coords.extend([sx, sy])
            canvas.create_line(*coords, fill=HIGHLIGHT, width=2, smooth=True)

        # 尺寸標註
        # 寬度
        sx1, sy1 = tx(bounds["min_x"], bounds["min_y"])
        sx2, sy2 = tx(bounds["max_x"], bounds["min_y"])
        dim_y = sy1 + 30
        canvas.create_line(sx1, dim_y, sx2, dim_y, fill=WARN, width=1)
        canvas.create_line(sx1, sy1, sx1, dim_y, fill=WARN, dash=(2, 2))
        canvas.create_line(sx2, sy2, sx2, dim_y, fill=WARN, dash=(2, 2))
        canvas.create_text((sx1 + sx2) / 2, dim_y + 12, text=f"{data_w:.3f}m",
                           fill=WARN, font=("Consolas", 9, "bold"))
        # 高度
        sx1, sy1 = tx(bounds["min_x"], bounds["min_y"])
        _, sy2 = tx(bounds["min_x"], bounds["max_y"])
        dim_x = sx1 - 30
        canvas.create_line(dim_x, sy1, dim_x, sy2, fill=WARN, width=1)
        canvas.create_line(sx1, sy1, dim_x, sy1, fill=WARN, dash=(2, 2))
        canvas.create_line(sx1, sy2, dim_x, sy2, fill=WARN, dash=(2, 2))
        canvas.create_text(dim_x - 5, (sy1 + sy2) / 2, text=f"{data_h:.3f}m",
                           fill=WARN, font=("Consolas", 9, "bold"), angle=90)

        # 標題
        type_names = {"plan": "平面圖", "elev_x": "X立面", "elev_y": "Y立面", "cross": "剖面"}
        title = f"{type_names.get(result.section_type.value, '')} @ {result.position:.2f}m"
        canvas.create_text(cw / 2, 15, text=title, fill=HIGHLIGHT,
                           font=("Microsoft JhengHei UI", 12, "bold"))

        self.preview_info.configure(
            text=f"點數: {result.n_points:,}  輪廓: {len(result.contours)}  "
                 f"寬: {data_w:.3f}m  高: {data_h:.3f}m"
        )

    def _draw_cloud(self):
        if self.pcd is None:
            return

        canvas = self.cloud_canvas
        canvas.delete("all")
        cw = canvas.winfo_width() or 800
        ch = canvas.winfo_height() or 600
        margin = 40

        pts = self.pcd.points
        view = self.view_var.get()

        # 選擇投影軸
        if view == "top":
            px, py = pts[:, 0], pts[:, 1]
            xlabel, ylabel = "X", "Y"
        elif view == "front":
            px, py = pts[:, 0], pts[:, 2]
            xlabel, ylabel = "X", "Z"
        else:
            px, py = pts[:, 1], pts[:, 2]
            xlabel, ylabel = "Y", "Z"

        # 下採樣顯示
        max_draw = 10000
        if len(px) > max_draw:
            idx = np.random.choice(len(px), max_draw, replace=False)
            px, py = px[idx], py[idx]

        xmin, xmax = px.min(), px.max()
        ymin, ymax = py.min(), py.max()
        data_w = xmax - xmin or 1
        data_h = ymax - ymin or 1
        view_w = cw - margin * 2
        view_h = ch - margin * 2
        scale = min(view_w / data_w, view_h / data_h)
        ox = margin + (view_w - data_w * scale) / 2
        oy = margin + (view_h - data_h * scale) / 2

        # 繪製
        for i in range(len(px)):
            sx = (px[i] - xmin) * scale + ox
            sy = ch - ((py[i] - ymin) * scale + oy)
            # 用 Z 值著色
            canvas.create_oval(sx, sy, sx + 2, sy + 2, fill="#3498db", outline="")

        # 軸標
        canvas.create_text(cw / 2, ch - 5, text=xlabel, fill="#888", font=("Consolas", 10))
        canvas.create_text(10, ch / 2, text=ylabel, fill="#888", font=("Consolas", 10), angle=90)
        canvas.create_text(cw / 2, 12, text=f"{view} 視圖 ({len(self.pcd):,} 點)",
                           fill=HIGHLIGHT, font=("Microsoft JhengHei UI", 11, "bold"))

        # 切面指示線
        if self.current_result:
            pos = self.current_result.position
            sec = self.current_result.section_type
            if sec == SectionType.PLAN and view in ("front", "side"):
                sy = ch - ((pos - ymin) * scale + oy)
                canvas.create_line(margin, sy, cw - margin, sy, fill=WARN, width=2, dash=(6, 3))
            elif sec == SectionType.ELEVATION_X and view == "top":
                sx = (pos - xmin) * scale + ox
                canvas.create_line(sx, margin, sx, ch - margin, fill=WARN, width=2, dash=(6, 3))

    # ── 座標功能 ─────────────────────────────────────
    def _apply_offset(self):
        if self.pcd is None:
            messagebox.showwarning("提示", "請先載入點雲")
            return
        dx, dy, dz = self.dx_var.get(), self.dy_var.get(), self.dz_var.get()
        self.pcd.points = apply_offset(self.pcd.points, dx, dy, dz)
        self.info = self._compute_info()
        self._on_loaded()
        self.coord_info.configure(text=f"✅ 已平移 ΔE={dx}, ΔN={dy}, ΔH={dz}")

    def _import_control_points(self):
        filepath = filedialog.askopenfilename(
            title="匯入控制點 CSV",
            filetypes=[("CSV", "*.csv"), ("TXT", "*.txt"), ("所有", "*.*")]
        )
        if not filepath:
            return
        try:
            data = np.loadtxt(filepath, delimiter=",", skiprows=1)
            # 格式: name, local_x, local_y, local_z, target_x, target_y, target_z
            # 或: local_x, local_y, local_z, target_x, target_y, target_z
            if data.shape[1] >= 6:
                cps = []
                for i, row in enumerate(data):
                    cps.append(ControlPoint(
                        name=f"CP{i+1}",
                        local_xyz=row[:3],
                        target_xyz=row[3:6],
                    ))
                self.control_points = cps

                result = transform_by_control_points(self.pcd.points, cps)
                self.pcd.points = result.points
                self.info = self._compute_info()
                self._on_loaded()
                self.coord_info.configure(
                    text=f"✅ {result.n_control_points} 控制點套匯完成, RMSE={result.rmse:.4f}m"
                )
            else:
                messagebox.showerror("格式錯誤", "CSV 需至少 6 欄: local_x,y,z,target_x,y,z")
        except Exception as e:
            messagebox.showerror("匯入失敗", str(e))

    def _convert_wgs84(self):
        if self.pcd is None:
            messagebox.showwarning("提示", "請先載入點雲")
            return
        pts = self.pcd.points
        # 判斷是否為 WGS84（經緯度範圍）
        if pts[:, 0].max() < 180 and pts[:, 1].max() < 90:
            self._set_status("轉換 WGS84 → TWD97 ...", HIGHLIGHT)
            self.pcd.points = batch_wgs84_to_twd97(pts)
            self.info = self._compute_info()
            self._on_loaded()
            self.coord_info.configure(text="✅ WGS84 → TWD97 轉換完成")
        else:
            messagebox.showinfo("提示", "點雲座標似乎不是 WGS84（經緯度），無需轉換")

    # ── 匯出 ─────────────────────────────────────────
    def _export(self, fmt: str):
        if self.current_result is None:
            messagebox.showwarning("提示", "請先生成斷面")
            return

        result = self.current_result
        type_name = result.section_type.value
        pos_str = f"{result.position:.1f}".replace(".", "_").replace("-", "n")

        if fmt == "dxf":
            filepath = filedialog.asksaveasfilename(
                title="匯出 DXF",
                defaultextension=".dxf",
                initialfile=f"{type_name}_{pos_str}.dxf",
                filetypes=[("AutoCAD DXF", "*.dxf")]
            )
            if filepath:
                export_dxf(result, filepath,
                           show_points=self.show_pts_var.get(),
                           show_grid=self.show_grid_var.get(),
                           show_dimensions=self.show_dim_var.get())
                self._set_status(f"✅ DXF 已匯出: {filepath}", SUCCESS)
        else:
            filepath = filedialog.asksaveasfilename(
                title="匯出 SVG",
                defaultextension=".svg",
                initialfile=f"{type_name}_{pos_str}.svg",
                filetypes=[("SVG", "*.svg")]
            )
            if filepath:
                export_svg(result, filepath)
                self._set_status(f"✅ SVG 已匯出: {filepath}", SUCCESS)

    def _export_all(self):
        if not self.results_history:
            messagebox.showwarning("提示", "無斷面可匯出")
            return

        out_dir = filedialog.askdirectory(title="選擇匯出目錄", initialdir=self.output_dir)
        if not out_dir:
            return
        self.output_dir = out_dir

        count = 0
        for result in self.results_history:
            if result.n_points == 0:
                continue
            type_name = result.section_type.value
            pos_str = f"{result.position:.1f}".replace(".", "_").replace("-", "n")
            base = f"{type_name}_{pos_str}"
            export_dxf(result, str(Path(out_dir) / f"{base}.dxf"),
                       show_points=self.show_pts_var.get(),
                       show_grid=self.show_grid_var.get(),
                       show_dimensions=self.show_dim_var.get())
            export_svg(result, str(Path(out_dir) / f"{base}.svg"))
            count += 1

        self._set_status(f"✅ 已匯出 {count} 個斷面到 {out_dir}", SUCCESS)
        messagebox.showinfo("匯出完成", f"已匯出 {count} 個斷面 (DXF+SVG)\n目錄: {out_dir}")

    def _export_selected(self, fmt: str):
        sel = self.history_tree.selection()
        if not sel:
            messagebox.showwarning("提示", "請先選擇一個斷面")
            return
        idx = self.history_tree.index(sel[0])
        if idx < len(self.results_history):
            self.current_result = self.results_history[idx]
            self._export(fmt)

    # ── 歷史 ─────────────────────────────────────────
    def _add_to_history(self, result: SectionResult):
        bounds = result.bounds
        w = bounds.get("max_x", 0) - bounds.get("min_x", 0) if bounds else 0
        h = bounds.get("max_y", 0) - bounds.get("min_y", 0) if bounds else 0
        self.history_tree.insert("", "end", values=(
            result.section_type.value,
            f"{result.position:.2f}",
            f"{result.n_points:,}",
            len(result.contours),
            f"{w:.3f}",
            f"{h:.3f}",
        ))

    def _on_history_select(self, event):
        sel = self.history_tree.selection()
        if sel:
            idx = self.history_tree.index(sel[0])
            if idx < len(self.results_history):
                self.current_result = self.results_history[idx]
                self._draw_section(self.current_result)

    def _clear_history(self):
        self.history_tree.delete(*self.history_tree.get_children())
        self.results_history.clear()

    # ── AI 分析 ──────────────────────────────────────
    def _ai_analyze(self):
        if self.current_result is None:
            messagebox.showwarning("提示", "請先生成斷面")
            return

        self.ai_text.delete("1.0", "end")
        self.ai_text.insert("end", "🤖 正在分析（本地 Ollama，0 雲端 token）...\n\n")
        self._set_status("AI 分析中...", HIGHLIGHT)

        model = self.model_var.get()
        result = self.current_result

        def _do():
            try:
                report = analyze_section(result, model=model)
                self.root.after(0, lambda: self._show_report(report))
            except Exception as e:
                self.root.after(0, lambda: self._show_ai_error(str(e)))

        threading.Thread(target=_do, daemon=True).start()

    def _show_report(self, report):
        self.ai_text.delete("1.0", "end")
        self.ai_text.insert("end", f"📋 斷面分析報告\n", "header")
        self.ai_text.insert("end", f"{'='*50}\n\n")
        self.ai_text.insert("end", f"模型: {report.model_used}\n")
        self.ai_text.insert("end", f"類型: {report.section_type} @ {report.position:.2f}m\n\n")

        self.ai_text.insert("end", "📝 摘要:\n")
        self.ai_text.insert("end", f"  {report.summary}\n\n")

        if report.features:
            self.ai_text.insert("end", "🔍 特徵:\n")
            for f in report.features:
                self.ai_text.insert("end", f"  • {f}\n")
            self.ai_text.insert("end", "\n")

        if report.issues:
            self.ai_text.insert("end", "⚠️ 問題:\n")
            for i in report.issues:
                self.ai_text.insert("end", f"  • {i}\n")
            self.ai_text.insert("end", "\n")

        if report.recommendations:
            self.ai_text.insert("end", "💡 建議:\n")
            for r in report.recommendations:
                self.ai_text.insert("end", f"  • {r}\n")
            self.ai_text.insert("end", "\n")

        if report.measurements:
            self.ai_text.insert("end", "📐 量測數據:\n")
            for k, v in report.measurements.items():
                if isinstance(v, float):
                    self.ai_text.insert("end", f"  {k}: {v:.4f}\n")
                else:
                    self.ai_text.insert("end", f"  {k}: {v}\n")

        self._set_status("✅ AI 分析完成 (本地模型)", SUCCESS)

    def _show_ai_error(self, msg: str):
        self.ai_text.delete("1.0", "end")
        self.ai_text.insert("end", f"❌ 分析失敗: {msg}\n\n")
        self.ai_text.insert("end", "請確認 Ollama 已啟動：\n")
        self.ai_text.insert("end", "  ollama serve\n")
        self._set_status(f"AI 分析失敗: {msg}", WARN)

    def _ai_compare(self):
        if len(self.results_history) < 2:
            messagebox.showwarning("提示", "需要至少 2 個斷面才能比較")
            return

        self.ai_text.delete("1.0", "end")
        self.ai_text.insert("end", "📊 正在比較所有斷面...\n\n")

        model = self.model_var.get()

        def _do():
            try:
                text = compare_sections(self.results_history, model=model)
                self.root.after(0, lambda: self._show_comparison(text))
            except Exception as e:
                self.root.after(0, lambda: self._show_ai_error(str(e)))

        threading.Thread(target=_do, daemon=True).start()

    def _show_comparison(self, text: str):
        self.ai_text.delete("1.0", "end")
        self.ai_text.insert("end", "📊 多斷面比較報告\n")
        self.ai_text.insert("end", f"{'='*50}\n\n")
        self.ai_text.insert("end", text)
        self._set_status("✅ 比較分析完成", SUCCESS)

    # ── 工具 ─────────────────────────────────────────
    @staticmethod
    def _auto_grid(extent: float) -> float:
        if extent <= 2:
            return 0.5
        elif extent <= 10:
            return 1.0
        elif extent <= 50:
            return 5.0
        elif extent <= 200:
            return 10.0
        elif extent <= 1000:
            return 50.0
        else:
            return 100.0


def main():
    root = tk.Tk()
    # 設定 DPI awareness (Windows)
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = PointCloudApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
