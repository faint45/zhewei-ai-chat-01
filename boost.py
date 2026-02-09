# 築未科技 — 雙擊 .bat 時執行之提升腳本（加強／優化，不更動其他）
from pathlib import Path
from data_location_config import RECOGNITION_DATA_ROOT

def main():
    root = Path(RECOGNITION_DATA_ROOT)
    root.mkdir(parents=True, exist_ok=True)
    print("提升完成:", root)

if __name__ == "__main__":
    main()
