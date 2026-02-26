"""
智慧數據歸檔 - 將戰情數據寫入 CSV
"""
import os
from datetime import datetime

import pandas as pd


class DataArchiver:
    def __init__(self, filename: str = "network_performance.csv"):
        self.filename = filename

    def log_performance(self, node: str, throughput: float, ops: float) -> None:
        data = {
            "Timestamp": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            "Node": [node],
            "Throughput(MB/s)": [throughput],
            "OPS": [ops],
        }
        df = pd.DataFrame(data)
        exists = os.path.exists(self.filename)
        df.to_csv(self.filename, mode="a", header=not exists, index=False)
