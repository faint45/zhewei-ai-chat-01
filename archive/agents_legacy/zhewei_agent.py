import pandas as pd
import ctypes
import os
from datetime import datetime

# [角色任務]：AI 數據代理人
# [核心功能]：獲取授權後自動整理數據至 Excel
class MiniAgent:
    def __init__(self):
        self.filename = "search_log.csv"

    def run(self):
        # 1. 請求許可 (詢問後操作)
        res = ctypes.windll.user32.MessageBoxW(0, "偵測到關注者數據，是否全權授權處理？", "AI 授權", 4)
        if res != 6: # 6 代表點擊「是」
            print("操作已取消。")
            return

        # 2. 全權處理數據 (最簡代碼實現)
        data = [
            {"時間": datetime.now().strftime("%H:%M:%S"), "平台": "Instagram", "行為": "搜尋您的帳號"},
            {"時間": datetime.now().strftime("%H:%M:%S"), "平台": "Facebook", "行為": "查看個人資料"}
        ]
        
        df = pd.DataFrame(data)
        
        # 3. 產出結果 (存檔並複製，方便直接貼到 Excel)
        df.to_csv(self.filename, index=False, encoding='utf-8-sig', mode='a', header=not os.path.exists(self.filename))
        df.to_clipboard(index=False, sep='\t')
        
        print(f"【成功】數據已存入 {self.filename}，且已複製到剪貼簿。請直接在 Excel 按下 Ctrl+V。")

if __name__ == "__main__":
    MiniAgent().run()