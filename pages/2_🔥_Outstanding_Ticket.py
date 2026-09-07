import streamlit as st
import pandas as pd
import plotly.express as px
import os
import glob
import json

st.set_page_config(page_title="Outstanding Ticket", page_icon="🔥", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #FAFAF9; }
    h1, h2, h3, h4 { color: #1C1917; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .card { background-color: #FFFFFF; border: 1px solid #E7E5E4; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05); }
    .kpi-title { color: #57534E; font-size: 14px; font-weight: 500; text-transform: uppercase; margin-bottom: 5px; }
    .kpi-value { color: #0C4A6E; font-size: 32px; font-weight: 700; margin-bottom: 5px; }
    .stDataFrame { border-radius: 8px; overflow: hidden; }
    /* Fix Header and Sidebar Toggle */
    header {background-color: transparent !important;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    [data-testid='collapsedControl'] {
        color: #0F766E !important;
        background-color: #F8FAFC !important;
        border: 2px solid #0F766E !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1) !important;
    }
    [data-testid="stSidebarNav"] ul li span { font-size: 1.1rem !important; font-weight: 600 !important; }

    /* Increase font sizes for filters */
    .stMultiSelect label, .stDateInput label, .stSelectbox label {
        font-size: 1.15rem !important;
        font-weight: 500 !important;
    }
    div[data-baseweb="select"] * {
        font-size: 1.05rem !important;
    }
    /* Attempt to scale dataframe */
    [data-testid="stDataFrame"] {
        font-size: 1.05rem !important;
    }
    .stMarkdown p, .stMarkdown li {
        font-size: 1.05rem !important;
    }

</style>
""", unsafe_allow_html=True)

# DATA LOADING (Same as Ticket Management)
LATEST_UPLOAD = "latest_uploaded_data.xlsx"
METADATA_FILE = "upload_metadata.json"

@st.cache_data(ttl=3600)
def load_data(file_trigger):
    target_file = None
    if os.path.exists(LATEST_UPLOAD):
        target_file = LATEST_UPLOAD
    else:
        file_pattern = "Ticket_detail_report_by_owner_flag_*.xlsx"
        files = glob.glob(file_pattern)
        if not files:
            files = [f for f in glob.glob("*.xlsx") if not f.startswith('~$') and 'Team GP' not in f and 'latest' not in f]
        if files:
            target_file = max(files, key=os.path.getctime)

    if not target_file:
        return pd.DataFrame(), "Unknown"

    try:
        preview = pd.read_excel(target_file, header=None, nrows=20)
        header_idx = 0
        for i, row in preview.iterrows():
            if 'TicketID' in str(row.values) or 'Ticket ID' in str(row.values):
                header_idx = i
                break
                
        df = pd.read_excel(target_file, header=header_idx)
        return df, os.path.basename(target_file)
    except Exception as e:
        st.error(f"Error parsing data: {e}")
        return pd.DataFrame(), "Unknown"

file_mtime = os.path.getmtime(LATEST_UPLOAD) if os.path.exists(LATEST_UPLOAD) else 0
raw_df, fallback_filename = load_data(file_mtime)

if raw_df.empty:
    st.warning("ไม่พบไฟล์ข้อมูล กรุณาอัปโหลดไฟล์ Excel ในหน้า Ticket Management ก่อน")
    st.stop()

# OUTSTANDING TRANSFORMATION
# Filter for Accept, Acknowledge
if 'Status' in raw_df.columns:
    df = raw_df[raw_df['Status'].astype(str).str.contains('Accept|Acknowledge', case=False, na=False)].copy()
else:
    df = pd.DataFrame()

if df.empty:
    st.info("ไม่มีงาน Outstanding (Status: Accept, Acknowledge) ในขณะนี้")
    st.stop()

# Convert dates
for col in ['CreateDate', 'StartSLADate', 'EndSLADate']:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors='coerce')

current_time = pd.Timestamp.now()

# Create requested columns map
out_df = pd.DataFrame()
out_df['Parent ID 1'] = df.get('CategoryLevel1', 'Unknown')
out_df['Child ID 2'] = df.get('CategoryLevel2', 'Unknown')
out_df['Name Staff'] = df.get('ResponseBy', 'Unknown')
out_df['Status'] = df.get('Status', 'Unknown')

if 'CreateDate' in df.columns:
    out_df['Ageing day'] = (current_time - df['CreateDate']).dt.days
else:
    out_df['Ageing day'] = 0

bg = df.get('BusinessGroup', '').fillna('')
cat1 = df.get('CategoryLevel1', '').fillna('')
out_df['Case - (Duration)-Problem'] = bg + " => " + cat1

out_df['Ticket No.'] = df.get('TicketID', 'Unknown')
out_df['Duration(Days)'] = df.get('EffortTime', 0)
out_df['Create Date/Time'] = df.get('CreateDate', '')
out_df['Details'] = df.get('DescriptionOfProblem', '')
out_df['Solution for IT'] = df.get('SolutionForIT', '')

def eval_sla(row):
    end_sla = row.get('EndSLADate')
    if pd.isna(end_sla): return 'Unknown'
    if current_time > end_sla: return 'Over SLA'
    if (end_sla - current_time).total_seconds() <= 86400: return 'Near SLA'
    return 'Within SLA'

out_df['SLA Rank'] = df.apply(eval_sla, axis=1) if 'EndSLADate' in df.columns else 'Unknown'
out_df['Start SLA date'] = df.get('StartSLADate', '')
out_df['SLA Due'] = df.get('EndSLADate', '')
out_df['Actual SLA'] = df.get('SLAStatus', '')
out_df['Count of status case'] = 1

# ==========================================
# SIDEBAR FILTERS
# ==========================================
st.sidebar.markdown("### 🔍 Filters")
def filter_multiselect(label, col_name, data):
    if col_name in data.columns:
        options = sorted(list(data[col_name].dropna().astype(str).unique()))
        return st.sidebar.multiselect(label, options=options)
    return []

f_category = filter_multiselect("Category (Level 1)", "Parent ID 1", out_df)
f_assignee = filter_multiselect("Assignee (Response By)", "Name Staff", out_df)

if f_category: out_df = out_df[out_df['Parent ID 1'].isin(f_category)]
if f_assignee: out_df = out_df[out_df['Name Staff'].isin(f_assignee)]

# ==========================================
# HEADER
# ==========================================
original_filename = fallback_filename
if os.path.exists(METADATA_FILE):
    try:
        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            meta = json.load(f)
            original_filename = meta.get("filename", fallback_filename)
    except: pass

st.markdown("<h2>🔥 Outstanding Tickets Dashboard</h2>", unsafe_allow_html=True)
st.markdown(f"<p style='color: #57534E;'>ข้อมูลงานค้าง (Accept/Acknowledge) | 📁 <b>{original_filename}</b></p>", unsafe_allow_html=True)

# KPIs
k1, k2, k3 = st.columns(3)
k1.markdown(f"<div class='card'><div class='kpi-title'>Total Outstanding</div><div class='kpi-value'>{len(out_df)}</div></div>", unsafe_allow_html=True)
k2.markdown(f"<div class='card'><div class='kpi-title'>Avg Ageing (Days)</div><div class='kpi-value'>{out_df['Ageing day'].mean():.1f}</div></div>", unsafe_allow_html=True)
over_sla = len(out_df[out_df['SLA Rank'] == 'Over SLA'])
k3.markdown(f"<div class='card'><div class='kpi-title'>Over SLA</div><div class='kpi-value' style='color: #EF4444;'>{over_sla}</div></div>", unsafe_allow_html=True)

# CHARTS
c1, c2, c3 = st.columns([1, 1, 1])

with c1:
    st.markdown("<div class='card'><h4>📊 Category (Level 1)</h4>", unsafe_allow_html=True)
    cat_df = out_df['Parent ID 1'].fillna('Unknown').value_counts().head(10).reset_index()
    cat_df.columns = ['Category', 'Count']
    fig1 = px.bar(cat_df, y='Category', x='Count', orientation='h', text_auto=True, color='Count', color_continuous_scale='Blues')
    fig1.update_layout(font=dict(size=14), yaxis={'categoryorder':'total ascending'}, margin=dict(t=10, b=10, l=10, r=10))
    st.plotly_chart(fig1, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.markdown("<div class='card'><h4>👤 Assignee Workload</h4>", unsafe_allow_html=True)
    staff_df = out_df['Name Staff'].fillna('Unknown').value_counts().head(10).reset_index()
    staff_df.columns = ['Name', 'Count']
    fig2 = px.bar(staff_df, y='Name', x='Count', orientation='h', text_auto=True, color='Count', color_continuous_scale='Oranges')
    fig2.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(t=10, b=10, l=10, r=10))
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with c3:
    st.markdown("<div class='card'><h4>🚨 Over SLA Days by Category</h4>", unsafe_allow_html=True)
    over_df = out_df[out_df['SLA Rank'] == 'Over SLA']
    if not over_df.empty:
        sla_days_df = over_df.groupby('Parent ID 1')['Ageing day'].sum().reset_index().sort_values('Ageing day', ascending=False).head(10)
        fig3 = px.bar(sla_days_df, x='Parent ID 1', y='Ageing day', text_auto=True, color='Ageing day', color_continuous_scale='Reds')
        fig3.update_layout(margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("🎉 ไม่มีงานที่ Over SLA")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<h3>📋 Outstanding Ticket Details</h3>", unsafe_allow_html=True)
st.markdown("<div class='card'>", unsafe_allow_html=True)
st.dataframe(out_df.style.set_properties(**{'font-size': '14px'}), use_container_width=True, hide_index=True)
st.markdown("</div>", unsafe_allow_html=True)
