"""
築未科技大腦 - 資料路徑設定
所有資料儲存於 D 槽，支援 append-only 保護
"""
import os
from pathlib import Path

# 預設 D 槽資料目錄，可透過環境變數 ZHEWEI_BRAIN_DATA_DIR 覆寫
_DEFAULT = Path("D:/zhewei_brain_data")
BRAIN_DATA_DIR = Path(os.environ.get("ZHEWEI_BRAIN_DATA_DIR", str(_DEFAULT)))
BRAIN_DATA_DIR.mkdir(parents=True, exist_ok=True)

# 各資料檔路徑
KNOWLEDGE_FILE = BRAIN_DATA_DIR / "brain_knowledge.ndjson"   # append-only
COST_FILE = BRAIN_DATA_DIR / "ai_cost_log.json"
LEARN_FILE = BRAIN_DATA_DIR / "brain_learn.json"
DISCOVERY_FILE = BRAIN_DATA_DIR / "ai_discoveries.json"
HISTORY_FILE = BRAIN_DATA_DIR / "chat_history.json"          # 對話紀錄
REMOTE_CSV = BRAIN_DATA_DIR / "zhewei_remote_master.csv"     # append-only
CHROMA_PATH = BRAIN_DATA_DIR / "brain_chroma_db"

# 舊格式相容（brain_knowledge.json 遷移用）
KNOWLEDGE_JSON_LEGACY = BRAIN_DATA_DIR / "brain_knowledge.json"

# 輸出與暫存（一律 D 槽）
DEV_OUTPUT_PATH = BRAIN_DATA_DIR / "dev_output.py"       # 開發：暫存執行檔
CREATIVE_OUTPUT_DIR = BRAIN_DATA_DIR / "creative_output"  # 創意工具輸出
VISION_OUTPUT_DIR = BRAIN_DATA_DIR / "vision_output"      # 視覺工具輸出
LOG_DIR = BRAIN_DATA_DIR / "logs"                         # 排程/執行 log
TEMP_DIR = BRAIN_DATA_DIR / "temp"                        # 暫存檔
REASONING_LOG = BRAIN_DATA_DIR / "reasoning_trace.ndjson" # AI 運算過程記錄
CURSOR_WATCHER_STATE = BRAIN_DATA_DIR / "cursor_watcher_state.json"  # Cursor 監聽狀態
SELF_LEARN_LOG = BRAIN_DATA_DIR / "self_learn_log.ndjson" # 自我學習紀錄
API_LOG_FILE = LOG_DIR / "brain_bridge_api.ndjson"  # API 請求日誌（每行一筆 JSON）
SESSIONS_FILE = BRAIN_DATA_DIR / "brain_sessions.json"  # Session 持久化

for _d in (CREATIVE_OUTPUT_DIR, VISION_OUTPUT_DIR, LOG_DIR, TEMP_DIR):
    _d.mkdir(parents=True, exist_ok=True)
