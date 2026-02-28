"""
築未科技 — 切面輸出器
將 SectionResult 輸出為 DXF (AutoCAD 相容) 或 SVG 格式。

DXF：給工程師用 AutoCAD / BricsCAD 開啟
SVG：給網頁預覽或嵌入報告
"""
import logging
from pathlib import Path
from typing import Optional

import numpy as np

from .section_extractor import SectionResult, SectionType

logger = logging.getLogger(__name__)


def export_dxf(result: SectionResult, output_path: str, scale: float = 1.0,
               layer_name: Optional[str] = None,
               show_points: bool = True, show_grid: bool = True,
               show_dimensions: bool = True, grid_spacing: float = 0.0):
    """
    匯出切面為 DXF 檔案（含尺寸標註、座標網格、散點圖）。

    Args:
        result: SectionResult 切面結果
        output_path: 輸出路徑 (.dxf)
        scale: 縮放比例（預設 1:1，公尺）
        layer_name: 圖層名稱
        show_points: 是否顯示散點
        show_grid: 是否顯示座標網格
        show_dimensions: 是否顯示尺寸標註
        grid_spacing: 網格間距 (0=自動)
    """
    import ezdxf
    from .dimension import auto_dimensions, add_dimensions_to_dxf, add_grid_to_dxf

    doc = ezdxf.new(dxfversion="R2010")
    msp = doc.modelspace()

    if layer_name is None:
        layer_name = _default_layer_name(result)

    doc.layers.add(layer_name, color=7)
    doc.layers.add("點雲", color=30)      # 淺藍
    doc.layers.add("標註", color=1)       # 紅
    doc.layers.add("網格", color=8)       # 灰

    # 繪製輪廓線
    for contour in result.contours:
        if len(contour) < 2:
            continue
        scaled = [(x * scale, y * scale) for x, y in contour]
        msp.add_lwpolyline(scaled, dxfattribs={"layer": layer_name, "lineweight": 35})

    # 繪製散點
    if show_points and result.n_points > 0:
        pts = result.points_2d
        # 限制散點數量避免 DXF 過大
        max_pts = min(len(pts), 5000)
        if len(pts) > max_pts:
            idx = np.random.choice(len(pts), max_pts, replace=False)
            pts = pts[idx]
        for p in pts:
            msp.add_point((p[0] * scale, p[1] * scale),
                          dxfattribs={"layer": "點雲"})

    bounds = result.bounds

    # 座標網格
    if show_grid and bounds:
        add_grid_to_dxf(msp, bounds, spacing=grid_spacing, scale=scale)

    # 尺寸標註
    if show_dimensions and bounds:
        dims = auto_dimensions(bounds, result.contours, result.section_type.value)
        add_dimensions_to_dxf(msp, dims, scale=scale)

    # 標題
    if bounds:
        cx = (bounds["min_x"] + bounds["max_x"]) / 2 * scale
        cy = bounds["max_y"] * scale + 2.0
        label = _section_label(result)
        msp.add_text(
            label,
            dxfattribs={
                "layer": layer_name,
                "height": 0.5 * scale,
                "insert": (cx, cy),
                "halign": 1,
            }
        )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(output_path)
    logger.info(f"DXF 匯出: {output_path} ({len(result.contours)} 輪廓, {result.n_points} 點)")
    return output_path


def export_svg(result: SectionResult, output_path: str, width: int = 800, height: int = 600,
               stroke_color: str = "#333333", stroke_width: float = 1.0, background: str = "#ffffff"):
    """
    匯出切面為 SVG 檔案。

    Args:
        result: SectionResult
        output_path: 輸出路徑 (.svg)
        width: SVG 寬度 (px)
        height: SVG 高度 (px)
    """
    bounds = result.bounds
    if not bounds or result.n_points == 0:
        logger.warning("切面無資料，跳過 SVG 匯出")
        return None

    # 計算變換（點雲座標 → SVG 座標）
    data_w = bounds["max_x"] - bounds["min_x"]
    data_h = bounds["max_y"] - bounds["min_y"]

    if data_w == 0 or data_h == 0:
        logger.warning("切面尺寸為零")
        return None

    margin = 40
    view_w = width - margin * 2
    view_h = height - margin * 2

    scale = min(view_w / data_w, view_h / data_h)
    offset_x = margin + (view_w - data_w * scale) / 2
    offset_y = margin + (view_h - data_h * scale) / 2

    def transform(x, y):
        sx = (x - bounds["min_x"]) * scale + offset_x
        sy = height - ((y - bounds["min_y"]) * scale + offset_y)  # Y 翻轉
        return sx, sy

    # 建立 SVG
    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">')
    lines.append(f'  <rect width="{width}" height="{height}" fill="{background}"/>')

    # 標題
    label = _section_label(result)
    lines.append(f'  <text x="{width/2}" y="25" text-anchor="middle" font-family="sans-serif" '
                 f'font-size="14" fill="#333">{label}</text>')

    # 繪製輪廓
    for contour in result.contours:
        if len(contour) < 2:
            continue
        path_data = []
        for i, (x, y) in enumerate(contour):
            sx, sy = transform(x, y)
            cmd = "M" if i == 0 else "L"
            path_data.append(f"{cmd}{sx:.1f},{sy:.1f}")
        path_data.append("Z")
        d = " ".join(path_data)
        lines.append(f'  <path d="{d}" fill="none" stroke="{stroke_color}" stroke-width="{stroke_width}"/>')

    # 尺寸標註
    if data_w > 0:
        x1, y1 = transform(bounds["min_x"], bounds["min_y"])
        x2, y2 = transform(bounds["max_x"], bounds["min_y"])
        dim_y = y1 + 20
        lines.append(f'  <line x1="{x1:.1f}" y1="{dim_y}" x2="{x2:.1f}" y2="{dim_y}" '
                     f'stroke="#999" stroke-width="0.5"/>')
        lines.append(f'  <text x="{(x1+x2)/2:.1f}" y="{dim_y+15}" text-anchor="middle" '
                     f'font-family="sans-serif" font-size="11" fill="#666">{data_w:.2f}m</text>')

    if data_h > 0:
        x1, y1 = transform(bounds["min_x"], bounds["min_y"])
        _, y2 = transform(bounds["min_x"], bounds["max_y"])
        dim_x = x1 - 15
        lines.append(f'  <line x1="{dim_x}" y1="{y1:.1f}" x2="{dim_x}" y2="{y2:.1f}" '
                     f'stroke="#999" stroke-width="0.5"/>')
        lines.append(f'  <text x="{dim_x-5}" y="{(y1+y2)/2:.1f}" text-anchor="end" '
                     f'font-family="sans-serif" font-size="11" fill="#666" '
                     f'transform="rotate(-90,{dim_x-5},{(y1+y2)/2:.1f})">{data_h:.2f}m</text>')

    lines.append('</svg>')

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"SVG 匯出: {output_path}")
    return output_path


def _default_layer_name(result: SectionResult) -> str:
    type_names = {
        SectionType.PLAN: "平面圖",
        SectionType.ELEVATION_X: "X立面圖",
        SectionType.ELEVATION_Y: "Y立面圖",
        SectionType.CROSS: "剖面圖",
    }
    name = type_names.get(result.section_type, "切面")
    return f"{name}_Z{result.position:.1f}" if result.section_type == SectionType.PLAN else f"{name}_{result.position:.1f}"


def _section_label(result: SectionResult) -> str:
    labels = {
        SectionType.PLAN: f"平面圖 (Z={result.position:.2f}m)",
        SectionType.ELEVATION_X: f"X方向立面圖 (X={result.position:.2f}m)",
        SectionType.ELEVATION_Y: f"Y方向立面圖 (Y={result.position:.2f}m)",
        SectionType.CROSS: f"剖面圖 (angle={result.position:.1f}°)",
    }
    return labels.get(result.section_type, "切面圖")
