"""
築未科技 - 高端管理儀表板 (Streamlit)
讀取 zhewei_remote_master.csv 進行 2026 格式數據展示
"""
import pandas as pd
import streamlit as st
from pathlib import Path

from brain_data_config import REMOTE_CSV as CSV_FILE


def main():
    st.set_page_config(page_title="築未智慧營建", layout="wide")
    st.title("築未科技 - 智慧營建管理儀表板")
    st.caption("數位足跡 / 2026 格式")

    if not CSV_FILE.exists():
        st.warning("尚無資料，請先透過 Discord 傳令兵發送指令。")
        return

    df = pd.read_csv(CSV_FILE, encoding="utf-8-sig")
    df = df.sort_values(by="時間", ascending=False)
    st.dataframe(df, use_container_width=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("總筆數", len(df))
    with col2:
        if "狀態" in df.columns:
            done = (df["狀態"] == "完成").sum()
            st.metric("已完成", done)
    with col3:
        if "時間" in df.columns:
            recent = df["時間"].iloc[0] if len(df) > 0 else "-"
            st.metric("最近一筆", recent)


if __name__ == "__main__":
    main()
