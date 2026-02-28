# -*- coding: utf-8 -*-
"""
築未科技 — 自動備份腳本
═══════════════════════════════════════
備份項目：
  1. PostgreSQL（pg_dump via docker exec）
  2. brain_workspace 關鍵資料（auth, licenses, usage, kb）
  3. .env 設定檔
  4. 支付記錄

備份目錄：D:\\zhewei_backups\\YYYY-MM-DD_HHMMSS\\
保留策略：保留最近 30 天

執行：
  python scripts/backup_all.py                    # 手動
  schtasks 排程每天凌晨 3:00 自動執行             # 自動

Windows Task Scheduler 設定（以管理員執行）：
  schtasks /create /tn "ZheWei-Daily-Backup" /tr "D:\\zhe-wei-tech\\.venv312\\Scripts\\python.exe D:\\zhe-wei-tech\\scripts\\backup_all.py" /sc daily /st 03:00 /ru SYSTEM /f
"""
import datetime
import os
import shutil
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── 設定 ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKUP_ROOT = Path(os.environ.get("ZHEWEI_BACKUP_DIR", str(PROJECT_ROOT / "backups")))
RETENTION_DAYS = int(os.environ.get("BACKUP_RETENTION_DAYS", "30"))

# PG 容器名稱（嘗試多個）
PG_CONTAINERS = ["docker-db_postgres-1", "zhewei_postgres", "postgres"]
PG_DATABASE = os.environ.get("PG_DATABASE", "jarvis")
PG_USER = os.environ.get("PG_USER", "postgres")

# 要備份的目錄/檔案
BACKUP_ITEMS = [
    ("brain_workspace/auth",       "auth"),
    ("brain_workspace/licenses",   "licenses"),
    ("brain_workspace/usage",      "usage"),
    ("brain_workspace/kb_snapshots", "kb_snapshots"),
    (".env",                       ".env"),
    ("brain_workspace/orders",     "orders"),
]

PASSED = 0
FAILED = 0


def _step(name, fn):
    global PASSED, FAILED
    try:
        fn()
        PASSED += 1
        print(f"  ✅ {name}")
    except Exception as e:
        FAILED += 1
        print(f"  ❌ {name} — {e}")


def backup_postgres(backup_dir: Path):
    """透過 docker exec 執行 pg_dump。"""
    dump_file = backup_dir / "postgres_jarvis.sql.gz"

    for container in PG_CONTAINERS:
        # 檢查容器是否存在
        check = subprocess.run(
            ["docker", "inspect", container],
            capture_output=True, text=True
        )
        if check.returncode != 0:
            continue

        # 執行 pg_dump | gzip
        cmd = [
            "docker", "exec", container,
            "pg_dump", "-U", PG_USER, "-d", PG_DATABASE,
            "--no-owner", "--no-privileges", "--clean", "--if-exists"
        ]
        with open(dump_file.with_suffix(""), "wb") as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, timeout=120)

        if result.returncode == 0:
            # 壓縮
            import gzip
            sql_file = dump_file.with_suffix("")
            with open(sql_file, "rb") as f_in:
                with gzip.open(str(dump_file), "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            sql_file.unlink()
            size_mb = dump_file.stat().st_size / 1024 / 1024
            print(f"    📦 {dump_file.name} ({size_mb:.1f} MB) from {container}")
            return
        else:
            stderr = result.stderr.decode("utf-8", errors="replace")
            if "does not exist" in stderr:
                print(f"    ⚠️  Database '{PG_DATABASE}' not found in {container}")
                continue
            raise RuntimeError(f"pg_dump failed: {stderr[:200]}")

    raise RuntimeError(f"No PG container found: tried {PG_CONTAINERS}")


def backup_files(backup_dir: Path):
    """備份關鍵檔案和目錄。"""
    for src_rel, dst_name in BACKUP_ITEMS:
        src = PROJECT_ROOT / src_rel
        dst = backup_dir / dst_name

        if not src.exists():
            print(f"    ⏭️  {src_rel} (不存在，跳過)")
            continue

        if src.is_dir():
            shutil.copytree(str(src), str(dst), dirs_exist_ok=True)
            count = sum(1 for _ in dst.rglob("*") if _.is_file())
            print(f"    📁 {dst_name}/ ({count} files)")
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dst))
            print(f"    📄 {dst_name}")


def cleanup_old_backups():
    """刪除超過保留期限的備份。"""
    if not BACKUP_ROOT.exists():
        return
    cutoff = datetime.datetime.now() - datetime.timedelta(days=RETENTION_DAYS)
    removed = 0
    for d in sorted(BACKUP_ROOT.iterdir()):
        if not d.is_dir():
            continue
        try:
            # 目錄名格式：2026-02-27_230000
            dir_date = datetime.datetime.strptime(d.name[:10], "%Y-%m-%d")
            if dir_date < cutoff:
                shutil.rmtree(str(d))
                removed += 1
        except (ValueError, IndexError):
            continue
    if removed:
        print(f"    🗑️  清理 {removed} 個過期備份（> {RETENTION_DAYS} 天）")
    else:
        print(f"    ✅ 無過期備份需清理")


def send_notification(backup_dir: Path, success: bool):
    """透過 Ntfy 發送備份結果通知。"""
    try:
        ntfy_url = os.environ.get("NTFY_URL", "http://localhost:2586")
        topic = os.environ.get("NTFY_TOPIC", "zhewei-alerts")
        import urllib.request
        status_text = "OK" if success else "PARTIAL_FAIL"
        size = sum(f.stat().st_size for f in backup_dir.rglob("*") if f.is_file()) / 1024 / 1024
        msg = f"Backup {status_text}\nDir: {backup_dir.name}\nSize: {size:.1f} MB\nResult: {PASSED} ok, {FAILED} fail"
        req = urllib.request.Request(
            f"{ntfy_url}/{topic}",
            data=msg.encode("utf-8"),
            method="POST",
        )
        req.add_header("Title", f"ZheWei Backup {status_text}")
        req.add_header("Priority", "3" if success else "4")
        req.add_header("Tags", "floppy_disk" if success else "warning")
        urllib.request.urlopen(req, timeout=5)
        print(f"  📨 通知已發送到 Ntfy")
    except Exception as e:
        print(f"  ⚠️  Ntfy 通知失敗: {e}")


def main():
    ts = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    backup_dir = BACKUP_ROOT / ts
    backup_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 55)
    print(f"築未科技備份 — {ts}")
    print(f"目標: {backup_dir}")
    print("=" * 55)

    print("\n📦 PostgreSQL 備份")
    _step("pg_dump", lambda: backup_postgres(backup_dir))

    print("\n📁 檔案備份")
    _step("關鍵檔案", lambda: backup_files(backup_dir))

    print("\n🗑️  清理過期備份")
    _step("清理", cleanup_old_backups)

    total_size = sum(f.stat().st_size for f in backup_dir.rglob("*") if f.is_file()) / 1024 / 1024
    success = FAILED == 0

    print(f"\n{'=' * 55}")
    print(f"結果: {PASSED} 成功, {FAILED} 失敗 | 總大小: {total_size:.1f} MB")
    print(f"{'=' * 55}")

    send_notification(backup_dir, success)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
