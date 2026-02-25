# -*- coding: utf-8 -*-
"""
築未科技 Construction Brain
init_project.py

功能：建立新專案的標準資料夾結構與 project.json 設定檔

用法：
    python init_project.py --project_id PRJ-001 --name "國道X號改善工程" --start 2026-02-24
"""

import argparse
import json
import os
from datetime import date
from pathlib import Path

BASE_DIR = Path(os.environ.get("ZHEWEI_BASE", r"C:\ZheweiConstruction"))

DIRS_TO_CREATE = [
    "01_Input/Photos/LINE",
    "01_Input/Photos/施工進度",
    "01_Input/Photos/工安缺失",
    "01_Input/Photos/材料入場",
    "01_Input/Photos/機具運作",
    "01_Input/Photos/竣工查驗",
    "01_Input/Photos/環境天候",
    "01_Input/Photos/其他",
    "01_Input/Voice/LINE",
    "02_Output/Reports",
    "02_Output/events",
    "03_KB",
]


def init_project(
    project_id: str,
    project_name: str,
    contractor: str = "",
    supervisor: str = "",
    start_date: str = "",
    end_date: str = "",
    contract_period: int = 0,
    planned_progress_pct: float = 0.0,
):
    project_dir = BASE_DIR / "projects" / project_id
    if project_dir.exists():
        print(f"[init] [WARN] 專案目錄已存在：{project_dir}")
    else:
        print(f"[init] 建立專案目錄：{project_dir}")

    for sub in DIRS_TO_CREATE:
        d = project_dir / sub
        d.mkdir(parents=True, exist_ok=True)

    (BASE_DIR / "db").mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "logs").mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "config").mkdir(parents=True, exist_ok=True)

    config = {
        "project_id": project_id,
        "project_name": project_name,
        "contractor": contractor,
        "supervisor": supervisor,
        "start_date": start_date or date.today().isoformat(),
        "end_date": end_date,
        "contract_period": contract_period,
        "planned_progress_pct": planned_progress_pct,
        "created_at": date.today().isoformat(),
    }
    config_path = BASE_DIR / "config" / f"{project_id}.json"
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[init] [OK] 專案設定 → {config_path}")

    group_map_path = BASE_DIR / "config" / "group_project_map.json"
    if not group_map_path.exists():
        group_map_path.write_text(json.dumps({}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[init] 建立 LINE群組對應表 → {group_map_path}")
        print(f"[init]   請手動填入：{{\"C1234567890\": \"{project_id}\"}}")

    env_path = BASE_DIR / ".env.example"
    if not env_path.exists():
        env_path.write_text(
            "LINE_CHANNEL_SECRET=your_secret_here\n"
            "LINE_CHANNEL_ACCESS_TOKEN=your_token_here\n"
            f"DEFAULT_PROJECT_ID={project_id}\n"
            f"ZHEWEI_BASE={BASE_DIR}\n"
            "OLLAMA_BASE_URL=http://localhost:11434\n"
            "OLLAMA_MODEL=zhewei-brain\n"
            "WHISPER_MODEL=base\n",
            encoding="utf-8",
        )
        print(f"[init] 建立 .env.example → {env_path}")

    print(f"\n{'='*50}")
    print(f"  專案初始化完成！")
    print(f"  專案代碼：{project_id}")
    print(f"  工程名稱：{project_name}")
    print(f"  根目錄：{project_dir}")
    print(f"{'='*50}")
    print(f"\n下一步：")
    print(f"  1. 複製 .env.example 為 .env 並填入 LINE Token")
    print(f"  2. 在 config/group_project_map.json 填入 LINE 群組 ID 對應")
    print(f"  3. 啟動服務：uvicorn line_receiver:app --port 8003")
    print(f"  4. 設定 Cloudflare Tunnel 指向 localhost:8003")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="築未科技 — 新專案初始化")
    parser.add_argument("--project_id", required=True, help="專案代碼（英數字，例：PRJ-2026-001）")
    parser.add_argument("--name", required=True, help="工程名稱")
    parser.add_argument("--contractor", default="", help="承攬廠商名稱")
    parser.add_argument("--supervisor", default="", help="工地主任姓名")
    parser.add_argument("--start", default="", help="開工日期 YYYY-MM-DD")
    parser.add_argument("--end", default="", help="竣工日期 YYYY-MM-DD")
    parser.add_argument("--period", type=int, default=0, help="核定工期（天）")
    args = parser.parse_args()

    init_project(
        project_id=args.project_id,
        project_name=args.name,
        contractor=args.contractor,
        supervisor=args.supervisor,
        start_date=args.start,
        end_date=args.end,
        contract_period=args.period,
    )
