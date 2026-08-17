import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import io

st.set_page_config(page_title="Game P&L Forecast Pro - Hoàng Thành Long", layout="wide", page_icon="🎮")

st.title("🎮 Hệ Thống Dự Phóng P&L by Hoàng Thành Long (VplayHN)")

# ==========================================
# CUSTOM CSS FOR EXCEL-LIKE TABLE
# ==========================================
st.markdown("""
<style>
    .section-title { font-size: 18px; font-weight: 600; color: #1E293B; margin-top: 10px; margin-bottom: 8px; }
    .dataframe-container { overflow-x: auto; margin-bottom: 20px; }
    table.custom-pnl { width: 100%; border-collapse: collapse; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 13px; color: #E2E8F0; background-color: #0F172A; }
    table.custom-pnl th { background-color: #0B3E45; color: white; font-weight: bold; text-align: center; padding: 8px 5px; border: 1px solid #1E293B; min-width: 100px; }
    table.custom-pnl th:first-child { background-color: #002B36; text-align: left; min-width: 200px; position: sticky; left: 0; z-index: 10; }
    table.custom-pnl td { padding: 6px 8px; text-align: right; border: 1px solid #334155; }
    table.custom-pnl td:first-child { text-align: left; font-weight: 500; position: sticky; left: 0; background-color: #0F172A; z-index: 9; border-right: 2px solid #475569; }
    
    table.custom-pnl tr.row-nru td { background-color: #F59E0B; color: black; font-weight: bold; }
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
</style>
""", unsafe_allow_html=True)

# ==========================================
# KHỞI TẠO DỮ LIỆU
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

def get_default_ob_daily(total_ob_nru, default_cpn):
    weights = np.zeros(30)
    weights[0] = 0.25
    weights[1] = 0.15
    weights[2] = 0.10
    weights[3:7] = 0.05
    weights[7:30] = 0.30 / 23
    nru_days = np.round(weights * total_ob_nru).astype(int)
    diff = total_ob_nru - np.sum(nru_days)
    nru_days[0] += diff
    return pd.DataFrame({
        "Ngày": [f"Day {i+1}" for i in range(30)],
        "NRU (Users)": nru_days,
        "CPN (VNĐ)": [default_cpn] * 30
    })

ALL_D_COLS = ["D1", "D3", "D7", "D14", "D30", "D60", "D90", "D180", "D210", "D240", "D270", "D300", "D330", "D360"]
ALL_D_TARGETS = [3, 7, 14, 30, 60, 90, 180, 210, 240, 270, 300, 330, 360]

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

def get_default_ltv(is_android=True):
    if is_android:
        return pd.DataFrame({
            "Phase Name": ["Phase 1 (Tháng OB)", "Phase 2 (Tháng 2&3)", "Phase 3 (Tháng 4+)"],
            "Áp dụng từ Tháng": ["Month OB", "Month OB+1", "Month OB+3"],
            "D1": [9000, 7000, 4500], "D3": [13500, 10500, 7000], "D7": [27000, 22000, 13000],
            "D14": [40000, 33000, 22000], "D30": [54000, 44000, 30000], "D60": [72000, 57000, 35000],
            "D90": [85000, 66000, 40000], "D180": [108000, 80000, 45000], "D210": [112000, 83000, 46000],
            "D240": [116000, 86000, 47000], "D270": [120000, 89000, 48000], "D300": [124000, 92000, 49000],
            "D330": [128000, 95000, 50000], "D360": [132000, 98000, 51000]
        })
    else:
        return pd.DataFrame({
            "Phase Name": ["Phase 1 (Tháng OB)", "Phase 2 (Tháng 2&3)", "Phase 3 (Tháng 4+)"],
            "Áp dụng từ Tháng": ["Month OB", "Month OB+1", "Month OB+3"],
            "D1": [12000, 10000, 6000], "D3": [18000, 15000, 10000], "D7": [36000, 31000, 19000],
            "D14": [55000, 48000, 31000], "D30": [72000, 62000, 45000], "D60": [96000, 81000, 50000],
            "D90": [115000, 93000, 55000], "D180": [144000, 110000, 60000], "D210": [150000, 113000, 61000],
            "D240": [156000, 116000, 62000], "D270": [162000, 119000, 63000], "D300": [168000, 122000, 64000],
            "D330": [174000, 125000, 65000], "D360": [180000, 128000, 66000]
        })

if "project_names" not in st.session_state:
    st.session_state.project_names = ["Dự án 1 (T029)", "T037"]
    st.session_state.current_project = "T037"

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.header("📁 Quản Lý Dự Án")
    selected_proj = st.selectbox("Chọn dự án:", st.session_state.project_names, index=st.session_state.project_names.index(st.session_state.current_project))
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
                st.session_state[f"ob_daily_adr_{new_proj_name}"] = get_default_ob_daily(100000, 25000)
                st.session_state[f"ob_daily_ios_{new_proj_name}"] = get_default_ob_daily(50000, 32000)
                st.session_state[f"ltv_android_{new_proj_name}"] = get_default_ltv(True)
                st.session_state[f"ltv_ios_{new_proj_name}"] = get_default_ltv(False)
                st.session_state[f"params_{new_proj_name}"] = {"rev_share": 20.2, "vat": 10.0, "payment_fee": 5.0}
                st.session_state.current_project = new_proj_name
                st.rerun()

    st.markdown("---")
    st.header("📤 Tải Lên Dữ Liệu (Excel)")
    uploaded_file = st.file_uploader("Upload file PNL_*.xlsx", type=["xlsx"])
    if uploaded_file is not None:
        try:
            excel_data = pd.ExcelFile(uploaded_file)
            imported_proj_name = uploaded_file.name.replace("PNL_", "").replace(".xlsx", "")
            if imported_proj_name not in st.session_state.project_names:
                st.session_state.project_names.append(imported_proj_name)
            
            if 'Traffic Android' in excel_data.sheet_names:
                st.session_state[f"traffic_android_{imported_proj_name}"] = pd.read_excel(excel_data, sheet_name='Traffic Android')
            if 'Traffic iOS' in excel_data.sheet_names:
                st.session_state[f"traffic_ios_{imported_proj_name}"] = pd.read_excel(excel_data, sheet_name='Traffic iOS')
            if 'LTV Android' in excel_data.sheet_names:
                st.session_state[f"ltv_android_{imported_proj_name}"] = pd.read_excel(excel_data, sheet_name='LTV Android')
            if 'LTV iOS' in excel_data.sheet_names:
                st.session_state[f"ltv_ios_{imported_proj_name}"] = pd.read_excel(excel_data, sheet_name='LTV iOS')
                
            st.session_state.current_project = imported_proj_name
            st.success(f"Đã nạp thành công dự án '{imported_proj_name}' từ file Excel!")
            st.rerun()
        except Exception as e:
            st.error(f"Lỗi đọc file Excel: {e}")

    st.markdown("---")
    st.header("💸 Cấu Hình Chi Phí (%)")
    if f"params_{cur_proj}" not in st.session_state:
        st.session_state[f"params_{cur_proj}"] = {"rev_share": 20.2, "vat": 10.0, "payment_fee": 5.0}
    p_params = st.session_state[f"params_{cur_proj}"]
    rev_share_pct = st.number_input("Revenue Share Dev (%)", value=float(p_params["rev_share"]), step=0.1)
    vat_pct = st.number_input("VAT (%)", value=float(p_params["vat"]), step=0.5)
    payment_fee_pct = st.number_input("Payment Fee (%)", value=float(p_params["payment_fee"]), step=0.5)
    st.session_state[f"params_{cur_proj}"] = {"rev_share": rev_share_pct, "vat": vat_pct, "payment_fee": payment_fee_pct}

# State init
if f"traffic_android_{cur_proj}" not in st.session_state: st.session_state[f"traffic_android_{cur_proj}"] = get_default_traffic(25, True)
if f"traffic_ios_{cur_proj}" not in st.session_state: st.session_state[f"traffic_ios_{cur_proj}"] = get_default_traffic(25, False)
if f"ob_daily_adr_{cur_proj}" not in st.session_state: st.session_state[f"ob_daily_adr_{cur_proj}"] = get_default_ob_daily(100000, 25000)
if f"ob_daily_ios_{cur_proj}" not in st.session_state: st.session_state[f"ob_daily_ios_{cur_proj}"] = get_default_ob_daily(50000, 32000)
if f"ltv_android_{cur_proj}" not in st.session_state: st.session_state[f"ltv_android_{cur_proj}"] = get_default_ltv(True)
if f"ltv_ios_{cur_proj}" not in st.session_state: st.session_state[f"ltv_ios_{cur_proj}"] = get_default_ltv(False)

# ==========================================
# TABS HIỂN THỊ
# ==========================================
tabs_to_show = ["🤖 1. Traffic Android", "🍎 2. Traffic iOS", "📈 3. LTV Android", "🍏 4. LTV iOS", "📊 5. Báo Cáo P&L Tổng Hợp"]
rendered_tabs = st.tabs(tabs_to_show)

# TAB 1: ANDROID
with rendered_tabs[0]:
    st.markdown(f'<div class="section-title">1. Kế Hoạch Traffic Tháng & Định Phí - ANDROID ({cur_proj})</div>', unsafe_allow_html=True)
    edited_tr_adr = st.data_editor(
        st.session_state[f"traffic_android_{cur_proj}"],
        num_rows="dynamic",
        use_container_width=True, hide_index=True, key=f"ed_tr_adr_{cur_proj}",
        column_config={
            "NRU": st.column_config.NumberColumn("NRU Android", format="%d", min_value=0),
            "CPN (VNĐ)": st.column_config.NumberColumn("CPN Android (VNĐ)", format="%d", min_value=0),
            "Nhân sự (VNĐ)": st.column_config.NumberColumn("Nhân sự (VNĐ)", format="%d", min_value=0),
            "Server (VNĐ)": st.column_config.NumberColumn("Server (VNĐ)", format="%d", min_value=0),
            "LF + Branding (VNĐ)": st.column_config.NumberColumn("LF + Branding (VNĐ)", format="%d", min_value=0)
        }
    )
    st.session_state[f"traffic_android_{cur_proj}"] = edited_tr_adr
    
    with st.expander("📅 Chi Tiết Phân Bổ 30 Ngày Tháng OPEN BETA (Android) - [Tùy Chỉnh Lệch Đầu / Launch Curve]", expanded=False):
        st.caption("👉 Điền chính xác số lượng **NRU** và **CPN** cho từng ngày (Day 1 → Day 30) của tháng Open Beta.")
        c1, c2, c3 = st.columns([1.5, 1.5, 3])
        if c1.button("⚡ Phân bổ dồn đầu (50-20-30)", key="btn_apply_dist_adr"):
            ob_total_target = float(edited_tr_adr.loc[edited_tr_adr["Tháng"] == "Month OB", "NRU"].values[0]) if "Month OB" in edited_tr_adr["Tháng"].values else 100000
            ob_cpn_target = float(edited_tr_adr.loc[edited_tr_adr["Tháng"] == "Month OB", "CPN (VNĐ)"].values[0]) if "Month OB" in edited_tr_adr["Tháng"].values else 25000
            st.session_state[f"ob_daily_adr_{cur_proj}"] = get_default_ob_daily(int(ob_total_target), int(ob_cpn_target))
            st.rerun()
        edited_ob_adr = st.data_editor(
            st.session_state[f"ob_daily_adr_{cur_proj}"],
            num_rows="fixed",
            use_container_width=True, hide_index=True, key=f"ed_ob_adr_{cur_proj}",
            column_config={"NRU (Users)": st.column_config.NumberColumn("NRU (Users)", format="%d", min_value=0), "CPN (VNĐ)": st.column_config.NumberColumn("CPN (VNĐ)", format="%d", min_value=0)}
        )
        st.session_state[f"ob_daily_adr_{cur_proj}"] = edited_ob_adr

# TAB 2: IOS
with rendered_tabs[1]:
    st.markdown(f'<div class="section-title">2. Kế Hoạch Traffic Tháng - iOS ({cur_proj})</div>', unsafe_allow_html=True)
    edited_tr_ios = st.data_editor(
        st.session_state[f"traffic_ios_{cur_proj}"],
        num_rows="dynamic",
        use_container_width=True, hide_index=True, key=f"ed_tr_ios_{cur_proj}",
        column_config={
            "NRU": st.column_config.NumberColumn("NRU iOS", format="%d", min_value=0),
            "CPN (VNĐ)": st.column_config.NumberColumn("CPN iOS (VNĐ)", format="%d", min_value=0)
        }
    )
    st.session_state[f"traffic_ios_{cur_proj}"] = edited_tr_ios
    
    with st.expander("📅 Chi Tiết Phân Bổ 30 Ngày Tháng OPEN BETA (iOS) - [Tùy Chỉnh Lệch Đầu / Launch Curve]", expanded=False):
        st.caption("👉 Điền chính xác số lượng **NRU** và **CPN** cho từng ngày (Day 1 → Day 30) của tháng Open Beta cho hệ iOS.")
        c1, c2, c3 = st.columns([1.5, 1.5, 3])
        if c1.button("⚡ Phân bổ dồn đầu (50-20-30)", key="btn_apply_dist_ios"):
            ob_total_target_ios = float(edited_tr_ios.loc[edited_tr_ios["Tháng"] == "Month OB", "NRU"].values[0]) if "Month OB" in edited_tr_ios["Tháng"].values else 50000
            ob_cpn_target_ios = float(edited_tr_ios.loc[edited_tr_ios["Tháng"] == "Month OB", "CPN (VNĐ)"].values[0]) if "Month OB" in edited_tr_ios["Tháng"].values else 32000
            st.session_state[f"ob_daily_ios_{cur_proj}"] = get_default_ob_daily(int(ob_total_target_ios), int(ob_cpn_target_ios))
            st.rerun()
        edited_ob_ios = st.data_editor(
            st.session_state[f"ob_daily_ios_{cur_proj}"],
            num_rows="fixed",
            use_container_width=True, hide_index=True, key=f"ed_ob_ios_{cur_proj}",
            column_config={"NRU (Users)": st.column_config.NumberColumn("NRU (Users)", format="%d", min_value=0), "CPN (VNĐ)": st.column_config.NumberColumn("CPN (VNĐ)", format="%d", min_value=0)}
        )
        st.session_state[f"ob_daily_ios_{cur_proj}"] = edited_ob_ios

# TAB 3: LTV ANDROID
with rendered_tabs[2]:
    st.markdown(f'<div class="section-title">3. Cấu Hình LTV Curve & Hệ Số K - ANDROID ({cur_proj})</div>', unsafe_allow_html=True)
    month_options = st.session_state[f"traffic_android_{cur_proj}"]["Tháng"].tolist()
    col_cfg_adr = {"Áp dụng từ Tháng": st.column_config.SelectboxColumn("Áp dụng từ Tháng", options=month_options)}
    for c in ALL_D_COLS: col_cfg_adr[c] = st.column_config.NumberColumn(f"{c} (VNĐ)", format="%d", min_value=0)
    
    edited_ltv_adr = st.data_editor(
        st.session_state[f"ltv_android_{cur_proj}"],
        num_rows="dynamic",
        use_container_width=True, hide_index=True, column_config=col_cfg_adr, key=f"ed_ltv_adr_{cur_proj}"
    )
    st.session_state[f"ltv_android_{cur_proj}"] = edited_ltv_adr
    
    k_adr_df = edited_ltv_adr.copy()
    for c in ALL_D_COLS: k_adr_df[c] = pd.to_numeric(k_adr_df[c], errors="coerce").fillna(0.0)
    k_adr_df['K1'] = np.where(k_adr_df['D1'] > 0, 1.0, 0.0)
    for d in ALL_D_TARGETS: k_adr_df[f'K{d}'] = np.where(k_adr_df['D1'] > 0, k_adr_df[f'D{d}'] / k_adr_df['D1'], 0.0)
    st.dataframe(k_adr_df[["Phase Name", "Áp dụng từ Tháng", "K1"] + [f'K{d}' for d in ALL_D_TARGETS]].style.format({f'K{d}': "{:.2f}x" for d in [1] + ALL_D_TARGETS}), use_container_width=True, hide_index=True)

# TAB 4: LTV IOS
with rendered_tabs[3]:
    st.markdown(f'<div class="section-title">4. Cấu Hình LTV Curve & Hệ Số K - iOS ({cur_proj})</div>', unsafe_allow_html=True)
    month_options = st.session_state[f"traffic_android_{cur_proj}"]["Tháng"].tolist()
    col_cfg_ios = {"Áp dụng từ Tháng": st.column_config.SelectboxColumn("Áp dụng từ Tháng", options=month_options)}
    for c in ALL_D_COLS: col_cfg_ios[c] = st.column_config.NumberColumn(f"{c} (VNĐ)", format="%d", min_value=0)
    
    edited_ltv_ios = st.data_editor(
        st.session_state[f"ltv_ios_{cur_proj}"],
        num_rows="dynamic",
        use_container_width=True, hide_index=True, column_config=col_cfg_ios, key=f"ed_ltv_ios_{cur_proj}"
    )
    st.session_state[f"ltv_ios_{cur_proj}"] = edited_ltv_ios
    
    k_ios_df = edited_ltv_ios.copy()
    for c in ALL_D_COLS: k_ios_df[c] = pd.to_numeric(k_ios_df[c], errors="coerce").fillna(0.0)
    k_ios_df['K1'] = np.where(k_ios_df['D1'] > 0, 1.0, 0.0)
    for d in ALL_D_TARGETS: k_ios_df[f'K{d}'] = np.where(k_ios_df['D1'] > 0, k_ios_df[f'D{d}'] / k_ios_df['D1'], 0.0)
    st.dataframe(k_ios_df[["Phase Name", "Áp dụng từ Tháng", "K1"] + [f'K{d}' for d in ALL_D_TARGETS]].style.format({f'K{d}': "{:.2f}x" for d in [1] + ALL_D_TARGETS}), use_container_width=True, hide_index=True)

# ==========================================
# ENGINE CALCULATION (PHASE MAPPING + DAILY OB TRAFFIC)
# ==========================================
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

def calculate_platform_rev_phase_mapping(df_traffic, df_ob_daily, df_ltv):
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
    active_curve = latest_curve
    month_curves = []
    for m in df_traffic['Tháng']:
        if m in ltv_mapping:
            active_curve = ltv_mapping[m]
        month_curves.append(active_curve)
        
    daily_nru_list = []
    daily_curve_list = []
    
    for m_idx, row in df_traffic.iterrows():
        month_label = row['Tháng']
        if month_label == "Month OB":
            ob_nrus = df_ob_daily["NRU (Users)"].astype(float).values
            for d in range(30):
                daily_nru_list.append(ob_nrus[d] if d < len(ob_nrus) else 0.0)
                daily_curve_list.append(month_curves[m_idx])
        else:
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

def format_cell_value(val, is_pct=False):
    if pd.isna(val) or val == 0: return "0"
    if is_pct: return f"{val*100:.2f}%"
    return f"{val:,.0f}"

# TAB 5: BÁO CÁO P&L TỔNG HỢP
with rendered_tabs[4]:
    st.markdown(f'<div class="section-title">5. Báo Cáo P&L Tổng Hợp (Consolidated) - {cur_proj}</div>', unsafe_allow_html=True)
    
    tr_adr = st.session_state[f"traffic_android_{cur_proj}"]
    tr_ios = st.session_state[f"traffic_ios_{cur_proj}"]
    ob_adr = st.session_state[f"ob_daily_adr_{cur_proj}"]
    ob_ios = st.session_state[f"ob_daily_ios_{cur_proj}"]
    ltv_adr = st.session_state[f"ltv_android_{cur_proj}"]
    ltv_ios = st.session_state[f"ltv_ios_{cur_proj}"]
    params = st.session_state.get(f"params_{cur_proj}", {"rev_share": 20.2, "vat": 10.0, "payment_fee": 5.0})
    
    run_sim = st.button(f"🚀 Chạy Mô Phỏng Tổng ({cur_proj})", type="primary")
    
    if run_sim or f"pnl_res_{cur_proj}" in st.session_state:
        with st.spinner("Đang tính ma trận Cohort hợp nhất..."):
            res = pd.DataFrame()
            res['Tháng'] = tr_adr['Tháng']
            
            nru_adr_list, mkt_adr_list = [], []
            for _, r in tr_adr.iterrows():
                if r['Tháng'] == "Month OB":
                    nru_adr_list.append(ob_adr["NRU (Users)"].sum())
                    mkt_adr_list.append((ob_adr["NRU (Users)"] * ob_adr["CPN (VNĐ)"]).sum())
                else:
                    u = float(r['NRU'])
                    nru_adr_list.append(u)
                    mkt_adr_list.append(u * float(r['CPN (VNĐ)']))
                    
            nru_ios_list, mkt_ios_list = [], []
            for _, r in tr_ios.iterrows():
                if r['Tháng'] == "Month OB":
                    nru_ios_list.append(ob_ios["NRU (Users)"].sum())
                    mkt_ios_list.append((ob_ios["NRU (Users)"] * ob_ios["CPN (VNĐ)"]).sum())
                else:
                    u = float(r['NRU'])
                    nru_ios_list.append(u)
                    mkt_ios_list.append(u * float(r['CPN (VNĐ)']))
                    
            res['NRU'] = np.array(nru_adr_list) + np.array(nru_ios_list)
            res['Marketing (UA+Tax)'] = np.array(mkt_adr_list) + np.array(mkt_ios_list)
            res['Cost per User'] = np.where(res['NRU'] > 0, res['Marketing (UA+Tax)'] / res['NRU'], 0.0)
            
            rev_adr = calculate_platform_rev_phase_mapping(tr_adr, ob_adr, ltv_adr)
            rev_ios = calculate_platform_rev_phase_mapping(tr_ios, ob_ios, ltv_ios)
            res['Revenue'] = rev_adr + rev_ios
            
            res['Nhân sự (VNĐ)'] = pd.to_numeric(tr_adr['Nhân sự (VNĐ)'], errors='coerce').fillna(0.0)
            res['Server (VNĐ)'] = pd.to_numeric(tr_adr['Server (VNĐ)'], errors='coerce').fillna(0.0)
            res['LF + Branding (VNĐ)'] = pd.to_numeric(tr_adr['LF + Branding (VNĐ)'], errors='coerce').fillna(0.0)
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
            st.session_state[f"pnl_res_{cur_proj}"] = res
            
            total_nru = res['NRU'].sum()
            total_mkt = res['Marketing (UA+Tax)'].sum()
            cpu_total = total_mkt / total_nru if total_nru > 0 else 0
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                tr_adr.to_excel(writer, sheet_name='Traffic Android', index=False)
                tr_ios.to_excel(writer, sheet_name='Traffic iOS', index=False)
                ltv_adr.to_excel(writer, sheet_name='LTV Android', index=False)
                ltv_ios.to_excel(writer, sheet_name='LTV iOS', index=False)
                res.to_excel(writer, sheet_name='P&L Tong Hop', index=False)
            buffer.seek(0)
            
            st.download_button(
                label=f"📥 Tải File P&L Tổng - {cur_proj} (Gửi cho team)",
                data=buffer,
                file_name=f"PNL_{cur_proj}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
            # HTML Table Render matching Excel formatting style
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
