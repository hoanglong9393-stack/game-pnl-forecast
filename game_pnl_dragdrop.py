import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import io
import json
import requests

st.set_page_config(page_title="Game P&L Forecast Pro - Hoàng Thành Long", layout="wide", page_icon="🎮")

GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycby9Vn-O9aaUjikdUMUnb5h063WCAlVnFVK2SwcIGYSRxj3qeoB8h1-T909WO3KtVWl9sw/exec"

# ==========================================
# CUSTOM CSS
# ==========================================
st.markdown("""
<style>
    .section-title { font-size: 20px; font-weight: 600; color: #1E293B; margin-top: 10px; margin-bottom: 8px; }
    .dataframe-container { overflow-x: auto; margin-bottom: 20px; }
    table.custom-pnl { width: 100%; border-collapse: collapse; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 13px; color: #E2E8F0; background-color: #0F172A; }
    table.custom-pnl th { background-color: #0B3E45; color: white; font-weight: bold; text-align: center; padding: 8px 5px; border: 1px solid #1E293B; min-width: 100px; }
    table.custom-pnl th:first-child { background-color: #002B36; text-align: left; min-width: 200px; position: sticky; left: 0; z-index: 10; }
    table.custom-pnl td { padding: 6px 8px; text-align: right; border: 1px solid #334155; }
    table.custom-pnl td:first-child { text-align: left; font-weight: 500; position: sticky; left: 0; background-color: #0F172A; z-index: 9; border-right: 2px solid #475569; }
    
    table.custom-pnl tr.row-nru td { background-color: #F59E0B; color: black; }
    table.custom-pnl tr.row-cost td { background-color: #FBBF24; color: black; }
    table.custom-pnl tr.row-rev-total td { background-color: #DC2626; color: white; font-weight: bold; }
    table.custom-pnl tr.row-spent-header td { background-color: #94A3B8; color: black; font-weight: bold; text-align: left;}
    table.custom-pnl tr.row-opex td { background-color: #FCD34D; color: black; }
    table.custom-pnl tr.row-total-cost td { background-color: #DC2626; color: white; font-weight: bold; }
    
    table.custom-pnl tr.row-profit-month td { background-color: white; color: black; }
    table.custom-pnl tr.row-profit-month td.positive { background-color: #22C55E; color: white; }
    table.custom-pnl tr.row-profit-cum td { background-color: white; color: black; font-weight: bold; }
    table.custom-pnl tr.row-profit-cum td.positive { background-color: #22C55E; color: white; }
    table.custom-pnl tr.row-roi td { background-color: white; color: black; }
    
    table.custom-pnl tr.row-nru td:first-child { background-color: #F59E0B; color: black;}
    table.custom-pnl tr.row-rev-total td:first-child { background-color: #DC2626; color: white; }
    table.custom-pnl tr.row-total-cost td:first-child { background-color: #DC2626; color: white; }
</style>
""", unsafe_allow_html=True)

st.title("🎮 Hệ Thống Dự Phóng P&L by Hoàng Thành Long (VplayHN)")

# ==========================================
# KHỞI TẠO DỮ LIỆU MẶC ĐỊNH
# ==========================================
def get_default_traffic(total_months=25, is_android=True):
    months_label = ["Pre-launch", "Month OB"] + [f"Month OB+{i}" for i in range(1, total_months - 1)]
    if is_android:
        return pd.DataFrame({
            "Tháng": months_label,
            "NRU": [0, 100000] + [70000] * (total_months - 2),
            "CPN (VNĐ)": [0, 25000] + [25000] * (total_months - 2),
            "Nhân sự (VNĐ)": [400000000, 200000000] + [200000000] * (total_months - 2),
            "Server (VNĐ)": [0, 200000000] + [200000000] * (total_months - 2),
            "LF + Branding (VNĐ)": [675000000, 1800000000] + [50000000] * (total_months - 2)
        })
    else:
        return pd.DataFrame({
            "Tháng": months_label,
            "NRU": [0, 50000] + [30000] * (total_months - 2),
            "CPN (VNĐ)": [0, 32000] + [32000] * (total_months - 2)
        })

ALL_D_COLS = ["D1", "D3", "D7", "D14", "D30", "D60", "D90", "D180", "D210", "D240", "D270", "D300", "D330", "D360"]
ALL_D_TARGETS = [3, 7, 14, 30, 60, 90, 180, 210, 240, 270, 300, 330, 360]

def get_default_ltv(is_android=True):
    if is_android:
        return pd.DataFrame({
            "Phase Name": ["Phase 1 (Tháng OB)", "Phase 2 (Tháng 2&3)", "Phase 3 (Tháng 4+)"],
            "Áp dụng từ Tháng": ["Month OB", "Month OB+1", "Month OB+3"],
            "D1": [9000, 7000, 4500],
            "D3": [13500, 10500, 7000],
            "D7": [27000, 22000, 13000],
            "D14": [40000, 33000, 22000],
            "D30": [54000, 44000, 30000],
            "D60": [72000, 57000, 35000],
            "D90": [85000, 66000, 40000],
            "D180": [108000, 80000, 45000],
            "D210": [112000, 83000, 46000],
            "D240": [116000, 86000, 47000],
            "D270": [120000, 89000, 48000],
            "D300": [124000, 92000, 49000],
            "D330": [128000, 95000, 50000],
            "D360": [132000, 98000, 51000]
        })
    else:
        return pd.DataFrame({
            "Phase Name": ["Phase 1 (Tháng OB)", "Phase 2 (Tháng 2&3)", "Phase 3 (Tháng 4+)"],
            "Áp dụng từ Tháng": ["Month OB", "Month OB+1", "Month OB+3"],
            "D1": [12000, 10000, 6000],
            "D3": [18000, 15000, 10000],
            "D7": [36000, 31000, 19000],
            "D14": [55000, 48000, 31000],
            "D30": [72000, 62000, 45000],
            "D60": [96000, 81000, 50000],
            "D90": [115000, 93000, 55000],
            "D180": [144000, 110000, 60000],
            "D210": [150000, 113000, 61000],
            "D240": [156000, 116000, 62000],
            "D270": [162000, 119000, 63000],
            "D300": [168000, 122000, 64000],
            "D330": [174000, 125000, 65000],
            "D360": [180000, 128000, 66000]
        })

if "project_names" not in st.session_state:
    st.session_state.project_names = ["Dự án 1 (T029)"]
    st.session_state.current_project = "Dự án 1 (T029)"

# ==========================================
# KHU VỰC QUẢN LÝ DỰ ÁN & ĐỒNG BỘ CLOUD (SIDEBAR)
# ==========================================
with st.sidebar:
    st.header("📁 Quản Lý Dự Án")
    
    selected_proj = st.selectbox(
        "Chọn dự án đang làm việc:", 
        st.session_state.project_names, 
        index=st.session_state.project_names.index(st.session_state.current_project)
    )
    st.session_state.current_project = selected_proj
    cur_proj = st.session_state.current_project
    
    with st.expander("➕ Tạo Dự Án Mới"):
        new_proj_name = st.text_input("Tên dự án mới:")
        new_proj_months = st.number_input("Số tháng dự phóng", min_value=3, max_value=60, value=25)
        if st.button("Tạo & Lưu"):
            if new_proj_name and new_proj_name not in st.session_state.project_names:
                st.session_state.project_names.append(new_proj_name)
                st.session_state[f"traffic_android_{new_proj_name}"] = get_default_traffic(new_proj_months, True)
                st.session_state[f"traffic_ios_{new_proj_name}"] = get_default_traffic(new_proj_months, False)
                st.session_state[f"ltv_android_{new_proj_name}"] = get_default_ltv(True)
                st.session_state[f"ltv_ios_{new_proj_name}"] = get_default_ltv(False)
                st.session_state[f"params_{new_proj_name}"] = {"rev_share": 20.2, "vat": 10.0, "payment_fee": 5.0}
                st.session_state.current_project = new_proj_name
                st.rerun()
            elif new_proj_name in st.session_state.project_names:
                st.warning("Tên dự án đã tồn tại!")

    st.markdown("---")
    st.header("☁️ Đồng Bộ Máy Khác (Google Sheet)")
    
    if st.button("🔄 Kéo Toàn Bộ Dữ Liệu Từ Sheet Về", help="Bấm nút này khi mở web trên máy mới để lấy lại tất cả 5 bảng của mọi dự án."):
        with st.spinner("Đang tải dữ liệu từ Google Sheet..."):
            try:
                resp = requests.get(GOOGLE_SCRIPT_URL, timeout=20)
                data = resp.json()
                if "project_names" in data:
                    st.session_state.project_names = data["project_names"]
                    st.session_state.current_project = data["current_project"]
                    for p, p_val in data["projects_data"].items():
                        st.session_state[f"traffic_android_{p}"] = pd.DataFrame(p_val["traffic_android"])
                        st.session_state[f"traffic_ios_{p}"] = pd.DataFrame(p_val["traffic_ios"])
                        st.session_state[f"ltv_android_{p}"] = pd.DataFrame(p_val["ltv_android"])
                        st.session_state[f"ltv_ios_{p}"] = pd.DataFrame(p_val["ltv_ios"])
                        st.session_state[f"params_{p}"] = p_val["params"]
                    st.success("🎉 Đã khôi phục thành công toàn bộ dự án từ Google Sheet!")
                    st.rerun()
                else:
                    st.warning("Chưa có bản sao lưu trên Google Sheet.")
            except Exception as e:
                st.error(f"Lỗi tải dữ liệu: {e}")

    st.markdown("---")
    st.header("💸 Cấu Hình Chi Phí Dự Án Này (%)")
    
    if f"params_{cur_proj}" not in st.session_state:
        st.session_state[f"params_{cur_proj}"] = {"rev_share": 20.2, "vat": 10.0, "payment_fee": 5.0}
        
    p_params = st.session_state[f"params_{cur_proj}"]
    
    rev_share_pct = st.number_input("Revenue Share Dev (%)", value=float(p_params["rev_share"]), step=0.1, key=f"rev_{cur_proj}")
    vat_pct = st.number_input("VAT (%)", value=float(p_params["vat"]), step=0.5, key=f"vat_{cur_proj}")
    payment_fee_pct = st.number_input("Payment Channel Fee (%)", value=float(p_params["payment_fee"]), step=0.5, key=f"pay_{cur_proj}")
    
    st.session_state[f"params_{cur_proj}"] = {
        "rev_share": rev_share_pct, "vat": vat_pct, "payment_fee": payment_fee_pct
    }

st.info(f"Đang làm việc trên dự án: **{cur_proj}**")

# Khởi tạo state dữ liệu 2 hệ nếu chưa có
if f"traffic_android_{cur_proj}" not in st.session_state:
    st.session_state[f"traffic_android_{cur_proj}"] = get_default_traffic(25, True)
if f"traffic_ios_{cur_proj}" not in st.session_state:
    st.session_state[f"traffic_ios_{cur_proj}"] = get_default_traffic(25, False)
if f"ltv_android_{cur_proj}" not in st.session_state:
    st.session_state[f"ltv_android_{cur_proj}"] = get_default_ltv(True)
if f"ltv_ios_{cur_proj}" not in st.session_state:
    st.session_state[f"ltv_ios_{cur_proj}"] = get_default_ltv(False)

# ==========================================
# 5 TABS: TRAFFIC ANDROID, TRAFFIC IOS, LTV ANDROID, LTV IOS, P&L TỔNG
# ==========================================
tab_tr_adr, tab_tr_ios, tab_ltv_adr, tab_ltv_ios, tab_pnl_total = st.tabs([
    "🤖 1. Traffic Android", 
    "🍎 2. Traffic iOS", 
    "📈 3. LTV Android", 
    "🍏 4. LTV iOS", 
    "📊 5. Báo Cáo P&L Tổng Hợp"
])

# Helper LTV Curve
def create_daily_ltv_curve(anchor_points):
    days = sorted(anchor_points.keys())
    max_day = 720
    full_curve = np.zeros(max_day + 1)
    for i in range(len(days) - 1):
        d_start, d_end = days[i], days[i+1]
        v_start, v_end = anchor_points[d_start], anchor_points[d_end]
        full_curve[d_start:d_end+1] = np.linspace(v_start, v_end, d_end - d_start + 1)
    last_day = days[-1]
    last_val = anchor_points[last_day]
    full_curve[last_day:max_day+1] = last_val
    return full_curve

# ==========================================
# TAB 1: TRAFFIC ANDROID
# ==========================================
with tab_tr_adr:
    st.markdown(f'<div class="section-title">1. Kế Hoạch Traffic & Định Phí - ANDROID ({cur_proj})</div>', unsafe_allow_html=True)
    st.caption("👉 Nhập số lượng **NRU**, **CPN Android** và các chi phí chung của dự án.")
    
    tr_adr_df = st.session_state[f"traffic_android_{cur_proj}"].copy()
    edited_tr_adr = st.data_editor(
        tr_adr_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key=f"ed_tr_adr_{cur_proj}",
        column_config={
            "NRU": st.column_config.NumberColumn("NRU Android", format="%d", min_value=0),
            "CPN (VNĐ)": st.column_config.NumberColumn("CPN Android (VNĐ)", format="%d", min_value=0),
            "Nhân sự (VNĐ)": st.column_config.NumberColumn("Nhân sự (VNĐ)", format="%d", min_value=0),
            "Server (VNĐ)": st.column_config.NumberColumn("Server (VNĐ)", format="%d", min_value=0),
            "LF + Branding (VNĐ)": st.column_config.NumberColumn("LF + Branding (VNĐ)", format="%d", min_value=0)
        }
    )
    
    # Marketing summary Android
    st.markdown("**Ngân sách Marketing Android Tự Động (CPN × NRU):**")
    mkt_adr = edited_tr_adr.copy()
    mkt_adr["Marketing Budget (VNĐ)"] = pd.to_numeric(mkt_adr["NRU"], errors="coerce").fillna(0) * pd.to_numeric(mkt_adr["CPN (VNĐ)"], errors="coerce").fillna(0)
    st.dataframe(mkt_adr[["Tháng", "NRU", "CPN (VNĐ)", "Marketing Budget (VNĐ)"]].style.format({"NRU": "{:,.0f}", "CPN (VNĐ)": "{:,.0f} đ", "Marketing Budget (VNĐ)": "{:,.0f} đ"}), use_container_width=True, hide_index=True)

# ==========================================
# TAB 2: TRAFFIC IOS
# ==========================================
with tab_tr_ios:
    st.markdown(f'<div class="section-title">2. Kế Hoạch Traffic - iOS ({cur_proj})</div>', unsafe_allow_html=True)
    st.caption("👉 Nhập số lượng **NRU** và **CPN iOS** (Chi phí cố định Nhân sự, Server được quản lý tập trung ở bảng Android/Dự án).")
    
    tr_ios_df = st.session_state[f"traffic_ios_{cur_proj}"].copy()
    if len(tr_ios_df) != len(edited_tr_adr):
        tr_ios_df = pd.DataFrame({
            "Tháng": edited_tr_adr["Tháng"],
            "NRU": [0, 50000] + [30000] * (len(edited_tr_adr) - 2),
            "CPN (VNĐ)": [0, 32000] + [32000] * (len(edited_tr_adr) - 2)
        })
        
    edited_tr_ios = st.data_editor(
        tr_ios_df[["Tháng", "NRU", "CPN (VNĐ)"]],
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key=f"ed_tr_ios_{cur_proj}",
        column_config={
            "NRU": st.column_config.NumberColumn("NRU iOS", format="%d", min_value=0),
            "CPN (VNĐ)": st.column_config.NumberColumn("CPN iOS (VNĐ)", format="%d", min_value=0)
        }
    )
    
    # Marketing summary iOS
    st.markdown("**Ngân sách Marketing iOS Tự Động (CPN × NRU):**")
    mkt_ios = edited_tr_ios.copy()
    mkt_ios["Marketing Budget (VNĐ)"] = pd.to_numeric(mkt_ios["NRU"], errors="coerce").fillna(0) * pd.to_numeric(mkt_ios["CPN (VNĐ)"], errors="coerce").fillna(0)
    st.dataframe(mkt_ios[["Tháng", "NRU", "CPN (VNĐ)", "Marketing Budget (VNĐ)"]].style.format({"NRU": "{:,.0f}", "CPN (VNĐ)": "{:,.0f} đ", "Marketing Budget (VNĐ)": "{:,.0f} đ"}), use_container_width=True, hide_index=True)

# ==========================================
# TAB 3: LTV ANDROID
# ==========================================
with tab_ltv_adr:
    st.markdown(f'<div class="section-title">3. Cấu Hình LTV Curve & Hệ Số K - ANDROID ({cur_proj})</div>', unsafe_allow_html=True)
    st.caption("👉 Điền giá trị LTV tích lũy từng mốc ngày tuổi cho **Android**. Bảng K tự động tính bên dưới ($K_x = LTV_x / LTV_1$).")
    
    month_options = edited_tr_adr["Tháng"].tolist()
    col_cfg_adr = {"Áp dụng từ Tháng": st.column_config.SelectboxColumn("Áp dụng từ Tháng", options=month_options)}
    for c in ALL_D_COLS: col_cfg_adr[c] = st.column_config.NumberColumn(f"{c} (VNĐ)", format="%d", min_value=0)
    
    ltv_adr_state = st.session_state[f"ltv_android_{cur_proj}"].copy()
    for col_d in ALL_D_COLS:
        if col_d not in ltv_adr_state.columns: ltv_adr_state[col_d] = 0
        
    edited_ltv_adr = st.data_editor(
        ltv_adr_state[["Phase Name", "Áp dụng từ Tháng"] + ALL_D_COLS],
        num_rows="dynamic",
        use_container_width=True,
        column_config=col_cfg_adr,
        hide_index=True,
        key=f"ed_ltv_adr_{cur_proj}"
    )
    
    st.markdown("**Bảng Hệ Số Tăng Trưởng K Tự Động (Android):**")
    k_adr_df = edited_ltv_adr.copy()
    for c in ALL_D_COLS: k_adr_df[c] = pd.to_numeric(k_adr_df[c], errors="coerce").fillna(0.0)
    k_adr_df['K1'] = np.where(k_adr_df['D1'] > 0, 1.0, 0.0)
    for d in ALL_D_TARGETS: k_adr_df[f'K{d}'] = np.where(k_adr_df['D1'] > 0, k_adr_df[f'D{d}'] / k_adr_df['D1'], 0.0)
    st.dataframe(k_adr_df[["Phase Name", "Áp dụng từ Tháng", "K1"] + [f'K{d}' for d in ALL_D_TARGETS]].style.format({f'K{d}': "{:.2f}x" for d in [1] + ALL_D_TARGETS}), use_container_width=True, hide_index=True)

    fig_ltv_adr = go.Figure()
    for idx, row in edited_ltv_adr.iterrows():
        try:
            anchors = {int(c[1:]): float(row[c]) for c in ALL_D_COLS}
            curve = create_daily_ltv_curve(anchors)
            fig_ltv_adr.add_trace(go.Scatter(x=np.arange(1, 361), y=curve[1:361], name=str(row['Phase Name'])))
        except: pass
    fig_ltv_adr.update_layout(height=300, template="plotly_white", margin=dict(l=0, r=0, t=30, b=0), xaxis_title="Ngày tuổi (Day)", yaxis_title="LTV Android (VNĐ)")
    st.plotly_chart(fig_ltv_adr, use_container_width=True)

# ==========================================
# TAB 4: LTV IOS
# ==========================================
with tab_ltv_ios:
    st.markdown(f'<div class="section-title">4. Cấu Hình LTV Curve & Hệ Số K - iOS ({cur_proj})</div>', unsafe_allow_html=True)
    st.caption("👉 Điền giá trị LTV tích lũy từng mốc ngày tuổi cho **iOS**. Bảng K tự động tính bên dưới ($K_x = LTV_x / LTV_1$).")
    
    col_cfg_ios = {"Áp dụng từ Tháng": st.column_config.SelectboxColumn("Áp dụng từ Tháng", options=month_options)}
    for c in ALL_D_COLS: col_cfg_ios[c] = st.column_config.NumberColumn(f"{c} (VNĐ)", format="%d", min_value=0)
    
    ltv_ios_state = st.session_state[f"ltv_ios_{cur_proj}"].copy()
    for col_d in ALL_D_COLS:
        if col_d not in ltv_ios_state.columns: ltv_ios_state[col_d] = 0
        
    edited_ltv_ios = st.data_editor(
        ltv_ios_state[["Phase Name", "Áp dụng từ Tháng"] + ALL_D_COLS],
        num_rows="dynamic",
        use_container_width=True,
        column_config=col_cfg_ios,
        hide_index=True,
        key=f"ed_ltv_ios_{cur_proj}"
    )
    
    st.markdown("**Bảng Hệ Số Tăng Trưởng K Tự Động (iOS):**")
    k_ios_df = edited_ltv_ios.copy()
    for c in ALL_D_COLS: k_ios_df[c] = pd.to_numeric(k_ios_df[c], errors="coerce").fillna(0.0)
    k_ios_df['K1'] = np.where(k_ios_df['D1'] > 0, 1.0, 0.0)
    for d in ALL_D_TARGETS: k_ios_df[f'K{d}'] = np.where(k_ios_df['D1'] > 0, k_ios_df[f'D{d}'] / k_ios_df['D1'], 0.0)
    st.dataframe(k_ios_df[["Phase Name", "Áp dụng từ Tháng", "K1"] + [f'K{d}' for d in ALL_D_TARGETS]].style.format({f'K{d}': "{:.2f}x" for d in [1] + ALL_D_TARGETS}), use_container_width=True, hide_index=True)

    fig_ltv_ios = go.Figure()
    for idx, row in edited_ltv_ios.iterrows():
        try:
            anchors = {int(c[1:]): float(row[c]) for c in ALL_D_COLS}
            curve = create_daily_ltv_curve(anchors)
            fig_ltv_ios.add_trace(go.Scatter(x=np.arange(1, 361), y=curve[1:361], name=str(row['Phase Name'])))
        except: pass
    fig_ltv_ios.update_layout(height=300, template="plotly_white", margin=dict(l=0, r=0, t=30, b=0), xaxis_title="Ngày tuổi (Day)", yaxis_title="LTV iOS (VNĐ)")
    st.plotly_chart(fig_ltv_ios, use_container_width=True)

# ==========================================
# ENGINE CALCULATION FOR 2 PLATFORMS (CONSOLIDATED)
# ==========================================
def calculate_single_platform_rev(df_traffic, df_ltv):
    num_months = len(df_traffic)
    ltv_mapping = {}
    for _, row in df_ltv.iterrows():
        try:
            anchors = {int(c[1:]): float(row[c]) for c in ALL_D_COLS if c in row}
            curve = create_daily_ltv_curve(anchors)
            if row['Áp dụng từ Tháng'] in df_traffic['Tháng'].values:
                ltv_mapping[row['Áp dụng từ Tháng']] = curve
        except: pass
        
    latest_curve = np.zeros(721)
    month_curves = []
    for m in df_traffic['Tháng']:
        if m in ltv_mapping: latest_curve = ltv_mapping[m]
        month_curves.append(latest_curve)
        
    daily_nru_list, daily_curve_list = [], []
    for m_idx, row in df_traffic.iterrows():
        nru_daily = float(row['NRU']) / 30.0
        for d in range(30):
            daily_nru_list.append(nru_daily)
            daily_curve_list.append(month_curves[m_idx])
            
    total_days = len(daily_nru_list)
    daily_rev = np.zeros(total_days)
    for c_day in range(total_days):
        c_nru = daily_nru_list[c_day]
        if c_nru <= 0: continue
        c_curve = daily_curve_list[c_day]
        inc_ltv = np.diff(np.insert(c_curve, 0, 0))[1:]
        for age in range(min(len(inc_ltv), total_days - c_day)):
            daily_rev[c_day + age] += c_nru * inc_ltv[age]
            
    return np.array([np.sum(daily_rev[i*30:(i+1)*30]) for i in range(num_months)])

def calculate_consolidated_pnl(df_tr_adr, df_tr_ios, df_ltv_adr, df_ltv_ios, params):
    res = pd.DataFrame()
    res['Tháng'] = df_tr_adr['Tháng']
    
    # 1. Traffic & Marketing
    nru_adr = pd.to_numeric(df_tr_adr['NRU'], errors='coerce').fillna(0.0)
    cpn_adr = pd.to_numeric(df_tr_adr['CPN (VNĐ)'], errors='coerce').fillna(0.0)
    mkt_adr = nru_adr * cpn_adr
    
    nru_ios = pd.to_numeric(df_tr_ios['NRU'], errors='coerce').fillna(0.0)
    cpn_ios = pd.to_numeric(df_tr_ios['CPN (VNĐ)'], errors='coerce').fillna(0.0)
    mkt_ios = nru_ios * cpn_ios
    
    res['NRU'] = nru_adr + nru_ios
    res['Marketing (UA+Tax)'] = mkt_adr + mkt_ios
    res['Cost per User'] = np.where(res['NRU'] > 0, res['Marketing (UA+Tax)'] / res['NRU'], 0.0)
    
    # 2. Revenue Cohort 2 hệ
    rev_adr = calculate_single_platform_rev(df_tr_adr, df_ltv_adr)
    rev_ios = calculate_single_platform_rev(df_tr_ios, df_ltv_ios)
    res['Revenue'] = rev_adr + rev_ios
    
    # 3. OPEX
    res['Nhân sự (VNĐ)'] = pd.to_numeric(df_tr_adr['Nhân sự (VNĐ)'], errors='coerce').fillna(0.0)
    res['Server (VNĐ)'] = pd.to_numeric(df_tr_adr['Server (VNĐ)'], errors='coerce').fillna(0.0)
    res['LF + Branding (VNĐ)'] = pd.to_numeric(df_tr_adr['LF + Branding (VNĐ)'], errors='coerce').fillna(0.0)
    
    res['Revenue share dev'] = res['Revenue'] * (params['rev_share'] / 100.0)
    res['VAT'] = res['Revenue'] * (params['vat'] / 100.0)
    res['Payment channel fee'] = res['Revenue'] * (params['payment_fee'] / 100.0)
    
    res['Tổng Chi Phí'] = (
        res['Marketing (UA+Tax)'] + res['Nhân sự (VNĐ)'] + res['Server (VNĐ)'] +
        res['LF + Branding (VNĐ)'] + res['Revenue share dev'] + res['VAT'] + res['Payment channel fee']
    )
    
    res['Lợi nhuận tháng'] = res['Revenue'] - res['Tổng Chi Phí']
    res['Lợi Nhuận'] = res['Lợi nhuận tháng'].cumsum()
    res['Tỷ Trọng MKT/REV'] = np.where(res['Revenue'] > 0, res['Marketing (UA+Tax)'] / res['Revenue'], 0.0)
    
    return res

def format_cell_value(val, is_pct=False):
    if pd.isna(val) or val == 0: return "0"
    if is_pct: return f"{val*100:.2f}%"
    return f"{val:,.0f}"

# ==========================================
# TAB 5: BÁO CÁO P&L TỔNG HỢP & LƯU GOOGLE SHEET
# ==========================================
with tab_pnl_total:
    st.markdown(f'<div class="section-title">5. Báo Cáo P&L Tổng Hợp (Consolidated) - {cur_proj}</div>', unsafe_allow_html=True)
    
    col_btn1, col_btn2 = st.columns([1, 2])
    run_sim = col_btn1.button(f"🚀 Chạy Mô Phỏng Tổng ({cur_proj})", type="primary")
    
    if run_sim or f"pnl_res_{cur_proj}" in st.session_state:
        with st.spinner(f"Đang tính toán ma trận Cohort 2 hệ (Android + iOS)..."):
            res = calculate_consolidated_pnl(edited_tr_adr, edited_tr_ios, edited_ltv_adr, edited_ltv_ios, st.session_state[f"params_{cur_proj}"])
            st.session_state[f"pnl_res_{cur_proj}"] = res
            
            total_nru = res['NRU'].sum()
            total_mkt = res['Marketing (UA+Tax)'].sum()
            cpu_total = total_mkt / total_nru if total_nru > 0 else 0
            
            # --- ĐỒNG BỘ 5 BẢNG VÀO GOOGLE SHEET ---
            if col_btn2.button("☁️ Lưu Toàn Bộ 5 Bảng Vào Google Sheet"):
                try:
                    with st.spinner("Đang lưu dữ liệu 2 hệ và P&L Tổng sang Google Spreadsheet..."):
                        tr_adr_rows = [edited_tr_adr.columns.tolist()] + edited_tr_adr.fillna("").values.tolist()
                        tr_ios_rows = [edited_tr_ios.columns.tolist()] + edited_tr_ios.fillna("").values.tolist()
                        
                        k_adr_full = edited_ltv_adr.copy()
                        for c in ALL_D_COLS: k_adr_full[c] = pd.to_numeric(k_adr_full[c], errors="coerce").fillna(0.0)
                        k_adr_full['K1'] = np.where(k_adr_full['D1'] > 0, 1.0, 0.0)
                        for d in ALL_D_TARGETS: k_adr_full[f'K{d}'] = np.where(k_adr_full['D1'] > 0, k_adr_full[f'D{d}'] / k_adr_full['D1'], 0.0)
                        ltv_adr_rows = [k_adr_full.columns.tolist()] + k_adr_full.fillna("").values.tolist()

                        k_ios_full = edited_ltv_ios.copy()
                        for c in ALL_D_COLS: k_ios_full[c] = pd.to_numeric(k_ios_full[c], errors="coerce").fillna(0.0)
                        k_ios_full['K1'] = np.where(k_ios_full['D1'] > 0, 1.0, 0.0)
                        for d in ALL_D_TARGETS: k_ios_full[f'K{d}'] = np.where(k_ios_full['D1'] > 0, k_ios_full[f'D{d}'] / k_ios_full['D1'], 0.0)
                        ltv_ios_rows = [k_ios_full.columns.tolist()] + k_ios_full.fillna("").values.tolist()

                        months = list(res['Tháng'])
                        pnl_rows = []
                        pnl_rows.append(["Dashboard", "Total"] + months)
                        pnl_rows.append(["", "KPI"] + ["KPI"] * len(months))
                        pnl_rows.append(["New Registed User", float(total_nru)] + list(res['NRU'].astype(float)))
                        pnl_rows.append(["Cost per User", float(cpu_total)] + list(res['Cost per User'].astype(float)))
                        pnl_rows.append(["Revenue", float(res["Revenue"].sum())] + list(res['Revenue'].astype(float)))
                        pnl_rows.append(["Spent", ""] + [""] * len(months))
                        
                        opex_items = [
                            ('Personel', 'Nhân sự (VNĐ)'), ('Server', 'Server (VNĐ)'),
                            ('Marketing (UA+Tax)', 'Marketing (UA+Tax)'), ('LF + Branding', 'LF + Branding (VNĐ)'),
                            ('Revenue share dev', 'Revenue share dev'), ('VAT', 'VAT'),
                            ('Payment channel fee', 'Payment channel fee')
                        ]
                        for label, col in opex_items:
                            pnl_rows.append([label, float(res[col].sum())] + list(res[col].astype(float)))
                            
                        pnl_rows.append(["Tổng Chi Phí", float(res["Tổng Chi Phí"].sum())] + list(res['Tổng Chi Phí'].astype(float)))
                        pnl_rows.append(["Lợi nhuận tháng", ""] + list(res['Lợi nhuận tháng'].astype(float)))
                        pnl_rows.append(["Lợi Nhuận", float(res['Lợi Nhuận'].iloc[-1])] + list(res['Lợi Nhuận'].astype(float)))
                        avg_mkt_rev = total_mkt / res["Revenue"].sum() if res["Revenue"].sum() > 0 else 0
                        pnl_rows.append(["Tỷ Trọng MKT/REV", f"{avg_mkt_rev*100:.2f}%"] + [f"{v*100:.2f}%" for v in res['Tỷ Trọng MKT/REV']])

                        all_projects_payload = {
                            "project_names": st.session_state.project_names,
                            "current_project": st.session_state.current_project,
                            "projects_data": {}
                        }
                        for p in st.session_state.project_names:
                            all_projects_payload["projects_data"][p] = {
                                "traffic_android": st.session_state.get(f"traffic_android_{p}", get_default_traffic(25, True)).to_dict(orient="records"),
                                "traffic_ios": st.session_state.get(f"traffic_ios_{p}", get_default_traffic(25, False)).to_dict(orient="records"),
                                "ltv_android": st.session_state.get(f"ltv_android_{p}", get_default_ltv(True)).to_dict(orient="records"),
                                "ltv_ios": st.session_state.get(f"ltv_ios_{p}", get_default_ltv(False)).to_dict(orient="records"),
                                "params": st.session_state.get(f"params_{p}", {"rev_share": 20.2, "vat": 10.0, "payment_fee": 5.0})
                            }

                        payload = {
                            "project_name": cur_proj,
                            "traffic_android": tr_adr_rows,
                            "traffic_ios": tr_ios_rows,
                            "ltv_android": ltv_adr_rows,
                            "ltv_ios": ltv_ios_rows,
                            "pnl_rows": pnl_rows,
                            "all_projects_payload": all_projects_payload
                        }
                        
                        resp = requests.post(GOOGLE_SCRIPT_URL, data=json.dumps(payload), timeout=25)
                        if resp.status_code == 200:
                            st.success(f"🎉 Đã lưu toàn bộ 5 bảng của '{cur_proj}' sang Google Sheet thành công!")
                        else:
                            st.error(f"Lỗi Webhook: {resp.text}")
                except Exception as ex:
                    st.error(f"Lỗi: {ex}")

            # Hiển thị bảng P&L HTML
            html = '<div class="dataframe-container"><table class="custom-pnl">'
            html += '<tr><th>Dashboard</th><th>Total</th>'
            for m in res['Tháng']: html += f'<th>{m}</th>'
            html += '</tr>'
            
            html += '<tr><td></td><td>KPI</td>'
            for _ in res['Tháng']: html += '<td>KPI</td>'
            html += '</tr>'
            
            html += f'<tr class="row-nru"><td>New Registed User</td><td>{format_cell_value(total_nru)}</td>'
            for v in res['NRU']: html += f'<td>{format_cell_value(v)}</td>'
            html += '</tr>'
            
            html += f'<tr class="row-cost"><td>Cost per User</td><td>{format_cell_value(cpu_total)}</td>'
            for v in res['Cost per User']: html += f'<td>{format_cell_value(v)}</td>'
            html += '</tr>'
            
            html += f'<tr class="row-rev-total"><td>Revenue</td><td>{format_cell_value(res["Revenue"].sum())}</td>'
            for v in res['Revenue']: html += f'<td>{format_cell_value(v)}</td>'
            html += '</tr>'
            
            html += '<tr class="row-spent-header"><td>Spent</td><td></td>' + '<td></td>'*len(res) + '</tr>'
            
            opex_rows = [
                ('Personel', 'Nhân sự (VNĐ)'), ('Server', 'Server (VNĐ)'),
                ('Marketing (UA+Tax)', 'Marketing (UA+Tax)'), ('LF + Branding', 'LF + Branding (VNĐ)'),
                ('Revenue share dev', 'Revenue share dev'), ('VAT', 'VAT'),
                ('Payment channel fee', 'Payment channel fee')
            ]
            for label, col in opex_rows:
                html += f'<tr class="row-opex"><td>{label}</td><td>{format_cell_value(res[col].sum())}</td>'
                for v in res[col]: html += f'<td>{format_cell_value(v)}</td>'
                html += '</tr>'
                
            html += f'<tr class="row-total-cost"><td>Tổng Chi Phí</td><td>{format_cell_value(res["Tổng Chi Phí"].sum())}</td>'
            for v in res['Tổng Chi Phí']: html += f'<td>{format_cell_value(v)}</td>'
            html += '</tr>'
            
            html += '<tr class="row-profit-month"><td>Lợi nhuận tháng</td><td></td>'
            for v in res['Lợi nhuận tháng']: 
                cls = "positive" if v > 0 else ""
                html += f'<td class="{cls}">{format_cell_value(v)}</td>'
            html += '</tr>'
            
            total_profit = res['Lợi Nhuận'].iloc[-1]
            html += f'<tr class="row-profit-cum"><td>Lợi Nhuận</td><td>{format_cell_value(total_profit)}</td>'
            for v in res['Lợi Nhuận']: 
                cls = "positive" if v > 0 else ""
                html += f'<td class="{cls}">{format_cell_value(v)}</td>'
            html += '</tr>'
            
            avg_mkt_rev = total_mkt / res["Revenue"].sum() if res["Revenue"].sum() > 0 else 0
            html += f'<tr class="row-roi"><td>Tỷ Trọng MKT/REV</td><td>{format_cell_value(avg_mkt_rev, True)}</td>'
            for v in res['Tỷ Trọng MKT/REV']: html += f'<td>{format_cell_value(v, True)}</td>'
            html += '</tr>'
            
            html += '</table></div>'
            st.markdown(html, unsafe_allow_html=True)
            
            out_buffer = io.BytesIO()
            res.to_excel(out_buffer, index=False, engine='openpyxl')
            out_buffer.seek(0)
            st.download_button(f"📥 Tải File P&L Tổng - {cur_proj}", data=out_buffer, file_name=f"Game_Forecast_Total_{cur_proj}.xlsx")
    else:
        st.info("💡 Bấm nút **Chạy Mô Phỏng Tổng** để tính toán hợp nhất doanh thu 2 hệ và lưu sang Google Sheet.")
