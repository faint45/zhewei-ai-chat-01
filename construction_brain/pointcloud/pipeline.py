"""
築未科技 — 點雲→平立面圖 一鍵處理管線

用法：
    from construction_brain.pointcloud.pipeline import PointCloudPipeline

    pipe = PointCloudPipeline("scan.las")
    results = pipe.auto_generate(output_dir="output/")
    # → 自動生成 3 張平面圖 + 4 張立面圖 (DXF + SVG)

    # 或指定切面：
    pipe.plan_view(z=1.2, output="floor_plan.dxf")
    pipe.elevation_view(direction="x", position=5.0, output="east_elevation.dxf")
"""
import logging
from pathlib import Path
from typing import Optional

from .loader import load_pointcloud, scan_directory
from .section_extractor import (
    SectionParams, SectionType, SectionResult,
    extract_section, auto_sections,
)
from .exporter import export_dxf, export_svg

logger = logging.getLogger(__name__)


class PointCloudPipeline:
    """點雲→平立面圖自動處理管線"""

    def __init__(self, filepath: str, voxel_size: float = 0.02):
        """
        Args:
            filepath: 點雲檔案路徑
            voxel_size: 體素下採樣大小 (公尺)，0 = 不下採樣
        """
        self.filepath = filepath
        self.pcd = load_pointcloud(filepath, voxel_size=voxel_size if voxel_size > 0 else None)
        self._info = self._get_info()
        logger.info(f"管線初始化: {self._info}")

    @property
    def info(self) -> dict:
        return self._info

    def _get_info(self) -> dict:
        points = self.pcd.points
        return {
            "file": Path(self.filepath).name,
            "n_points": len(points),
            "x_range": [float(points[:, 0].min()), float(points[:, 0].max())],
            "y_range": [float(points[:, 1].min()), float(points[:, 1].max())],
            "z_range": [float(points[:, 2].min()), float(points[:, 2].max())],
            "width": float(points[:, 0].max() - points[:, 0].min()),
            "depth": float(points[:, 1].max() - points[:, 1].min()),
            "height": float(points[:, 2].max() - points[:, 2].min()),
        }

    def plan_view(self, z: float, thickness: float = 0.1, output: Optional[str] = None,
                  format: str = "dxf") -> SectionResult:
        """
        生成平面圖（水平切面）。

        Args:
            z: 切面高度 (公尺)
            thickness: 切片厚度
            output: 輸出檔案路徑（不指定則不存檔）
            format: "dxf" 或 "svg"
        """
        params = SectionParams(section_type=SectionType.PLAN, position=z, thickness=thickness)
        result = extract_section(self.pcd, params)

        if output:
            if format == "svg":
                export_svg(result, output)
            else:
                export_dxf(result, output)

        return result

    def elevation_view(self, direction: str = "x", position: float = 0.0,
                       thickness: float = 0.1, output: Optional[str] = None,
                       format: str = "dxf") -> SectionResult:
        """
        生成立面圖（垂直切面）。

        Args:
            direction: "x" 或 "y"
            position: 切面位置
            thickness: 切片厚度
            output: 輸出路徑
            format: "dxf" 或 "svg"
        """
        sec_type = SectionType.ELEVATION_X if direction.lower() == "x" else SectionType.ELEVATION_Y
        params = SectionParams(section_type=sec_type, position=position, thickness=thickness)
        result = extract_section(self.pcd, params)

        if output:
            if format == "svg":
                export_svg(result, output)
            else:
                export_dxf(result, output)

        return result

    def cross_section(self, angle: float = 0.0, position: float = 0.0,
                      thickness: float = 0.1, output: Optional[str] = None,
                      format: str = "dxf") -> SectionResult:
        """生成任意角度剖面圖。"""
        params = SectionParams(
            section_type=SectionType.CROSS, position=position,
            thickness=thickness, angle=angle
        )
        result = extract_section(self.pcd, params)

        if output:
            if format == "svg":
                export_svg(result, output)
            else:
                export_dxf(result, output)

        return result

    def auto_generate(self, output_dir: str, n_plans: int = 3, n_elevations: int = 4,
                      thickness: float = 0.1, formats: tuple = ("dxf", "svg")) -> list[dict]:
        """
        自動生成多個平面圖和立面圖。

        Args:
            output_dir: 輸出目錄
            n_plans: 平面圖數量
            n_elevations: 立面圖數量
            thickness: 切片厚度
            formats: 輸出格式 ("dxf", "svg" 或兩者)
        Returns:
            生成結果列表
        """
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        results = auto_sections(self.pcd, n_plans=n_plans, n_elevations=n_elevations, thickness=thickness)
        outputs = []

        for i, result in enumerate(results):
            if result.n_points == 0:
                logger.warning(f"切面 {i} 無點，跳過")
                continue

            type_name = result.section_type.value
            pos_str = f"{result.position:.1f}".replace(".", "_")
            base_name = f"{type_name}_{pos_str}"

            files = {}
            if "dxf" in formats:
                dxf_path = str(out / f"{base_name}.dxf")
                export_dxf(result, dxf_path)
                files["dxf"] = dxf_path

            if "svg" in formats:
                svg_path = str(out / f"{base_name}.svg")
                export_svg(result, svg_path)
                files["svg"] = svg_path

            outputs.append({
                "type": type_name,
                "position": result.position,
                "n_points": result.n_points,
                "n_contours": len(result.contours),
                "bounds": result.bounds,
                "files": files,
            })

        logger.info(f"自動生成完成: {len(outputs)} 個圖面 → {output_dir}")
        return outputs


def batch_process(input_dir: str, output_dir: str, voxel_size: float = 0.02,
                  n_plans: int = 3, n_elevations: int = 4) -> list[dict]:
    """
    批次處理：掃描目錄內所有點雲檔案，自動生成平立面圖。

    Args:
        input_dir: 點雲輸入目錄
        output_dir: 輸出目錄
        voxel_size: 下採樣大小
        n_plans: 每個檔案生成幾張平面圖
        n_elevations: 每個檔案生成幾張立面圖
    """
    files = scan_directory(input_dir)
    if not files:
        logger.warning(f"目錄 {input_dir} 中沒有點雲檔案")
        return []

    all_results = []
    for f in files:
        logger.info(f"處理: {f['name']} ({f['size_mb']} MB)")
        try:
            out_sub = str(Path(output_dir) / Path(f["name"]).stem)
            pipe = PointCloudPipeline(f["path"], voxel_size=voxel_size)
            results = pipe.auto_generate(out_sub, n_plans=n_plans, n_elevations=n_elevations)
            all_results.append({
                "file": f["name"],
                "info": pipe.info,
                "outputs": results,
            })
        except Exception as e:
            logger.error(f"處理失敗 {f['name']}: {e}")
            all_results.append({"file": f["name"], "error": str(e)})

    return all_results
