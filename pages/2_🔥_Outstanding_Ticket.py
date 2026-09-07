import streamlit as st
import pandas as pd
import plotly.express as px
import os
import glob

# ==========================================
# PAGE CONFIGURATION & THEME
# ==========================================
st.set_page_config(
    page_title="Outstanding Ticket",
    page_icon="🔥",
    layout="wide"
)

# Theme CSS
st.markdown("""
<style>
    .stApp { background-color: #FAFAF9; }
    h1, h2, h3, h4 { color: #1C1917; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .card {
        background-color: #FFFFFF;
        border: 1px solid #E7E5E4;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }
    .kpi-title { color: #57534E; font-size: 14px; font-weight: 500; text-transform: uppercase; margin-bottom: 5px; }
    .kpi-value { color: #0C4A6E; font-size: 32px; font-weight: 700; margin-bottom: 5px; }
    .stDataFrame { border-radius: 8px; overflow: hidden; }
    [data-testid="stSidebarNav"] ul li span { font-size: 1.1rem !important; font-weight: 600 !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# DATA PROCESSING & UPLOAD LOGIC
# ==========================================
st.sidebar.markdown("### 📥 Data Source")
uploaded_file = st.sidebar.file_uploader("Upload Outstanding Excel", type=["xlsx", "xls"])

LATEST_UPLOAD = "latest_outstanding_data.xlsx"
TARGET_FILE = "Outstanding_tickets_report_20260907_13.16.xlsx"

if uploaded_file:
    with open(LATEST_UPLOAD, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.sidebar.success("อัปโหลดข้อมูลเรียบร้อยแล้ว!")

@st.cache_data(ttl=3600)
def load_data(file_trigger):
    file_to_load = None
    
    if os.path.exists(LATEST_UPLOAD):
        file_to_load = LATEST_UPLOAD
    elif os.path.exists(TARGET_FILE):
        file_to_load = TARGET_FILE
    elif os.path.exists(f"../{TARGET_FILE}"):
        file_to_load = f"../{TARGET_FILE}"
    else:
        # Fallback
        files = glob.glob("Outstanding_tickets_report_*.xlsx")
        if not files:
            files = glob.glob("../Outstanding_tickets_report_*.xlsx")
        if files:
            file_to_load = max(files, key=os.path.getctime)

    if not file_to_load:
        return pd.DataFrame(), "Unknown"

    try:
        # Auto-detect header row
        preview = pd.read_excel(file_to_load, header=None, nrows=20)
        header_idx = 0
        for i, row in preview.iterrows():
            if 'Ticket No.' in row.values or 'Parent ID 1' in row.values:
                header_idx = i
                break
                
        df = pd.read_excel(file_to_load, header=header_idx)
        
        # Clean Pivot Table structure
        # Forward fill the grouping columns
        ffill_cols = ['Parent ID 1', 'Child ID 2', 'Name Staff', 'Status']
        for col in ffill_cols:
            if col in df.columns:
                df[col] = df[col].ffill()
                
        # Remove subtotals (where Ticket No. is NaN)
        if 'Ticket No.' in df.columns:
            df = df.dropna(subset=['Ticket No.'])
            
        # Extract Category Level 1 from Case column if present
        if 'Case - (Duration)-Problem' in df.columns:
            df['Category (Level 1)'] = df['Case - (Duration)-Problem'].astype(str).apply(lambda x: x.split('=>')[-1].strip() if '=>' in x else x.strip())
        else:
            df['Category (Level 1)'] = df.get('Parent ID 1', 'Unknown')
            
        # Ensure Ageing Day is numeric
        if 'Ageing day' in df.columns:
            df['Ageing day'] = pd.to_numeric(df['Ageing day'], errors='coerce').fillna(0)
            
        return df, os.path.basename(file_to_load)
    except Exception as e:
        st.error(f"Error parsing data: {e}")
        return pd.DataFrame(), "Unknown"

file_mtime = os.path.getmtime(LATEST_UPLOAD) if os.path.exists(LATEST_UPLOAD) else 0
df, filename = load_data(file_mtime)

if df.empty:
    st.warning("ไม่พบไฟล์ข้อมูล กรุณาอัปโหลดไฟล์ Outstanding Excel เพื่อเริ่มวิเคราะห์")
    st.stop()

# ==========================================
# SIDEBAR FILTERS
# ==========================================
st.sidebar.markdown("### 🔍 Filters")

def filter_multiselect(label, col_name, data):
    if col_name in data.columns:
        options = sorted(list(data[col_name].dropna().astype(str).unique()))
        selected = st.sidebar.multiselect(label, options=options)
        return selected
    return []

f_category = filter_multiselect("Category (Level 1)", "Category (Level 1)", df)
f_assignee = filter_multiselect("Assignee (Response By)", "Name Staff", df)

if f_category: df = df[df['Category (Level 1)'].isin(f_category)]
if f_assignee: df = df[df['Name Staff'].isin(f_assignee)]

# ==========================================
# HEADER
# ==========================================
st.markdown("<h2>🔥 Outstanding Tickets Dashboard</h2>", unsafe_allow_html=True)
st.markdown(f"<p style='color: #57534E;'>วิเคราะห์สถานะงานค้างและระดับ SLA | 📁 <b>{filename}</b></p>", unsafe_allow_html=True)

# ==========================================
# KPIs
# ==========================================
total_out = len(df)
avg_ageing = df['Ageing day'].mean() if 'Ageing day' in df.columns else 0

sla_at_risk = 0
if 'SLA Rank' in df.columns:
    sla_at_risk = len(df[df['SLA Rank'].astype(str).str.contains('Over|Risk|Breach', case=False, na=False)])
    
k1, k2, k3 = st.columns(3)
k1.markdown(f"<div class='card'><div class='kpi-title'>Total Outstanding</div><div class='kpi-value'>{total_out}</div></div>", unsafe_allow_html=True)
k2.markdown(f"<div class='card'><div class='kpi-title'>Avg Ageing (Days)</div><div class='kpi-value'>{avg_ageing:.1f}</div></div>", unsafe_allow_html=True)
k3.markdown(f"<div class='card'><div class='kpi-title'>SLA Overdue/At Risk</div><div class='kpi-value' style='color: #EF4444;'>{sla_at_risk}</div></div>", unsafe_allow_html=True)


# ==========================================
# CHARTS
# ==========================================
c1, c2, c3 = st.columns([1, 1, 1])

with c1:
    st.markdown("<div class='card'><h4>📊 SLA Status (Rank)</h4>", unsafe_allow_html=True)
    if 'SLA Rank' in df.columns:
        sla_df = df['SLA Rank'].fillna('Unknown').value_counts().reset_index()
        sla_df.columns = ['SLA Rank', 'Count']
        fig_sla = px.pie(sla_df, names='SLA Rank', values='Count', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_sla.update_layout(margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig_sla, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.markdown("<div class='card'><h4>📁 Category (Level 1)</h4>", unsafe_allow_html=True)
    cat_col = 'Category (Level 1)'
    if cat_col in df.columns:
        prod_df = df[cat_col].fillna('Unknown').value_counts().head(10).reset_index()
        prod_df.columns = ['Product', 'Count']
        fig_prod = px.bar(prod_df, y='Product', x='Count', orientation='h', text_auto=True, color='Count', color_continuous_scale='Blues')
        fig_prod.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig_prod, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with c3:
    st.markdown("<div class='card'><h4>👤 Assignee Workload</h4>", unsafe_allow_html=True)
    if 'Name Staff' in df.columns:
        staff_df = df['Name Staff'].fillna('Unknown').value_counts().head(10).reset_index()
        staff_df.columns = ['Name', 'Count']
        fig_staff = px.bar(staff_df, y='Name', x='Count', orientation='h', text_auto=True, color='Count', color_continuous_scale='Oranges')
        fig_staff.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig_staff, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# DATA TABLE
# ==========================================
st.markdown("<h3>📋 Outstanding Ticket List</h3>", unsafe_allow_html=True)
st.markdown("<div class='card'>", unsafe_allow_html=True)

# Filter out empty columns to make it cleaner
disp_cols = [c for c in df.columns if not c.startswith('Unnamed')]
if disp_cols:
    st.dataframe(df[disp_cols], use_container_width=True, hide_index=True)
st.markdown("</div>", unsafe_allow_html=True)
