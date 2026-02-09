---
name: zhewei-pointcloud-cli
description: 築未科技點雲與 LiDAR CLI 操作。當任務涉及點雲整理、LAS、PLY、工地數據集中、LiDAR 資料夾歸檔、point_cloud_config、organize_las 時套用。教 AI 何時執行專案內點雲腳本與設定檔。
---

# 築未科技 — 點雲 / LiDAR CLI 技能

## 適用情境

- 使用者要求「整理點雲」「集中 LAS」「歸檔工地數據」「設定點雲路徑」「一筆分析一資料夾」。
- 需讀寫或說明 `point_cloud_config.py`、`organize_las_pointcloud.py` 之行為與參數。
- 需處理副檔名：`.las`, `.ply`, `.pcd`, `.codata`, `.cvsp`（點雲）；`.tra`, `.gga`, `.crd`, `.gps`（軌跡）；照片等。

## 專案內工具

| 項目 | 路徑 | 用途 |
|------|------|------|
| 設定檔 | `point_cloud_config.py` | 定義 `POINT_CLOUD_ROOT`、`SOURCES`、副檔名常數；一筆分析一資料夾、整份移動不拆開。 |
| 整理腳本 | `organize_las_pointcloud.py` | 依 `SOURCES` 將來源資料夾整份移入 `POINT_CLOUD_ROOT`，同一筆分析之點雲/照片/GPS 保持同夾。 |

## 執行時機

- **整理/集中點雲**：執行 `python organize_las_pointcloud.py`（需確認 `point_cloud_config.py` 之 `SOURCES`、`POINT_CLOUD_ROOT` 符合環境）。
- **修改路徑或來源**：編輯 `point_cloud_config.py` 之 `POINT_CLOUD_ROOT`、`SOURCES`，再執行整理腳本。
- **僅查詢邏輯**：讀取上述兩檔即可，不必執行。

## 注意事項

- 移動為整份資料夾，不拆開單一檔案；若目標已存在會自動加後綴 `_1`, `_2`。
- `POINT_CLOUD_ROOT` 預設為 `E:\築未科技_點雲與LAS`；與歸檔腳本 `archive_zhewei_to_folder.py` 之執行順序會影響最終位置，需依現場流程說明。
