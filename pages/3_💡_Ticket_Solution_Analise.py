import streamlit as st
import pandas as pd
import plotly.express as px
import os
import glob

# ==========================================
# PAGE CONFIGURATION & THEME
# ==========================================
st.set_page_config(
    page_title="Ticket Solution Analysis",
    page_icon="💡",
    layout="wide"
)

# Blue-Green Theme CSS
st.markdown("""
<style>
    /* Main Background */
    .stApp {
        background-color: #F0F9FF; /* Light Blue-Green tint */
    }
    
    /* Header typography */
    h1, h2, h3, h4 {
        color: #0369A1; /* Deep Ocean Blue */
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Dashboard Cards */
    .analysis-card {
        background-color: #FFFFFF;
        border-top: 4px solid #0D9488; /* Teal/Green border */
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
    }
    
    .kpi-title {
        color: #0F766E; /* Dark Teal */
        font-size: 14px;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 5px;
    }
    
    .kpi-value {
        color: #0369A1; /* Ocean Blue */
        font-size: 32px;
        font-weight: 700;
        margin-bottom: 5px;
    }
    
    /* Table Styling overrides */
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
    }
    
    [data-testid="stSidebarNav"] ul li span { font-size: 1.1rem !important; font-weight: 600 !important; }

    /* Fix Header and Sidebar Toggle */
    header {background-color: transparent !important;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    
    /* Make the sidebar toggle arrow clearly visible */
    [data-testid='collapsedControl'] {
        color: #0F766E !important;
        background-color: #F8FAFC !important;
        border: 2px solid #0F766E !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1) !important;
    }


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

# ==========================================
# DATA PROCESSING & UPLOAD LOGIC
# ==========================================
st.sidebar.markdown("### 📥 Data Source")
uploaded_file = st.sidebar.file_uploader("Upload Excel File", type=["xlsx", "xls"])

LATEST_UPLOAD = "latest_uploaded_data.xlsx"
import json
METADATA_FILE = "upload_metadata.json"

if uploaded_file:
    with open(LATEST_UPLOAD, "wb") as f:
        f.write(uploaded_file.getbuffer())
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"filename": uploaded_file.name}, f)
    st.sidebar.success("อัปโหลดและอัปเดตข้อมูลสำเร็จ!")

@st.cache_data(ttl=3600)
def load_data(file_trigger):
    file_to_load = None
    
    if os.path.exists(LATEST_UPLOAD):
        file_to_load = LATEST_UPLOAD
    else:
        file_pattern = "Ticket_detail_report_by_owner_flag_*.xlsx"
        files = glob.glob(file_pattern)
        if not files:
            files = [f for f in glob.glob("*.xlsx") if not f.startswith('~$') and 'Team GP' not in f and 'latest' not in f]
        if files:
            file_to_load = max(files, key=os.path.getctime)

    if not file_to_load:
        return pd.DataFrame()

    try:
        # Auto-detect header row
        preview = pd.read_excel(file_to_load, header=None, nrows=20)
        header_idx = 0
        for i, row in preview.iterrows():
            if 'TicketID' in row.values or 'Ticket ID' in row.values:
                header_idx = i
                break
                
        df = pd.read_excel(file_to_load, header=header_idx)
        
        # Datetime conversion for CreateDate
        if 'CreateDate' in df.columns:
            df['CreateDate'] = pd.to_datetime(df['CreateDate'], errors='coerce')
        
        # Fill missing values for analysis columns
        text_cols = ['Solution/Defect LV 1', 'Solution/Defect LV 2', 'DescriptionOfProblem', 'SolutionForUser']
        for col in text_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).replace('nan', 'Unknown')
                df[col] = df[col].fillna('Unknown')
                
        # Only keep rows that have actual defects mapped (ignore totally unknown ones if we want, but let's keep them and filter later)
        return df
    except Exception as e:
        st.error(f"Error parsing data: {e}")
        return pd.DataFrame()

# Use file modified time to trigger cache reload
file_mtime = os.path.getmtime(LATEST_UPLOAD) if os.path.exists(LATEST_UPLOAD) else 0
df = load_data(file_mtime)

if df.empty:
    st.warning("ไม่พบไฟล์ข้อมูล กรุณาอัปโหลดไฟล์ Excel เพื่อเริ่มวิเคราะห์")
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

f_ticket_type = filter_multiselect("Ticket Type", "TicketType", df)
f_defect1 = filter_multiselect("Defect Level 1", "Solution/Defect LV 1", df)
f_defect2 = filter_multiselect("Defect Level 2", "Solution/Defect LV 2", df)

if f_ticket_type: df = df[df['TicketType'].isin(f_ticket_type)]
if f_defect1: df = df[df['Solution/Defect LV 1'].isin(f_defect1)]
if f_defect2: df = df[df['Solution/Defect LV 2'].isin(f_defect2)]

# ==========================================
# HEADER
# ==========================================
st.markdown("<h2>💡 Problem & Solution Analysis</h2>", unsafe_allow_html=True)

original_filename = "Default System Data"
if os.path.exists(METADATA_FILE):
    try:
        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            meta = json.load(f)
            original_filename = meta.get("filename", "Unknown")
    except: pass

date_text = "N/A"
if not df.empty and 'CreateDate' in df.columns and not df['CreateDate'].isna().all():
    s_date = df['CreateDate'].dt.date.min().strftime('%d %b %Y')
    e_date = df['CreateDate'].dt.date.max().strftime('%d %b %Y')
    date_text = f"{s_date} - {e_date}"

st.markdown(f"<p style='color: #0F766E;'>ระบบวิเคราะห์และจัดกลุ่มปัญหาอัตโนมัติ (Blue-Green Theme) | 📁 <b>{original_filename}</b> | 📅 <b>{date_text}</b></p>", unsafe_allow_html=True)

# Filter out 'Unknown' or invalid defects for the core grouping
if 'Solution/Defect LV 1' in df.columns and 'Solution/Defect LV 2' in df.columns:
    valid_defects = df[~df['Solution/Defect LV 1'].str.contains('Unknown|-', case=False, regex=True)]
else:
    valid_defects = pd.DataFrame()

# ==========================================
# GROUPING LOGIC (KNOWLEDGE BASE)
# ==========================================
kb_df = pd.DataFrame()
if not valid_defects.empty:
    # Group by LV1 and LV2
    group_cols = ['Solution/Defect LV 1', 'Solution/Defect LV 2']
    
    # We want to aggregate: Count of tickets, and Mode (most frequent) description & solution
    kb_df = valid_defects.groupby(group_cols).agg(
        Frequency=('TicketID', 'count'),
        Sample_Problem=('DescriptionOfProblem', lambda x: x.mode()[0] if not x.mode().empty else x.iloc[0]),
        Recommended_Solution=('SolutionForUser', lambda x: x.mode()[0] if not x.mode().empty else x.iloc[0])
    ).reset_index().sort_values('Frequency', ascending=False)


# ==========================================
# AI INSIGHTS & RECOMMENDATIONS
# ==========================================
st.markdown("<div class='analysis-card'>", unsafe_allow_html=True)
st.markdown("<h3>🤖 AI Analytical Recommendations</h3>", unsafe_allow_html=True)

if not kb_df.empty:
    top_lv1 = kb_df.groupby('Solution/Defect LV 1')['Frequency'].sum().idxmax()
    top_lv1_count = kb_df.groupby('Solution/Defect LV 1')['Frequency'].sum().max()
    
    top_specific = kb_df.iloc[0]
    
    st.markdown(f"""
    **ข้อสังเกตจากข้อมูล (Data Insights):**
    1. 🎯 **ปัญหาหลักที่พบมากที่สุด:** หมวดหมู่ **{top_lv1}** มีจำนวนการแจ้งเหตุสูงสุดถึง {top_lv1_count} รายการ
    2. 🔍 **ปัญหาย่อยที่พบบ่อยที่สุด:** **{top_specific['Solution/Defect LV 1']} ➔ {top_specific['Solution/Defect LV 2']}** (เกิดซ้ำ {top_specific['Frequency']} ครั้ง)
    
    **ข้อเสนอแนะเชิงบริหาร (Recommendations):**
    - 💡 ควรนำแนวทางแก้ไข: *"{top_specific['Recommended_Solution']}"* จัดทำเป็น **Self-Service Manual** เผยแพร่ให้ผู้ใช้งานเพื่อลดปริมาณตั๋วในหมวดหมู่นี้
    - 🔄 หากปัญหาลักษณะเดิมเกิดขึ้นซ้ำเกิน 20% ของระบบ ควรพิจารณาประสานงานกับทีมพัฒนาเพื่อแก้ไขที่ต้นเหตุ (Root Cause)
    """)
else:
    st.info("ไม่พบข้อมูล Defect ที่ชัดเจนสำหรับการวิเคราะห์")
st.markdown("</div>", unsafe_allow_html=True)


# ==========================================
# VISUALIZATION
# ==========================================
c1, c2 = st.columns([1, 1])

with c1:
    st.markdown("<div class='analysis-card'>", unsafe_allow_html=True)
    st.markdown("<h4>📊 Defect Distribution (Treemap)</h4>", unsafe_allow_html=True)
    if not kb_df.empty:
        fig_tree = px.treemap(kb_df, path=['Solution/Defect LV 1', 'Solution/Defect LV 2'], values='Frequency',
                              color='Frequency', color_continuous_scale=px.colors.sequential.Teal)
        fig_tree.update_layout(margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_tree, use_container_width=True)
    else:
        st.info("ไม่มีข้อมูลสำหรับกราฟ")
    st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.markdown("<div class='analysis-card'>", unsafe_allow_html=True)
    st.markdown("<h4>📈 Top 10 Specific Defects</h4>", unsafe_allow_html=True)
    if not kb_df.empty:
        top10_df = kb_df.head(10).copy()
        top10_df['Defect Path'] = top10_df['Solution/Defect LV 1'] + " > " + top10_df['Solution/Defect LV 2']
        fig_bar = px.bar(top10_df, x='Frequency', y='Defect Path', orientation='h', text_auto=True,
                         color='Frequency', color_continuous_scale=px.colors.sequential.Teal)
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("ไม่มีข้อมูลสำหรับกราฟ")
    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# GROUPED KNOWLEDGE BASE TABLE
# ==========================================
st.markdown("<div class='analysis-card'>", unsafe_allow_html=True)
st.markdown("<h3>📚 Solution Knowledge Base (จัดกลุ่มปัญหาที่เหมือนกัน)</h3>", unsafe_allow_html=True)

if not kb_df.empty:
    st.dataframe(kb_df.style.set_properties(**{'font-size': '14px'}), use_container_width=True, hide_index=True, height=500)
else:
    st.warning("ไม่สามารถสร้างตาราง Knowledge Base ได้ เนื่องจากข้อมูลไม่ครบถ้วน")
st.markdown("</div>", unsafe_allow_html=True)
