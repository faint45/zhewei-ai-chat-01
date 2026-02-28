"""
築未科技 — 精準尺寸標註模組
生成工程圖標準的尺寸標註（DXF DIMENSION 實體 + 座標網格）。

功能：
  - 自動偵測關鍵特徵尺寸（寬、高、偏移）
  - DXF 線性標註 (DIMENSION)
  - 座標網格線 + 標籤
  - 距離/角度/面積量測
"""
import logging
import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class DimensionLine:
    """一條尺寸標註線"""
    start: tuple[float, float]      # 起點 (x, y)
    end: tuple[float, float]        # 終點 (x, y)
    offset: float = 1.0             # 標註線偏移距離
    text: str = ""                  # 標註文字（空=自動計算）
    direction: str = "horizontal"   # horizontal / vertical / aligned
    precision: int = 3              # 小數位數


@dataclass
class MeasureResult:
    """量測結果"""
    distance: float = 0.0
    angle: float = 0.0         # 度
    area: float = 0.0          # 平方公尺
    perimeter: float = 0.0
    details: dict = field(default_factory=dict)


def auto_dimensions(bounds: dict, contours: list, section_type: str = "plan") -> list[DimensionLine]:
    """
    根據切面邊界和輪廓自動生成尺寸標註。

    Returns:
        DimensionLine 列表
    """
    dims = []
    if not bounds:
        return dims

    min_x = bounds["min_x"]
    max_x = bounds["max_x"]
    min_y = bounds["min_y"]
    max_y = bounds["max_y"]
    w = max_x - min_x
    h = max_y - min_y

    # 總寬度標註（底部）
    dims.append(DimensionLine(
        start=(min_x, min_y),
        end=(max_x, min_y),
        offset=-max(h * 0.08, 0.5),
        direction="horizontal",
    ))

    # 總高度標註（左側）
    dims.append(DimensionLine(
        start=(min_x, min_y),
        end=(min_x, max_y),
        offset=-max(w * 0.08, 0.5),
        direction="vertical",
    ))

    # 如果有輪廓，標註主要輪廓的關鍵段
    for contour in contours[:3]:
        if len(contour) < 4:
            continue
        # 找最長的水平段和垂直段
        best_h = None
        best_v = None
        best_h_len = 0
        best_v_len = 0

        for i in range(len(contour) - 1):
            x1, y1 = contour[i]
            x2, y2 = contour[i + 1]
            dx = abs(x2 - x1)
            dy = abs(y2 - y1)
            seg_len = math.sqrt(dx ** 2 + dy ** 2)

            if dy < dx * 0.3 and seg_len > best_h_len:
                best_h = (contour[i], contour[i + 1])
                best_h_len = seg_len
            if dx < dy * 0.3 and seg_len > best_v_len:
                best_v = (contour[i], contour[i + 1])
                best_v_len = seg_len

        if best_h and best_h_len > w * 0.1:
            dims.append(DimensionLine(
                start=best_h[0], end=best_h[1],
                offset=max(h * 0.05, 0.3),
                direction="horizontal",
            ))
        if best_v and best_v_len > h * 0.1:
            dims.append(DimensionLine(
                start=best_v[0], end=best_v[1],
                offset=max(w * 0.05, 0.3),
                direction="vertical",
            ))

    return dims


def add_dimensions_to_dxf(msp, dims: list[DimensionLine], scale: float = 1.0,
                          layer: str = "標註", color: int = 1):
    """
    將尺寸標註加入 DXF modelspace。

    Args:
        msp: ezdxf modelspace
        dims: DimensionLine 列表
        scale: 縮放比例
        layer: 圖層名
        color: 顏色 (AutoCAD color index, 1=紅)
    """
    for dim in dims:
        x1, y1 = dim.start[0] * scale, dim.start[1] * scale
        x2, y2 = dim.end[0] * scale, dim.end[1] * scale

        if dim.direction == "horizontal":
            length = abs(x2 - x1)
            text = dim.text or f"{length:.{dim.precision}f}"
            dim_y = min(y1, y2) + dim.offset * scale
            # 標註線
            msp.add_line((x1, dim_y), (x2, dim_y),
                         dxfattribs={"layer": layer, "color": color})
            # 延伸線
            msp.add_line((x1, y1), (x1, dim_y),
                         dxfattribs={"layer": layer, "color": color})
            msp.add_line((x2, y2), (x2, dim_y),
                         dxfattribs={"layer": layer, "color": color})
            # 箭頭（簡化為短線）
            arrow_size = max(length * 0.02, 0.1) * scale
            msp.add_line((x1, dim_y), (x1 + arrow_size, dim_y + arrow_size * 0.5),
                         dxfattribs={"layer": layer, "color": color})
            msp.add_line((x1, dim_y), (x1 + arrow_size, dim_y - arrow_size * 0.5),
                         dxfattribs={"layer": layer, "color": color})
            msp.add_line((x2, dim_y), (x2 - arrow_size, dim_y + arrow_size * 0.5),
                         dxfattribs={"layer": layer, "color": color})
            msp.add_line((x2, dim_y), (x2 - arrow_size, dim_y - arrow_size * 0.5),
                         dxfattribs={"layer": layer, "color": color})
            # 文字
            text_height = max(length * 0.03, 0.15) * scale
            msp.add_text(text, dxfattribs={
                "layer": layer, "color": color,
                "height": text_height,
                "insert": ((x1 + x2) / 2, dim_y - text_height * 1.5),
                "halign": 1,
            })

        elif dim.direction == "vertical":
            length = abs(y2 - y1)
            text = dim.text or f"{length:.{dim.precision}f}"
            dim_x = min(x1, x2) + dim.offset * scale
            msp.add_line((dim_x, y1), (dim_x, y2),
                         dxfattribs={"layer": layer, "color": color})
            msp.add_line((x1, y1), (dim_x, y1),
                         dxfattribs={"layer": layer, "color": color})
            msp.add_line((x2, y2), (dim_x, y2),
                         dxfattribs={"layer": layer, "color": color})
            arrow_size = max(length * 0.02, 0.1) * scale
            msp.add_line((dim_x, y1), (dim_x + arrow_size * 0.5, y1 + arrow_size),
                         dxfattribs={"layer": layer, "color": color})
            msp.add_line((dim_x, y1), (dim_x - arrow_size * 0.5, y1 + arrow_size),
                         dxfattribs={"layer": layer, "color": color})
            msp.add_line((dim_x, y2), (dim_x + arrow_size * 0.5, y2 - arrow_size),
                         dxfattribs={"layer": layer, "color": color})
            msp.add_line((dim_x, y2), (dim_x - arrow_size * 0.5, y2 - arrow_size),
                         dxfattribs={"layer": layer, "color": color})
            text_height = max(length * 0.03, 0.15) * scale
            msp.add_text(text, dxfattribs={
                "layer": layer, "color": color,
                "height": text_height,
                "insert": (dim_x - text_height * 1.5, (y1 + y2) / 2),
                "rotation": 90,
            })

        else:  # aligned
            length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            text = dim.text or f"{length:.{dim.precision}f}"
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            text_height = max(length * 0.03, 0.15) * scale
            angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
            msp.add_line((x1, y1), (x2, y2),
                         dxfattribs={"layer": layer, "color": color, "linetype": "DASHED"})
            msp.add_text(text, dxfattribs={
                "layer": layer, "color": color,
                "height": text_height,
                "insert": (mx, my + text_height),
                "rotation": angle,
            })


def add_grid_to_dxf(msp, bounds: dict, spacing: float = 1.0, scale: float = 1.0,
                    layer: str = "網格", color: int = 8):
    """
    在 DXF 上繪製座標網格線。

    Args:
        bounds: 邊界 dict
        spacing: 網格間距 (公尺)
        scale: 縮放
        layer: 圖層名
        color: 顏色 (8=灰)
    """
    min_x = bounds["min_x"] * scale
    max_x = bounds["max_x"] * scale
    min_y = bounds["min_y"] * scale
    max_y = bounds["max_y"] * scale

    # 自動計算合適的網格間距
    w = max_x - min_x
    h = max_y - min_y
    if spacing <= 0:
        spacing = _auto_grid_spacing(max(w, h))
    spacing_s = spacing * scale

    # 垂直格線
    x = math.floor(min_x / spacing_s) * spacing_s
    while x <= max_x:
        msp.add_line((x, min_y - spacing_s * 0.3), (x, max_y + spacing_s * 0.3),
                     dxfattribs={"layer": layer, "color": color, "linetype": "DOT"})
        # 座標標籤
        coord_val = x / scale if scale != 0 else x
        msp.add_text(f"{coord_val:.1f}", dxfattribs={
            "layer": layer, "color": color,
            "height": spacing_s * 0.15,
            "insert": (x, min_y - spacing_s * 0.5),
            "halign": 1,
        })
        x += spacing_s

    # 水平格線
    y = math.floor(min_y / spacing_s) * spacing_s
    while y <= max_y:
        msp.add_line((min_x - spacing_s * 0.3, y), (max_x + spacing_s * 0.3, y),
                     dxfattribs={"layer": layer, "color": color, "linetype": "DOT"})
        coord_val = y / scale if scale != 0 else y
        msp.add_text(f"{coord_val:.1f}", dxfattribs={
            "layer": layer, "color": color,
            "height": spacing_s * 0.15,
            "insert": (min_x - spacing_s * 0.6, y),
        })
        y += spacing_s


def measure_distance(p1: tuple, p2: tuple) -> float:
    """兩點距離"""
    return math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)


def measure_contour(contour: list[tuple]) -> MeasureResult:
    """量測輪廓的面積和周長"""
    if len(contour) < 3:
        return MeasureResult()

    # 周長
    perimeter = 0.0
    for i in range(len(contour) - 1):
        perimeter += measure_distance(contour[i], contour[i + 1])

    # 面積 (Shoelace formula)
    area = 0.0
    n = len(contour)
    for i in range(n - 1):
        x1, y1 = contour[i]
        x2, y2 = contour[i + 1]
        area += x1 * y2 - x2 * y1
    area = abs(area) / 2.0

    return MeasureResult(
        distance=0.0,
        area=area,
        perimeter=perimeter,
        details={"n_vertices": len(contour)},
    )


def _auto_grid_spacing(extent: float) -> float:
    """根據範圍自動選擇網格間距"""
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
