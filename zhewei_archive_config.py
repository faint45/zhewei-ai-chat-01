# 築未科技 — E 槽歸檔設定（預留最新版、其餘移入新資料夾）
import os

# E 槽根目錄
E_DRIVE_ROOT = r"E:\"

# 預留最新版本：此資料夾不移動，視為正式版
LATEST_ROOT = os.path.join(E_DRIVE_ROOT, "築未科技開發資料庫")

# 歸檔目標資料夾（其餘築未相關內容移入此處）
ARCHIVE_ROOT = os.path.join(E_DRIVE_ROOT, "築未科技_歸檔")

# 要移入歸檔的築未相關資料夾（相對於 E:\，僅移動與築未／工程相關者）
# 若該名稱不存在於 E:\ 則略過。「下載區」為混合內容未列入，需時可自行加入
FOLDERS_TO_ARCHIVE = [
    "施工圖數量計算excel",
    "光達",
    "堆置區土方",
    "拔林車站",
    "大藍海計畫v1",
    "lidar",
    "moved",
    "新增資料夾 (2)",
]
