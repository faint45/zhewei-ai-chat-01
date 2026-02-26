"""
Asset Commander Streamlit 儀表板
即時監控 GPU 挖礦與 HDD 儲存收益
"""

import streamlit as st
import requests
import time
import psutil
from datetime import datetime

st.set_page_config(
    page_title="Asset Commander",
    page_icon="💰",
    layout="wide"
)

API_BASE = "http://localhost:8002"

st.title("💰 Asset Commander - 資產指揮官")

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

def refresh_data():
    try:
        state = requests.get(f"{API_BASE}/api/asset/state", timeout=5).json()
        health = requests.get(f"{API_BASE}/api/asset/health", timeout=5).json()
        config = requests.get(f"{API_BASE}/api/asset/config", timeout=5).json()
        report = requests.get(f"{API_BASE}/api/asset/report", timeout=5).json()
        earnings = requests.get(f"{API_BASE}/api/asset/earnings?days=7", timeout=5).json()
        return state, health, config, report, earnings
    except Exception as e:
        return None, None, None, None, None

col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("🔄 刷新數據"):
        st.session_state.last_refresh = time.time()
        st.rerun()

auto_refresh = st.checkbox("自動刷新 (30秒)", value=False)
if auto_refresh:
    if time.time() - st.session_state.last_refresh > 30:
        st.session_state.last_refresh = time.time()
        st.rerun()

state, health, config, report, earnings = refresh_data()

if not state or not state.get("ok"):
    st.error("無法連接到 Asset Commander API，請確保 brain_server.py 已啟動")
    st.stop()

st.markdown("---")

current_state = state.get("state", {})
platforms = current_state.get("platforms", {})

with col1:
    status_color = "🟢" if current_state.get("running") else "🔴"
    st.metric("系統狀態", f"{status_color} {'運行中' if current_state.get('running') else '已停止'}")

with col2:
    st.metric("當前平臺", current_state.get("current_platform", "none").upper())

with col3:
    profit = current_state.get("net_profit_day", 0)
    profit_color = "normal" if profit >= 0 else "inverse"
    st.metric("每日淨利 (NT$)", f"${profit:.2f}", delta=f"{profit:.2f}", delta_color=profit_color)

with col4:
    should_pause = current_state.get("should_pause")
    pause_status = "⚠️ 應暫停" if should_pause else "✅ 正常運行"
    st.metric("淨利狀態", pause_status)

st.markdown("---")

st.subheader("🎮 GPU 狀態")
g1, g2, g3, g4 = st.columns(4)
with g1:
    st.metric("GPU 功率", f"{current_state.get('gpu_power_watts', 0):.1f} W")
with g2:
    st.metric("GPU 利用率", f"{current_state.get('gpu_utilization', 0):.1f}%")
with g3:
    st.metric("每日收益", f"NT$ {current_state.get('total_earnings_day', 0):.2f}")
with g4:
    st.metric("每日成本", f"NT$ {current_state.get('total_cost_day', 0):.2f}")

st.markdown("---")

st.subheader("📊 平臺比較")
platform_data = []
for name, p in platforms.items():
    platform_data.append({
        "平臺": name.upper(),
        "狀態": p.get("status", "unknown"),
        "每小時收益": p.get("earnings", 0),
        "每小時成本": p.get("cost", 0),
        "每小時淨利": p.get("profit", 0),
        "已啟用": p.get("enabled", False)
    })

import pandas as pd
if platform_data:
    df = pd.DataFrame(platform_data)
    
    def highlight_profit(val):
        if isinstance(val, (int, float)):
            if val > 0:
                return "🟢"
            elif val < 0:
                return "🔴"
        return ""
    
    st.dataframe(
        df.style.format({
            "每小時收益": "${:.4f}",
            "每小時成本": "${:.4f}",
            "每小時淨利": "${:.4f}"
        }),
        use_container_width=True
    )
    
    best = current_state.get("best_platform", "none")
    st.info(f"🏆 最佳平臺: **{best.upper()}** (每小時淨利 NT$ {platforms.get(best, {}).get('profit', 0):.4f})")

st.markdown("---")

st.subheader("📈 收益歷史")
if earnings and earnings.get("ok"):
    history = earnings.get("history", [])
    if history:
        history_df = pd.DataFrame(history)
        history_df["timestamp"] = pd.to_datetime(history_df["timestamp"])
        history_df = history_df.sort_values("timestamp")
        
        chart_data = history_df[["timestamp", "net_profit"]].copy()
        chart_data["date"] = chart_data["timestamp"].dt.date
        daily_profit = chart_data.groupby("date")["net_profit"].sum().reset_index()
        
        st.line_chart(daily_profit.set_index("date")["net_profit"])
    else:
        st.info("尚無收益歷史資料")
else:
    st.info("無法載入收益歷史")

st.markdown("---")

st.subheader("⚙️ 配置")

with st.expander("電費與門檻設定"):
    cfg = config.get("config", {}) if config.get("ok") else {}
    electricity_rate = cfg.get("electricity_rate", 4.0)
    min_threshold = cfg.get("min_profit_threshold", 0.5)
    
    c1, c2 = st.columns(2)
    with c1:
        new_rate = st.number_input("電費 (NT$/kWh)", value=electricity_rate, step=0.1)
    with c2:
        new_threshold = st.number_input("最低淨利門檻 (NT$/天)", value=min_threshold, step=0.1)
    
    if st.button("儲存設定"):
        try:
            resp = requests.post(
                f"{API_BASE}/api/asset/config",
                json={"electricity_rate": new_rate, "min_profit_threshold": new_threshold},
                timeout=5
            )
            if resp.json().get("ok"):
                st.success("設定已儲存")
            else:
                st.error("儲存失敗")
        except Exception as e:
            st.error(f"錯誤: {e}")

with st.expander("平臺設定"):
    gpu_cfg = cfg.get("gpu", {})
    st.write(f"**GPU**: {gpu_cfg.get('name', 'RTX 4060 Ti')} - {gpu_cfg.get('watts', 160)}W")
    
    st.write("**平臺 API 設定** (請輸入真實 API Key 以啟用)")
    for platform_name in ["io_net", "render", "salad", "storj"]:
        pcfg = cfg.get("platforms", {}).get(platform_name, {})
        with st.expander(f"{platform_name.upper()} 設定"):
            enabled = st.checkbox("啟用", value=pcfg.get("enabled", True), key=f"enable_{platform_name}")
            if platform_name == "storj":
                storage = st.number_input("儲存空間 (GB)", value=pcfg.get("storage_gb", 0), key=f"storage_{platform_name}")
                rate = st.number_input("月費率 (NT$/GB/月)", value=pcfg.get("earnings_per_gb_month", 0.0), step=0.01, key=f"rate_{platform_name}")
            else:
                hourly = st.number_input("每小時收益 (NT$)", value=pcfg.get("earnings_per_gpu_hour", 0.0), step=0.01, key=f"hourly_{platform_name}")

st.markdown("---")

st.subheader("🎮 控制")

c1, c2, c3 = st.columns(3)
with c1:
    if current_state.get("running"):
        if st.button("⏹️ 停止"):
            try:
                resp = requests.post(f"{API_BASE}/api/asset/stop", timeout=5)
                if resp.json().get("ok"):
                    st.success("已停止")
                    time.sleep(1)
                    st.rerun()
            except Exception as e:
                st.error(f"錯誤: {e}")
    else:
        if st.button("▶️ 啟動"):
            try:
                resp = requests.post(f"{API_BASE}/api/asset/start", timeout=5)
                if resp.json().get("ok"):
                    st.success("已啟動")
                    time.sleep(1)
                    st.rerun()
            except Exception as e:
                st.error(f"錯誤: {e}")

with c2:
    if st.button("🔄 刷新收益"):
        try:
            resp = requests.post(f"{API_BASE}/api/asset/refresh", timeout=10)
            if resp.json().get("ok"):
                st.success("已刷新")
                time.sleep(1)
                st.rerun()
        except Exception as e:
            st.error(f"錯誤: {e}")

with c3:
    best_platform = current_state.get("best_platform", "none")
    if best_platform != "none" and best_platform != current_state.get("current_platform"):
        if st.button(f"🔀 切換到 {best_platform.upper()}"):
            try:
                resp = requests.post(
                    f"{API_BASE}/api/asset/switch",
                    json={"platform": best_platform},
                    timeout=5
                )
                if resp.json().get("ok"):
                    st.success(f"已切換到 {best_platform.upper()}")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("切換失敗")
            except Exception as e:
                st.error(f"錯誤: {e}")

st.markdown("---")

st.caption(f"最後更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
