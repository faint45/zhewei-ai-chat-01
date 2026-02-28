"""
築未科技 — 點雲切面提取器
從點雲中提取指定平面/立面的截面，生成 2D 輪廓線。

支援：
  - 平面圖（水平切面，指定高度 Z）
  - 立面圖（垂直切面，指定方向 X/Y 或任意角度）
  - 剖面圖（任意平面切面）
"""
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class SectionType(Enum):
    PLAN = "plan"           # 平面圖（水平切）
    ELEVATION_X = "elev_x"  # 立面圖（X 方向切，看 YZ 面）
    ELEVATION_Y = "elev_y"  # 立面圖（Y 方向切，看 XZ 面）
    CROSS = "cross"         # 剖面圖（任意角度）


@dataclass
class SectionParams:
    """切面參數"""
    section_type: SectionType = SectionType.PLAN
    position: float = 0.0          # 切面位置 (平面圖=Z高度, 立面=X或Y座標)
    thickness: float = 0.1         # 切片厚度 (公尺)，越薄越精確但點越少
    angle: float = 0.0             # 剖面角度 (僅 CROSS 類型，度)
    denoise_radius: float = 0.05   # 降噪半徑
    denoise_neighbors: int = 10    # 降噪鄰居數
    simplify_tolerance: float = 0.01  # 輪廓簡化容差 (公尺)


@dataclass
class SectionResult:
    """切面結果"""
    section_type: SectionType
    position: float
    points_2d: np.ndarray        # 切面上的 2D 點 (N, 2)
    contours: list = field(default_factory=list)  # 輪廓線列表，每條 [(x,y), ...]
    bounds: dict = field(default_factory=dict)     # 邊界 {min_x, max_x, min_y, max_y}
    n_points: int = 0
    unit: str = "m"


def extract_section(pcd, params: SectionParams) -> SectionResult:
    """
    從點雲提取切面。

    Args:
        pcd: PointCloud (from loader)
        params: SectionParams 切面參數
    Returns:
        SectionResult
    """
    points = pcd.points
    logger.info(f"提取切面: type={params.section_type.value}, pos={params.position}, thickness={params.thickness}")

    # 根據切面類型提取點
    if params.section_type == SectionType.PLAN:
        # 平面圖：取 Z 在 [position - thickness/2, position + thickness/2] 的點
        mask = np.abs(points[:, 2] - params.position) <= params.thickness / 2
        slice_points = points[mask]
        # 投影到 XY 平面
        points_2d = slice_points[:, :2]  # (X, Y)

    elif params.section_type == SectionType.ELEVATION_X:
        # X 方向立面：取 X 在範圍的點，投影到 YZ
        mask = np.abs(points[:, 0] - params.position) <= params.thickness / 2
        slice_points = points[mask]
        points_2d = slice_points[:, 1:3]  # (Y, Z)

    elif params.section_type == SectionType.ELEVATION_Y:
        # Y 方向立面：取 Y 在範圍的點，投影到 XZ
        mask = np.abs(points[:, 1] - params.position) <= params.thickness / 2
        slice_points = points[mask]
        points_2d = np.column_stack([slice_points[:, 0], slice_points[:, 2]])  # (X, Z)

    elif params.section_type == SectionType.CROSS:
        # 任意角度剖面
        angle_rad = np.radians(params.angle)
        normal = np.array([np.cos(angle_rad), np.sin(angle_rad), 0.0])
        distances = np.dot(points[:, :2], normal[:2])
        mask = np.abs(distances - params.position) <= params.thickness / 2
        slice_points = points[mask]
        # 投影到剖面座標系
        tangent = np.array([-np.sin(angle_rad), np.cos(angle_rad)])
        proj_h = np.dot(slice_points[:, :2], tangent)
        proj_v = slice_points[:, 2]
        points_2d = np.column_stack([proj_h, proj_v])

    else:
        raise ValueError(f"未知的切面類型: {params.section_type}")

    if len(points_2d) == 0:
        logger.warning("切面內無點，請調整位置或厚度")
        return SectionResult(
            section_type=params.section_type,
            position=params.position,
            points_2d=np.empty((0, 2)),
            n_points=0
        )

    logger.info(f"切面點數: {len(points_2d):,}")

    # 降噪
    points_2d = _denoise_2d(points_2d, params.denoise_radius, params.denoise_neighbors)
    logger.info(f"降噪後: {len(points_2d):,}")

    # 提取輪廓線
    contours = _extract_contours(points_2d, params.simplify_tolerance)
    logger.info(f"輪廓線數: {len(contours)}")

    # 計算邊界
    bounds = {
        "min_x": float(points_2d[:, 0].min()),
        "max_x": float(points_2d[:, 0].max()),
        "min_y": float(points_2d[:, 1].min()),
        "max_y": float(points_2d[:, 1].max()),
    }

    return SectionResult(
        section_type=params.section_type,
        position=params.position,
        points_2d=points_2d,
        contours=contours,
        bounds=bounds,
        n_points=len(points_2d),
    )


def auto_sections(pcd, n_plans: int = 3, n_elevations: int = 4, thickness: float = 0.1) -> list[SectionResult]:
    """
    自動生成多個切面（平面圖+立面圖）。

    Args:
        pcd: 點雲
        n_plans: 平面圖數量（均勻分佈在高度範圍）
        n_elevations: 立面圖數量（2個X方向 + 2個Y方向）
        thickness: 切片厚度
    Returns:
        SectionResult 列表
    """
    points = pcd.points
    z_min, z_max = points[:, 2].min(), points[:, 2].max()
    x_min, x_max = points[:, 0].min(), points[:, 0].max()
    y_min, y_max = points[:, 1].min(), points[:, 1].max()

    results = []

    # 平面圖：均勻高度
    z_positions = np.linspace(z_min + (z_max - z_min) * 0.1, z_max - (z_max - z_min) * 0.1, n_plans)
    for z in z_positions:
        params = SectionParams(section_type=SectionType.PLAN, position=float(z), thickness=thickness)
        results.append(extract_section(pcd, params))

    # 立面圖
    n_x = n_elevations // 2
    n_y = n_elevations - n_x

    x_positions = np.linspace(x_min + (x_max - x_min) * 0.3, x_max - (x_max - x_min) * 0.3, n_x)
    for x in x_positions:
        params = SectionParams(section_type=SectionType.ELEVATION_X, position=float(x), thickness=thickness)
        results.append(extract_section(pcd, params))

    y_positions = np.linspace(y_min + (y_max - y_min) * 0.3, y_max - (y_max - y_min) * 0.3, n_y)
    for y in y_positions:
        params = SectionParams(section_type=SectionType.ELEVATION_Y, position=float(y), thickness=thickness)
        results.append(extract_section(pcd, params))

    logger.info(f"自動生成 {len(results)} 個切面 ({n_plans} 平面 + {n_x} X立面 + {n_y} Y立面)")
    return results


def _denoise_2d(points: np.ndarray, radius: float, min_neighbors: int) -> np.ndarray:
    """2D 統計降噪：移除孤立點"""
    if len(points) < min_neighbors + 1:
        return points

    from scipy.spatial import cKDTree
    tree = cKDTree(points)
    counts = tree.query_ball_point(points, r=radius, return_length=True)
    mask = counts >= min_neighbors
    return points[mask]


def _extract_contours(points: np.ndarray, tolerance: float) -> list[list[tuple]]:
    """
    從 2D 點集提取輪廓線。
    使用 Alpha Shape / Concave Hull 方法。
    """
    if len(points) < 3:
        return []

    try:
        from scipy.spatial import Delaunay
        from collections import defaultdict

        # Delaunay 三角化
        tri = Delaunay(points)

        # 提取邊界邊（只屬於一個三角形的邊）
        edge_count = defaultdict(int)
        for simplex in tri.simplices:
            for i in range(3):
                edge = tuple(sorted([simplex[i], simplex[(i + 1) % 3]]))
                edge_count[edge] += 1

        # Alpha shape：根據邊長過濾
        mean_dist = np.mean(np.linalg.norm(np.diff(np.sort(points, axis=0)[:100], axis=0), axis=1))
        alpha_threshold = mean_dist * 5

        boundary_edges = []
        for edge, count in edge_count.items():
            p1, p2 = points[edge[0]], points[edge[1]]
            edge_len = np.linalg.norm(p2 - p1)
            if count == 1 or edge_len > alpha_threshold:
                if edge_len <= alpha_threshold * 2:
                    boundary_edges.append(edge)

        if not boundary_edges:
            # fallback: convex hull
            from scipy.spatial import ConvexHull
            hull = ConvexHull(points)
            contour = [(float(points[i, 0]), float(points[i, 1])) for i in hull.vertices]
            contour.append(contour[0])  # 閉合
            return [contour]

        # 串連邊界邊為輪廓線
        contours = _chain_edges(boundary_edges, points)

        # 簡化輪廓
        simplified = []
        for contour in contours:
            if len(contour) >= 3:
                simplified_contour = _douglas_peucker(contour, tolerance)
                if len(simplified_contour) >= 3:
                    simplified.append(simplified_contour)

        return simplified

    except Exception as e:
        logger.warning(f"輪廓提取失敗: {e}，使用 ConvexHull 替代")
        try:
            from scipy.spatial import ConvexHull
            hull = ConvexHull(points)
            contour = [(float(points[i, 0]), float(points[i, 1])) for i in hull.vertices]
            contour.append(contour[0])
            return [contour]
        except Exception:
            return []


def _chain_edges(edges: list, points: np.ndarray) -> list[list[tuple]]:
    """將離散的邊串連成連續的輪廓線"""
    from collections import defaultdict

    adj = defaultdict(set)
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)

    visited = set()
    contours = []

    for start in adj:
        if start in visited:
            continue

        chain = []
        current = start
        prev = None

        while current is not None and current not in visited:
            visited.add(current)
            chain.append((float(points[current, 0]), float(points[current, 1])))

            neighbors = adj[current] - {prev}
            unvisited = neighbors - visited
            prev = current
            current = next(iter(unvisited), None)

        if len(chain) >= 3:
            chain.append(chain[0])  # 閉合
            contours.append(chain)

    return contours


def _douglas_peucker(points: list[tuple], tolerance: float) -> list[tuple]:
    """Douglas-Peucker 線段簡化演算法"""
    if len(points) <= 2:
        return points

    # 找最遠點
    start = np.array(points[0])
    end = np.array(points[-1])
    line_vec = end - start
    line_len = np.linalg.norm(line_vec)

    if line_len == 0:
        return [points[0], points[-1]]

    line_unit = line_vec / line_len
    max_dist = 0
    max_idx = 0

    for i in range(1, len(points) - 1):
        p = np.array(points[i])
        proj = np.dot(p - start, line_unit)
        proj = np.clip(proj, 0, line_len)
        closest = start + proj * line_unit
        dist = np.linalg.norm(p - closest)
        if dist > max_dist:
            max_dist = dist
            max_idx = i

    if max_dist > tolerance:
        left = _douglas_peucker(points[:max_idx + 1], tolerance)
        right = _douglas_peucker(points[max_idx:], tolerance)
        return left[:-1] + right
    else:
        return [points[0], points[-1]]
