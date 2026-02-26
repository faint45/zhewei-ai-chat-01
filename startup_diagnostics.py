# -*- coding: utf-8 -*-
"""
築未科技 — 啟動前環境診斷（入口）
委派 preflight_check.run_main()，供批次檔或手動執行。
"""
import sys
from preflight_check import run_main

if __name__ == "__main__":
    sys.exit(run_main())
