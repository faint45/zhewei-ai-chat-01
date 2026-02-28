"""快速測試點雲→平立面圖模組"""
import sys
sys.path.insert(0, r"D:\zhe-wei-tech")

from construction_brain.pointcloud.pipeline import PointCloudPipeline

INPUT = r"E:\我的雲端硬碟\0519\2024-12-31-153900result.las"
OUTPUT = r"D:\zhe-wei-tech\brain_workspace\pointcloud_output"

print(f"載入 {INPUT} (1.72 億點，下採樣中...)")
pipe = PointCloudPipeline(INPUT, voxel_size=0.2)  # 0.2m voxel for 172M points
print("=== 點雲資訊 ===")
for k, v in pipe.info.items():
    print(f"  {k}: {v}")

print("\n=== 自動生成平立面圖 ===")
results = pipe.auto_generate(OUTPUT, n_plans=2, n_elevations=2, thickness=1.0)
print(f"\n生成 {len(results)} 個圖面:")
for r in results:
    print(f"  [{r['type']}] pos={r['position']:.1f}m  pts={r['n_points']}  contours={r['n_contours']}")
    for fmt, path in r.get("files", {}).items():
        print(f"    → {fmt}: {path}")

print("\n完成！")
