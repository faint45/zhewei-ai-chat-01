"""
築未科技 — 點雲統一載入器
支援格式：LAS, LAZ, PLY, XYZ, PTS
來源：RS10 光達、無人機航拍、手持掃描儀（iPhone LiDAR 等）

不依賴 Open3D（相容 Python 3.12+），使用純 numpy + laspy。
"""
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = {".las", ".laz", ".ply", ".xyz", ".pts"}


@dataclass
class PointCloud:
    """輕量點雲容器（取代 Open3D PointCloud）"""
    points: np.ndarray                      # (N, 3) float64
    colors: Optional[np.ndarray] = None     # (N, 3) float64, 0~1

    def __len__(self):
        return len(self.points)

    def voxel_down_sample(self, voxel_size: float) -> "PointCloud":
        """體素下採樣"""
        if voxel_size <= 0:
            return self
        quantized = np.floor(self.points / voxel_size).astype(np.int64)
        _, idx = np.unique(quantized, axis=0, return_index=True)
        idx.sort()
        new_colors = self.colors[idx] if self.colors is not None else None
        return PointCloud(points=self.points[idx], colors=new_colors)


def load_pointcloud(filepath: str, voxel_size: Optional[float] = None) -> PointCloud:
    """
    統一載入點雲。

    Args:
        filepath: 點雲檔案路徑
        voxel_size: 若指定則自動體素下採樣 (單位：公尺)
    Returns:
        PointCloud
    """
    path = Path(filepath)
    ext = path.suffix.lower()

    if ext not in SUPPORTED_FORMATS:
        raise ValueError(f"不支援的格式: {ext}，支援: {SUPPORTED_FORMATS}")

    logger.info(f"載入點雲: {path.name} ({ext})")

    if ext in (".las", ".laz"):
        pcd = _load_las(filepath)
    elif ext == ".ply":
        pcd = _load_ply(filepath)
    elif ext == ".xyz":
        pcd = _load_xyz(filepath)
    elif ext == ".pts":
        pcd = _load_pts(filepath)
    else:
        raise ValueError(f"不支援的格式: {ext}")

    logger.info(f"載入完成: {len(pcd):,} 點")

    if voxel_size and voxel_size > 0:
        pcd = pcd.voxel_down_sample(voxel_size)
        logger.info(f"下採樣 (voxel={voxel_size}m): {len(pcd):,} 點")

    return pcd


def _load_las(filepath: str) -> PointCloud:
    """LAS/LAZ → PointCloud"""
    import laspy

    las = laspy.read(filepath)
    points = np.vstack([las.x, las.y, las.z]).T.astype(np.float64)

    colors = None
    if hasattr(las, "red") and hasattr(las, "green") and hasattr(las, "blue"):
        colors = np.vstack([las.red, las.green, las.blue]).T.astype(np.float64)
        max_val = colors.max()
        if max_val > 255:
            colors /= 65535.0
        elif max_val > 0:
            colors /= 255.0

    return PointCloud(points=points, colors=colors)


def _load_ply(filepath: str) -> PointCloud:
    """PLY (ASCII) → PointCloud"""
    path = Path(filepath)
    with open(path, "rb") as f:
        header_lines = []
        while True:
            line = f.readline().decode("ascii", errors="ignore").strip()
            header_lines.append(line)
            if line == "end_header":
                break

        # 解析 header
        n_vertices = 0
        props = []
        in_vertex = False
        for line in header_lines:
            if line.startswith("element vertex"):
                n_vertices = int(line.split()[-1])
                in_vertex = True
            elif line.startswith("element"):
                in_vertex = False
            elif in_vertex and line.startswith("property"):
                parts = line.split()
                props.append(parts[-1])  # 屬性名

        # 讀取數據
        is_binary = any("binary" in h for h in header_lines)
        if is_binary:
            # 簡化：只讀 float32 x,y,z
            dtype = np.dtype([(p, np.float32) for p in props[:3]])
            data = np.fromfile(f, dtype=dtype, count=n_vertices)
            points = np.column_stack([data[p] for p in props[:3]]).astype(np.float64)
        else:
            rows = []
            for _ in range(n_vertices):
                line = f.readline().decode("ascii", errors="ignore").strip()
                if line:
                    rows.append([float(x) for x in line.split()])
            data = np.array(rows)
            points = data[:, :3].astype(np.float64)

    colors = None
    prop_names = [p.lower() for p in props]
    if "red" in prop_names and "green" in prop_names and "blue" in prop_names:
        ri = prop_names.index("red")
        gi = prop_names.index("green")
        bi = prop_names.index("blue")
        if not is_binary and data.shape[1] > max(ri, gi, bi):
            colors = data[:, [ri, gi, bi]].astype(np.float64)
            if colors.max() > 1.0:
                colors /= 255.0

    return PointCloud(points=points, colors=colors)


def _load_xyz(filepath: str) -> PointCloud:
    """XYZ 純文字 → PointCloud"""
    data = np.loadtxt(filepath, comments="#", delimiter=None)
    points = data[:, :3].astype(np.float64)

    colors = None
    if data.shape[1] >= 6:
        colors = data[:, 3:6].astype(np.float64)
        if colors.max() > 1.0:
            colors /= 255.0

    return PointCloud(points=points, colors=colors)


def _load_pts(filepath: str) -> PointCloud:
    """PTS 格式 → PointCloud"""
    lines = Path(filepath).read_text().strip().split("\n")
    start = 0
    try:
        int(lines[0].strip())
        start = 1
    except ValueError:
        pass

    rows = []
    for line in lines[start:]:
        parts = line.strip().split()
        if len(parts) >= 3:
            rows.append([float(x) for x in parts[:3]])

    return PointCloud(points=np.array(rows, dtype=np.float64))


def scan_directory(root_dir: str, recursive: bool = True) -> list[dict]:
    """掃描目錄，列出所有支援的點雲檔案"""
    root = Path(root_dir)
    results = []
    pattern = "**/*" if recursive else "*"

    for f in root.glob(pattern):
        if f.suffix.lower() in SUPPORTED_FORMATS:
            results.append({
                "path": str(f),
                "name": f.name,
                "format": f.suffix.lower(),
                "size_mb": round(f.stat().st_size / (1024 * 1024), 1),
            })

    results.sort(key=lambda x: x["name"])
    logger.info(f"掃描 {root_dir}: 找到 {len(results)} 個點雲檔案")
    return results
