import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import io
import json
import requests

st.set_page_config(page_title="Game P&L Forecast Pro - Hoàng Thành Long", layout="wide", page_icon="🎮")

GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwNdEQThD8xUXDOEr397lTSLQdWrRd6u63KwC6P2U0G6qHOHWQhrj5uBpzN0yALWZI8Kw/exec"

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
def get_default_input(total_months=25):
    months_label = ["Pre-launch", "Month OB"] + [f"Month OB+{i}" for i in range(1, total_months - 1)]
    return pd.DataFrame({
        "Tháng": months_label,
        "NRU": [0, 150000] + [100000] * (total_months - 2),
        "CPN (VNĐ)": [0, 27000] + [27000] * (total_months - 2),
        "Nhân sự (VNĐ)": [400000000, 200000000] + [200000000] * (total_months - 2),
        "Server (VNĐ)": [0, 200000000] + [200000000] * (total_months - 2),
        "LF + Branding (VNĐ)": [675000000, 1800000000] + [50000000] * (total_months - 2)
    })

ALL_D_COLS = ["D1", "D3", "D7", "D14", "D30", "D60", "D90", "D180", "D210", "D240", "D270", "D300", "D330", "D360"]
ALL_D_TARGETS = [3, 7, 14, 30, 60, 90, 180, 210, 240, 270, 300, 330, 360]

def get_default_ltv():
    return pd.DataFrame({
        "Phase Name": ["Phase 1 (Tháng OB)", "Phase 2 (Tháng 2&3)", "Phase 3 (Tháng 4+)"],
        "Áp dụng từ Tháng": ["Month OB", "Month OB+1", "Month OB+3"],
        "D1": [10000, 8000, 5000],
        "D3": [15000, 12000, 8000],
        "D7": [30000, 25000, 15000],
        "D14": [45000, 38000, 25000],
        "D30": [60000, 50000, 35000],
        "D60": [80000, 65000, 40000],
        "D90": [95000, 75000, 45000],
        "D180": [120000, 90000, 50000],
        "D210": [125000, 93000, 51000],
        "D240": [130000, 96000, 52000],
        "D270": [135000, 99000, 53000],
        "D300": [140000, 102000, 54000],
        "D330": [145000, 105000, 55000],
        "D360": [150000, 108000, 56000]
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
                st.session_state[f"input_df_{new_proj_name}"] = get_default_input(new_proj_months)
                st.session_state[f"ltv_df_{new_proj_name}"] = get_default_ltv()
                st.session_state[f"params_{new_proj_name}"] = {"rev_share": 20.2, "vat": 10.0, "payment_fee": 5.0}
                st.session_state.current_project = new_proj_name
                st.rerun()
            elif new_proj_name in st.session_state.project_names:
                st.warning("Tên dự án đã tồn tại!")

    st.markdown("---")
    st.header("☁️ Đồng Bộ Máy Khác (Google Sheet)")
    
    if st.button("🔄 Kéo Toàn Bộ Dữ Liệu Từ Sheet Về", help="Bấm nút này khi bạn mở web trên máy mới để lấy lại tất cả dự án đã lưu."):
        with st.spinner("Đang tải toàn bộ dữ liệu từ Google Sheet..."):
            try:
                resp = requests.get(GOOGLE_SCRIPT_URL, timeout=20)
                data = resp.json()
                if "project_names" in data:
                    st.session_state.project_names = data["project_names"]
                    st.session_state.current_project = data["current_project"]
                    for p, p_val in data["projects_data"].items():
                        st.session_state[f"input_df_{p}"] = pd.DataFrame(p_val["input_df"])
                        st.session_state[f"ltv_df_{p}"] = pd.DataFrame(p_val["ltv_df"])
                        st.session_state[f"params_{p}"] = p_val["params"]
                    st.success("🎉 Đã khôi phục thành công toàn bộ dự án từ Google Sheet!")
                    st.rerun()
                else:
                    st.warning("Google Sheet chưa có bản sao lưu nào. Hãy bấm 'Lưu Toàn Bộ Dữ Liệu Vào Google Sheet' trước.")
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

# Khởi tạo state dữ liệu dự án
if f"input_df_{cur_proj}" not in st.session_state:
    st.session_state[f"input_df_{cur_proj}"] = get_default_input(25)
if f"ltv_df_{cur_proj}" not in st.session_state:
    st.session_state[f"ltv_df_{cur_proj}"] = get_default_ltv()

for col_d in ALL_D_COLS:
    if col_d not in st.session_state[f"ltv_df_{cur_proj}"].columns:
        last_val = st.session_state[f"ltv_df_{cur_proj}"]["D180"] if "D180" in st.session_state[f"ltv_df_{cur_proj}"].columns else 50000
        st.session_state[f"ltv_df_{cur_proj}"][col_d] = last_val

tab_input, tab_ltv, tab_report = st.tabs(["📋 1. Kế hoạch Traffic & Định Phí", "📈 2. Đường LTV Curve & Hệ Số K", "📊 3. Báo Cáo P&L Tổng"])

# ==========================================
# TAB 1: KẾ HOẠCH TRAFFIC & ĐỊNH PHÍ
# ==========================================
with tab_input:
    st.markdown(f'<div class="section-title">1. Nhập Kế Hoạch NRU & CPN - {cur_proj}</div>', unsafe_allow_html=True)
    st.caption("👉 Điền số lượng **NRU** và đơn giá **CPN (Cost per NRU)**. Ngân sách Marketing sẽ được tính tự động $= CPN \\times NRU$ bên dưới.")
    
    input_base_df = st.session_state[f"input_df_{cur_proj}"].copy()
    if "CPN (VNĐ)" not in input_base_df.columns:
        if "Marketing Budget (VNĐ)" in input_base_df.columns:
            input_base_df["CPN (VNĐ)"] = np.where(input_base_df["NRU"] > 0, input_base_df["Marketing Budget (VNĐ)"] / input_base_df["NRU"], 27000.0)
        else:
            input_base_df["CPN (VNĐ)"] = 27000.0
            
    input_cols = ["Tháng", "NRU", "CPN (VNĐ)", "Nhân sự (VNĐ)", "Server (VNĐ)", "LF + Branding (VNĐ)"]
    valid_cols = [c for c in input_cols if c in input_base_df.columns]
    
    edited_input_df = st.data_editor(
        input_base_df[valid_cols], 
        num_rows="dynamic", 
        use_container_width=True,
        hide_index=True,
        key=f"editor_input_{cur_proj}",
        column_config={
            "NRU": st.column_config.NumberColumn("NRU", format="%d", min_value=0),
            "CPN (VNĐ)": st.column_config.NumberColumn("CPN (VNĐ)", format="%d", min_value=0),
            "Nhân sự (VNĐ)": st.column_config.NumberColumn("Nhân sự (VNĐ)", format="%d", min_value=0),
            "Server (VNĐ)": st.column_config.NumberColumn("Server (VNĐ)", format="%d", min_value=0),
            "LF + Branding (VNĐ)": st.column_config.NumberColumn("LF + Branding (VNĐ)", format="%d", min_value=0)
        }
    )
    
    st.markdown(f'<div class="section-title">2. Ngân Sách Marketing Tự Động Tính (Marketing Budget = CPN × NRU)</div>', unsafe_allow_html=True)
    mkt_summary_df = edited_input_df.copy()
    mkt_summary_df["NRU"] = pd.to_numeric(mkt_summary_df["NRU"], errors="coerce").fillna(0)
    mkt_summary_df["CPN (VNĐ)"] = pd.to_numeric(mkt_summary_df["CPN (VNĐ)"], errors="coerce").fillna(0)
    mkt_summary_df["Marketing Budget (VNĐ)"] = mkt_summary_df["NRU"] * mkt_summary_df["CPN (VNĐ)"]
    
    display_mkt_cols = ["Tháng", "NRU", "CPN (VNĐ)", "Marketing Budget (VNĐ)"]
    format_mkt_dict = {
        "NRU": "{:,.0f}",
        "CPN (VNĐ)": "{:,.0f} đ",
        "Marketing Budget (VNĐ)": "{:,.0f} đ"
    }
    st.dataframe(mkt_summary_df[display_mkt_cols].style.format(format_mkt_dict), use_container_width=True, hide_index=True)
    
# ==========================================
# TAB 2: CẤU HÌNH LTV CURVE (HỖ TRỢ ĐẾN D360)
# ==========================================
with tab_ltv:
    st.markdown(f'<div class="section-title">1. Nhập Giá Trị LTV Tích Lũy (D1 → D360) (VNĐ)</div>', unsafe_allow_html=True)
    st.caption("👉 Điền giá trị LTV các ngày tuổi trực tiếp tại bảng dưới (hỗ trợ tới **D360**). Bảng hệ số K bên dưới sẽ tự động tính ($K_x = LTV_x / LTV_1$).")

    month_options = edited_input_df["Tháng"].tolist()
    
    col_config = {
        "Áp dụng từ Tháng": st.column_config.SelectboxColumn("Áp dụng từ Tháng", options=month_options)
    }
    for c in ALL_D_COLS:
        col_config[c] = st.column_config.NumberColumn(f"{c} (VNĐ)", format="%d", min_value=0)

    current_ltv_state = st.session_state[f"ltv_df_{cur_proj}"].copy()
    for col_d in ALL_D_COLS:
        if col_d not in current_ltv_state.columns:
            current_ltv_state[col_d] = 0
            
    show_cols = ["Phase Name", "Áp dụng từ Tháng"] + ALL_D_COLS

    edited_ltv = st.data_editor(
        current_ltv_state[show_cols], 
        num_rows="dynamic", 
        use_container_width=True,
        column_config=col_config,
        hide_index=True,
        key=f"editor_ltv_{cur_proj}"
    )

    st.markdown(f'<div class="section-title">2. Bảng Hệ Số Tăng Trưởng K Tự Động ($K_x = LTV_x / LTV_1$)</div>', unsafe_allow_html=True)
    
    k_display_df = edited_ltv.copy()
    for c in ALL_D_COLS:
        k_display_df[c] = pd.to_numeric(k_display_df[c], errors="coerce").fillna(0.0)
        
    k_display_df['K1'] = np.where(k_display_df['D1'] > 0, 1.0, 0.0)
    for d in ALL_D_TARGETS:
        k_display_df[f'K{d}'] = np.where(k_display_df['D1'] > 0, k_display_df[f'D{d}'] / k_display_df['D1'], 0.0)
        
    k_only_cols = ["Phase Name", "Áp dụng từ Tháng", "K1"] + [f'K{d}' for d in ALL_D_TARGETS]
    k_table_to_show = k_display_df[k_only_cols].copy()
    
    format_k_dict = {f'K{d}': "{:.2f}x" for d in [1] + ALL_D_TARGETS}
    st.dataframe(k_table_to_show.style.format(format_k_dict), use_container_width=True, hide_index=True)

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

    st.write("**3. Đồ thị đường cong LTV mô phỏng (D1 → D360):**")
    fig_ltv = go.Figure()
    for idx, row in edited_ltv.iterrows():
        try:
            anchors = {int(c[1:]): float(row[c]) for c in ALL_D_COLS}
            curve = create_daily_ltv_curve(anchors)
            fig_ltv.add_trace(go.Scatter(x=np.arange(1, 361), y=curve[1:361], name=str(row['Phase Name'])))
        except:
            pass
    fig_ltv.update_layout(height=350, template="plotly_white", margin=dict(l=0, r=0, t=30, b=0), xaxis_title="Ngày tuổi (Day)", yaxis_title="LTV Tích Lũy (VNĐ)")
    st.plotly_chart(fig_ltv, use_container_width=True)

# ==========================================
# ENGINE CALCULATION (CORE COHORT MATRIX)
# ==========================================
def calculate_pnl(df_plan, df_ltv, params):
    df_plan = df_plan.copy()
    num_months = len(df_plan)
    ltv_mapping = {}
    
    for _, row in df_ltv.iterrows():
        try:
            anchors = {int(c[1:]): float(row[c]) for c in ALL_D_COLS if c in row}
            curve = create_daily_ltv_curve(anchors)
            if row['Áp dụng từ Tháng'] in df_plan['Tháng'].values:
                ltv_mapping[row['Áp dụng từ Tháng']] = curve
        except: pass
            
    latest_curve = np.zeros(721)
    month_curves = []
    for m in df_plan['Tháng']:
        if m in ltv_mapping: latest_curve = ltv_mapping[m]
        month_curves.append(latest_curve)
        
    daily_nru_list, daily_curve_list = [], []
    for m_idx, row in df_plan.iterrows():
        nru_daily = float(row['NRU']) / 30.0
        for d in range(30):
            daily_nru_list.append(nru_daily)
            daily_curve_list.append(month_curves[m_idx])
            
    total_days = len(daily_nru_list)
    daily_revenue = np.zeros(total_days)
    
    for c_day in range(total_days):
        c_nru = daily_nru_list[c_day]
        if c_nru <= 0: continue
        c_curve = daily_curve_list[c_day]
        inc_ltv = np.diff(np.insert(c_curve, 0, 0))[1:]
        for age in range(min(len(inc_ltv), total_days - c_day)):
            daily_revenue[c_day + age] += c_nru * inc_ltv[age]
            
    monthly_rev = [np.sum(daily_revenue[i*30:(i+1)*30]) for i in range(num_months)]
    
    df_plan['Revenue'] = monthly_rev
    
    df_plan['CPN (VNĐ)'] = pd.to_numeric(df_plan['CPN (VNĐ)'], errors='coerce').fillna(0.0)
    df_plan['NRU'] = pd.to_numeric(df_plan['NRU'], errors='coerce').fillna(0.0)
    df_plan['Marketing (UA+Tax)'] = df_plan['CPN (VNĐ)'] * df_plan['NRU']
    
    df_plan['Revenue share dev'] = df_plan['Revenue'] * (params['rev_share']/100)
    df_plan['VAT'] = df_plan['Revenue'] * (params['vat']/100)
    df_plan['Payment channel fee'] = df_plan['Revenue'] * (params['payment_fee']/100)
    
    df_plan['Cost per User'] = df_plan['CPN (VNĐ)']
    
    df_plan['Tổng Chi Phí'] = (
        df_plan['Marketing (UA+Tax)'] + df_plan['Nhân sự (VNĐ)'].astype(float) + df_plan['Server (VNĐ)'].astype(float) + 
        df_plan['LF + Branding (VNĐ)'].astype(float) + df_plan['Revenue share dev'] + df_plan['VAT'] + df_plan['Payment channel fee']
    )
    
    df_plan['Lợi nhuận tháng'] = df_plan['Revenue'] - df_plan['Tổng Chi Phí']
    df_plan['Lợi Nhuận'] = df_plan['Lợi nhuận tháng'].cumsum()
    df_plan['Tỷ Trọng MKT/REV'] = df_plan.apply(lambda x: x['Marketing (UA+Tax)'] / x['Revenue'] if x['Revenue'] > 0 else 0, axis=1)
    
    return df_plan

def format_cell_value(val, is_pct=False):
    if pd.isna(val) or val == 0: return "0"
    if is_pct: return f"{val*100:.2f}%"
    return f"{val:,.0f}"

# ==========================================
# GÓI DỮ LIỆU ĐỂ LƯU TOÀN DIỆN VÀO GOOGLE SHEET
# ==========================================
def export_all_to_google_sheet(cur_proj, df_input, df_ltv, res_pnl):
    traffic_rows = [df_input.columns.tolist()] + df_input.fillna("").values.tolist()
    
    k_df = df_ltv.copy()
    for c in ALL_D_COLS:
        if c in k_df.columns:
            k_df[c] = pd.to_numeric(k_df[c], errors="coerce").fillna(0.0)
    k_df['K1'] = np.where(k_df['D1'] > 0, 1.0, 0.0)
    for d in ALL_D_TARGETS:
        k_df[f'K{d}'] = np.where(k_df['D1'] > 0, k_df[f'D{d}'] / k_df['D1'], 0.0)
    ltv_rows = [k_df.columns.tolist()] + k_df.fillna("").values.tolist()
    
    total_nru = res_pnl['NRU'].sum()
    total_mkt = res_pnl['Marketing (UA+Tax)'].sum()
    cpu_total = total_mkt / total_nru if total_nru > 0 else 0
    months = list(res_pnl['Tháng'])

    pnl_rows = []
    pnl_rows.append(["Dashboard", "Total"] + months)
    pnl_rows.append(["", "KPI"] + ["KPI"] * len(months))
    pnl_rows.append(["New Registed User", float(total_nru)] + list(res_pnl['NRU'].astype(float)))
    pnl_rows.append(["Cost per User", float(cpu_total)] + list(res_pnl['Cost per User'].astype(float)))
    pnl_rows.append(["Revenue", float(res_pnl["Revenue"].sum())] + list(res_pnl['Revenue'].astype(float)))
    pnl_rows.append(["Spent", ""] + [""] * len(months))
    
    opex_items = [
        ('Personel', 'Nhân sự (VNĐ)'), ('Server', 'Server (VNĐ)'),
        ('Marketing (UA+Tax)', 'Marketing (UA+Tax)'), ('LF + Branding', 'LF + Branding (VNĐ)'),
        ('Revenue share dev', 'Revenue share dev'), ('VAT', 'VAT'),
        ('Payment channel fee', 'Payment channel fee')
    ]
    for label, col in opex_items:
        pnl_rows.append([label, float(res_pnl[col].sum())] + list(res_pnl[col].astype(float)))
        
    pnl_rows.append(["Tổng Chi Phí", float(res_pnl["Tổng Chi Phí"].sum())] + list(res_pnl['Tổng Chi Phí'].astype(float)))
    pnl_rows.append(["Lợi nhuận tháng", ""] + list(res_pnl['Lợi nhuận tháng'].astype(float)))
    pnl_rows.append(["Lợi Nhuận", float(res_pnl['Lợi Nhuận'].iloc[-1])] + list(res_pnl['Lợi Nhuận'].astype(float)))
    
    avg_mkt_rev = total_mkt / res_pnl["Revenue"].sum() if res_pnl["Revenue"].sum() > 0 else 0
    pnl_rows.append(["Tỷ Trọng MKT/REV", f"{avg_mkt_rev*100:.2f}%"] + [f"{v*100:.2f}%" for v in res_pnl['Tỷ Trọng MKT/REV']])

    all_projects_payload = {
        "project_names": st.session_state.project_names,
        "current_project": st.session_state.current_project,
        "projects_data": {}
    }
    for p in st.session_state.project_names:
        all_projects_payload["projects_data"][p] = {
            "input_df": st.session_state.get(f"input_df_{p}", get_default_input()).to_dict(orient="records"),
            "ltv_df": st.session_state.get(f"ltv_df_{p}", get_default_ltv()).to_dict(orient="records"),
            "params": st.session_state.get(f"params_{p}", {"rev_share": 20.2, "vat": 10.0, "payment_fee": 5.0})
        }

    payload = {
        "project_name": cur_proj,
        "traffic_plan": traffic_rows,
        "ltv_plan": ltv_rows,
        "pnl_rows": pnl_rows,
        "all_projects_payload": all_projects_payload
    }
    
    return requests.post(GOOGLE_SCRIPT_URL, data=json.dumps(payload), timeout=25)

# ==========================================
# TAB 3: BÁO CÁO P&L & HIỂN THỊ
# ==========================================
with tab_report:
    st.markdown(f'<div class="section-title">Báo Cáo Dự Án: {cur_proj}</div>', unsafe_allow_html=True)
    
    col_btn1, col_btn2 = st.columns([1, 2])
    run_sim = col_btn1.button(f"🚀 Chạy Mô Phỏng ({cur_proj})", type="primary")
    
    if run_sim or "last_pnl_res" in st.session_state:
        with st.spinner(f"Đang tính toán ma trận Cohort cho {cur_proj}..."):
            
            res = calculate_pnl(edited_input_df, edited_ltv, st.session_state[f"params_{cur_proj}"])
            st.session_state["last_pnl_res"] = res
            
            total_nru = res['NRU'].sum()
            total_mkt = res['Marketing (UA+Tax)'].sum()
            cpu_total = total_mkt / total_nru if total_nru > 0 else 0
            
            if col_btn2.button("☁️ Lưu Toàn Bộ Dữ Liệu Vào Google Sheet"):
                try:
                    with st.spinner("Đang lưu Input Traffic, LTV & Báo cáo P&L sang Google Spreadsheet..."):
                        resp = export_all_to_google_sheet(cur_proj, edited_input_df, edited_ltv, res)
                        if resp.status_code == 200:
                            st.success(f"🎉 Đã lưu thành công toàn bộ Input & Output của '{cur_proj}' vào Google Sheet!")
                        else:
                            st.error(f"Lỗi kết nối Webhook: {resp.text}")
                except Exception as ex:
                    st.error(f"Không thể kết nối Google Sheet: {ex}")

            html = '<div class="dataframe-container"><table class="custom-pnl">'
            
            # Header
            html += '<tr><th>Dashboard</th><th>Total</th>'
            for m in res['Tháng']: html += f'<th>{m}</th>'
            html += '</tr>'
            
            # KPI
            html += '<tr><td></td><td>KPI</td>'
            for _ in res['Tháng']: html += '<td>KPI</td>'
            html += '</tr>'
            
            # NRU
            html += f'<tr class="row-nru"><td>New Registed User</td><td>{format_cell_value(total_nru)}</td>'
            for v in res['NRU']: html += f'<td>{format_cell_value(v)}</td>'
            html += '</tr>'
            
            # Cost per User
            html += f'<tr class="row-cost"><td>Cost per User</td><td>{format_cell_value(cpu_total)}</td>'
            for v in res['Cost per User']: html += f'<td>{format_cell_value(v)}</td>'
            html += '</tr>'
            
            # Total Revenue
            html += f'<tr class="row-rev-total"><td>Revenue</td><td>{format_cell_value(res["Revenue"].sum())}</td>'
            for v in res['Revenue']: html += f'<td>{format_cell_value(v)}</td>'
            html += '</tr>'
            
            # Spent Header
            html += '<tr class="row-spent-header"><td>Spent</td><td></td>' + '<td></td>'*len(res) + '</tr>'
            
            # OPEX Rows
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
                
            # Total Cost
            html += f'<tr class="row-total-cost"><td>Tổng Chi Phí</td><td>{format_cell_value(res["Tổng Chi Phí"].sum())}</td>'
            for v in res['Tổng Chi Phí']: html += f'<td>{format_cell_value(v)}</td>'
            html += '</tr>'
            
            # Monthly Profit
            html += '<tr class="row-profit-month"><td>Lợi nhuận tháng</td><td></td>'
            for v in res['Lợi nhuận tháng']: 
                cls = "positive" if v > 0 else ""
                html += f'<td class="{cls}">{format_cell_value(v)}</td>'
            html += '</tr>'
            
            # Cumulative Profit
            total_profit = res['Lợi Nhuận'].iloc[-1]
            html += f'<tr class="row-profit-cum"><td>Lợi Nhuận</td><td>{format_cell_value(total_profit)}</td>'
            for v in res['Lợi Nhuận']: 
                cls = "positive" if v > 0 else ""
                html += f'<td class="{cls}">{format_cell_value(v)}</td>'
            html += '</tr>'
            
            # ROI
            avg_mkt_rev = total_mkt / res["Revenue"].sum() if res["Revenue"].sum() > 0 else 0
            html += f'<tr class="row-roi"><td>Tỷ Trọng MKT/REV</td><td>{format_cell_value(avg_mkt_rev, True)}</td>'
            for v in res['Tỷ Trọng MKT/REV']: html += f'<td>{format_cell_value(v, True)}</td>'
            html += '</tr>'
            
            html += '</table></div>'
            st.markdown(html, unsafe_allow_html=True)
            
            out_buffer = io.BytesIO()
            res.to_excel(out_buffer, index=False, engine='openpyxl')
            out_buffer.seek(0)
            st.download_button(f"📥 Tải File P&L - {cur_proj}", data=out_buffer, file_name=f"Game_Forecast_{cur_proj}.xlsx")
    else:
        st.info("💡 Bấm nút **Chạy Mô Phỏng** sau đó bấm **Lưu Toàn Bộ Dữ Liệu Vào Google Sheet** để đồng bộ.")
