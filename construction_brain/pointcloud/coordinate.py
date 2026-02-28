"""
築未科技 — 三維坐標套匯模組
支援 TWD97 ↔ WGS84 轉換、控制點匹配、座標系偏移校正。

營建工程常見需求：
  - RS10 光達掃描資料（本地座標）套匯到 TWD97
  - 無人機航拍（WGS84）轉換到 TWD97
  - 多次掃描的點雲對齊（ICP-like 控制點匹配）
"""
import logging
import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


# ── TWD97 參數 ──────────────────────────────────────────
# TWD97 採用 TM2 投影，中央經線 121°E
TWD97_A = 6378137.0           # GRS80 長半軸
TWD97_F = 1 / 298.257222101   # 扁率
TWD97_LON0 = 121.0            # 中央經線
TWD97_K0 = 0.9999             # 尺度因子
TWD97_DX = 250000.0           # 東偏
TWD97_DY = 0.0                # 北偏


@dataclass
class ControlPoint:
    """控制點（已知座標）"""
    name: str
    local_xyz: np.ndarray    # 本地座標 (3,)
    target_xyz: np.ndarray   # 目標座標 (3,)  TWD97 E/N/H 或 WGS84 lon/lat/h


@dataclass
class TransformResult:
    """座標轉換結果"""
    points: np.ndarray           # 轉換後的點 (N, 3)
    translation: np.ndarray      # 平移量 (3,)
    rotation: np.ndarray         # 旋轉矩陣 (3, 3)
    scale: float                 # 尺度因子
    rmse: float                  # 殘差 RMSE (公尺)
    n_control_points: int
    method: str


def wgs84_to_twd97(lon: float, lat: float, h: float = 0.0) -> tuple[float, float, float]:
    """
    WGS84 經緯度 → TWD97 TM2 座標 (E, N, H)。

    Args:
        lon: 經度 (度)
        lat: 緯度 (度)
        h: 橢球高 (公尺)
    Returns:
        (E, N, H) TWD97 座標
    """
    a = TWD97_A
    f = TWD97_F
    lon0 = math.radians(TWD97_LON0)
    k0 = TWD97_K0

    lat_r = math.radians(lat)
    lon_r = math.radians(lon)

    e2 = 2 * f - f ** 2
    e_prime2 = e2 / (1 - e2)

    N = a / math.sqrt(1 - e2 * math.sin(lat_r) ** 2)
    T = math.tan(lat_r) ** 2
    C = e_prime2 * math.cos(lat_r) ** 2
    A_coeff = (lon_r - lon0) * math.cos(lat_r)

    # 子午線弧長
    M = a * (
        (1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256) * lat_r
        - (3 * e2 / 8 + 3 * e2 ** 2 / 32 + 45 * e2 ** 3 / 1024) * math.sin(2 * lat_r)
        + (15 * e2 ** 2 / 256 + 45 * e2 ** 3 / 1024) * math.sin(4 * lat_r)
        - (35 * e2 ** 3 / 3072) * math.sin(6 * lat_r)
    )

    easting = TWD97_DX + k0 * N * (
        A_coeff
        + (1 - T + C) * A_coeff ** 3 / 6
        + (5 - 18 * T + T ** 2 + 72 * C - 58 * e_prime2) * A_coeff ** 5 / 120
    )

    northing = TWD97_DY + k0 * (
        M + N * math.tan(lat_r) * (
            A_coeff ** 2 / 2
            + (5 - T + 9 * C + 4 * C ** 2) * A_coeff ** 4 / 24
            + (61 - 58 * T + T ** 2 + 600 * C - 330 * e_prime2) * A_coeff ** 6 / 720
        )
    )

    return (easting, northing, h)


def twd97_to_wgs84(e: float, n: float, h: float = 0.0) -> tuple[float, float, float]:
    """
    TWD97 TM2 → WGS84 經緯度。

    Args:
        e: 東距 (E)
        n: 北距 (N)
        h: 橢球高
    Returns:
        (lon, lat, h) 度
    """
    a = TWD97_A
    f = TWD97_F
    k0 = TWD97_K0
    lon0 = math.radians(TWD97_LON0)

    e2 = 2 * f - f ** 2
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))

    M = (n - TWD97_DY) / k0
    mu = M / (a * (1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256))

    lat1 = (
        mu
        + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * math.sin(2 * mu)
        + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * math.sin(4 * mu)
        + (151 * e1 ** 3 / 96) * math.sin(6 * mu)
    )

    e_prime2 = e2 / (1 - e2)
    N1 = a / math.sqrt(1 - e2 * math.sin(lat1) ** 2)
    T1 = math.tan(lat1) ** 2
    C1 = e_prime2 * math.cos(lat1) ** 2
    R1 = a * (1 - e2) / (1 - e2 * math.sin(lat1) ** 2) ** 1.5
    D = (e - TWD97_DX) / (N1 * k0)

    lat = lat1 - (N1 * math.tan(lat1) / R1) * (
        D ** 2 / 2
        - (5 + 3 * T1 + 10 * C1 - 4 * C1 ** 2 - 9 * e_prime2) * D ** 4 / 24
        + (61 + 90 * T1 + 298 * C1 + 45 * T1 ** 2 - 252 * e_prime2 - 3 * C1 ** 2) * D ** 6 / 720
    )

    lon = lon0 + (
        D
        - (1 + 2 * T1 + C1) * D ** 3 / 6
        + (5 - 2 * C1 + 28 * T1 - 3 * C1 ** 2 + 8 * e_prime2 + 24 * T1 ** 2) * D ** 5 / 120
    ) / math.cos(lat1)

    return (math.degrees(lon), math.degrees(lat), h)


def transform_by_control_points(
    points: np.ndarray,
    control_points: list[ControlPoint],
    allow_scale: bool = False,
) -> TransformResult:
    """
    使用控制點進行剛體轉換（Helmert / 7 參數轉換）。

    最少需要 3 個控制點（無尺度）或 4 個（含尺度）。
    使用 SVD 求解最佳旋轉 + 平移。

    Args:
        points: 原始點 (N, 3)
        control_points: 控制點列表
        allow_scale: 是否允許尺度變換
    Returns:
        TransformResult
    """
    n_cp = len(control_points)
    if n_cp < 3:
        raise ValueError(f"至少需要 3 個控制點，目前只有 {n_cp} 個")

    src = np.array([cp.local_xyz for cp in control_points])
    dst = np.array([cp.target_xyz for cp in control_points])

    # 質心
    src_mean = src.mean(axis=0)
    dst_mean = dst.mean(axis=0)

    src_c = src - src_mean
    dst_c = dst - dst_mean

    # SVD
    H = src_c.T @ dst_c
    U, S, Vt = np.linalg.svd(H)
    d = np.linalg.det(Vt.T @ U.T)
    sign_matrix = np.diag([1, 1, np.sign(d)])
    R = Vt.T @ sign_matrix @ U.T

    # 尺度
    if allow_scale and n_cp >= 4:
        scale = np.sum(S) / np.sum(src_c ** 2)
    else:
        scale = 1.0

    # 平移
    t = dst_mean - scale * (R @ src_mean)

    # 轉換所有點
    transformed = scale * (points @ R.T) + t

    # RMSE
    residuals = dst - (scale * (src @ R.T) + t)
    rmse = float(np.sqrt(np.mean(residuals ** 2)))

    logger.info(f"座標轉換完成: {n_cp} 控制點, RMSE={rmse:.4f}m, scale={scale:.6f}")

    return TransformResult(
        points=transformed,
        translation=t,
        rotation=R,
        scale=scale,
        rmse=rmse,
        n_control_points=n_cp,
        method="SVD_rigid" if not allow_scale else "SVD_similarity",
    )


def apply_offset(points: np.ndarray, dx: float = 0, dy: float = 0, dz: float = 0) -> np.ndarray:
    """簡單平移偏移"""
    offset = np.array([dx, dy, dz], dtype=np.float64)
    return points + offset


def batch_wgs84_to_twd97(coords: np.ndarray) -> np.ndarray:
    """
    批次 WGS84 → TWD97。

    Args:
        coords: (N, 3) 陣列，每行 [lon, lat, h]
    Returns:
        (N, 3) 陣列，每行 [E, N, H]
    """
    result = np.zeros_like(coords)
    for i in range(len(coords)):
        e, n, h = wgs84_to_twd97(coords[i, 0], coords[i, 1], coords[i, 2])
        result[i] = [e, n, h]
    return result


def batch_twd97_to_wgs84(coords: np.ndarray) -> np.ndarray:
    """批次 TWD97 → WGS84。"""
    result = np.zeros_like(coords)
    for i in range(len(coords)):
        lon, lat, h = twd97_to_wgs84(coords[i, 0], coords[i, 1], coords[i, 2])
        result[i] = [lon, lat, h]
    return result
