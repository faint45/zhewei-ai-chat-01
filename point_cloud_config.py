# 築未科技 — LAS／點雲整理設定（同一筆分析所需檔案放一起）
# 原則：一筆分析 = 點雲＋照片＋GPS 軌跡等皆在同一資料夾，不拆開；以整份資料夾移動。
import os

# E 槽根目錄
E_DRIVE_ROOT = r"E:\"

# 點雲與 LAS 統一根目錄（相關分析資料集中於此）
POINT_CLOUD_ROOT = os.path.join(E_DRIVE_ROOT, "築未科技_點雲與LAS")

# 一筆分析常見副檔名（點雲／照片／軌跡等，供掃描或篩選用，僅參考；實際以整份資料夾為單位）
POINT_CLOUD_EXTENSIONS = (".las", ".ply", ".pcd", ".codata", ".cvsp")
ANALYSIS_RELATED_EXTENSIONS = (
    ".las", ".ply", ".pcd", ".codata", ".cvsp",  # 點雲
    ".jpg", ".jpeg", ".png", ".bmp",             # 照片
    ".tra", ".gga", ".crd", ".gps", ".bin",      # GPS／軌跡
)

# 要集中到此根目錄的來源資料夾：(來源絕對路徑, 在根目錄下的子資料夾名稱)
# 整份移動，不拆開該資料夾內之點雲、照片、軌跡等
SOURCES = [
    (os.path.join(E_DRIVE_ROOT, "lidar"), "lidar"),
    (os.path.join(E_DRIVE_ROOT, "光達"), "光達"),
    (os.path.join(E_DRIVE_ROOT, "堆置區土方"), "堆置區土方"),
    (os.path.join(E_DRIVE_ROOT, "下載區", "CopreWorkSpace"), "CopreWorkSpace_下載區"),
]
# 若先執行了 archive_zhewei_to_folder，lidar／光達／堆置區土方會在「築未科技_歸檔」；
# 可改為從歸檔路徑移入，或先執行本腳本再執行歸檔，使點雲集中於本根目錄。
