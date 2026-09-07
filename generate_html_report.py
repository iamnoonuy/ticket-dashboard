import pandas as pd
import plotly.express as px
import plotly.io as pio
import os
from datetime import datetime

# --- LOAD DATA ---
data_file = 'Ticket_detail_report_by_owner_flag_20260902_07.57.xlsx'
df = pd.read_excel(data_file, skiprows=5)

# --- CLEAN DATA ---
df['CreateDate_Parsed'] = pd.to_datetime(df['CreateDate'], errors='coerce')
df['CreateDate_Day'] = df['CreateDate_Parsed'].dt.date
df['Status'] = df['Status'].fillna('Unknown')
df['CategoryLevel1'] = df['CategoryLevel1'].fillna('Unknown')
df['ActualSLA'] = df['ActualSLA'].fillna('Unknown')
df['ResponseBy'] = df['ResponseBy'].fillna('Unassigned')

for col in ['Solution/Defect LV 1', 'Solution/Defect LV 2']:
    if col in df.columns:
        df[col] = df[col].fillna('Unknown')
    else:
        df[col] = 'Unknown'
        
for col in ['DescriptionOfProblem', 'SolutionForUser', 'SolutionForIT']:
    if col in df.columns:
        df[col] = df[col].fillna('-')
    else:
        df[col] = '-'

# --- TEAM FILTER ---
team_file_path = 'Team GP Account&Finance.xlsx'
if os.path.exists(team_file_path):
    team_df = pd.read_excel(team_file_path)
    if 'รายชื่อทีม' in team_df.columns:
        team_names_clean = team_df['รายชื่อทีม'].dropna().astype(str).str.replace('^คุณ', '', regex=True).str.strip().tolist()
        team_names_raw = team_df['รายชื่อทีม'].dropna().astype(str).str.strip().tolist()
        allowed_names = set(team_names_clean + team_names_raw)
        df = df[df['ResponseBy'].isin(allowed_names)]

# --- SLA CALCULATION ---
df['UpdateDate_Parsed'] = pd.to_datetime(df['UpdateDate'], errors='coerce')
df['EndSLADate_Parsed'] = pd.to_datetime(df['EndSLADate'], errors='coerce')
current_date = df['UpdateDate_Parsed'].max() if not df['UpdateDate_Parsed'].isna().all() else pd.to_datetime('today')
active_mask = ~df['Status'].str.contains('Complete|Closed|Cancel', case=False, na=False)
df['Days_to_SLA'] = (df['EndSLADate_Parsed'] - current_date).dt.total_seconds() / (24*3600)
df['SLA_Risk'] = 'Safe'
df.loc[df['ActualSLA'] == 'Over SLA', 'SLA_Risk'] = 'Over SLA'
df.loc[active_mask & (df['ActualSLA'] != 'Over SLA') & (df['Days_to_SLA'] <= 1) & (df['Days_to_SLA'] >= 0), 'SLA_Risk'] = 'At Risk (<= 1 Day)'
df.loc[active_mask & (df['Days_to_SLA'] < 0), 'SLA_Risk'] = 'Over SLA'

# --- KPIs ---
total_tickets = len(df)
resolved_tickets = len(df[df['Status'].str.contains('Complete|Closed', case=False, na=False)])
over_sla_cases = len(df[df['SLA_Risk'] == 'Over SLA'])
risk_sla_cases = len(df[df['SLA_Risk'] == 'At Risk (<= 1 Day)'])

# --- CHARTS ---
# 1. SLA Donut
sla_data = df['SLA_Risk'].value_counts().reset_index()
sla_data.columns = ['SLA Risk', 'Count']
color_map = {'Safe':'#26A69A', 'At Risk (<= 1 Day)':'#FFA726', 'Over SLA':'#EF5350', 'Unknown':'#B0BEC5'}
fig_donut = px.pie(sla_data, values='Count', names='SLA Risk', hole=0.5, template="plotly_white", color='SLA Risk', color_discrete_map=color_map, title="SLA Risk Status")
donut_html = pio.to_html(fig_donut, full_html=False, include_plotlyjs='cdn')

# 2. Defect Sunburst
defect_df = df[(df['Solution/Defect LV 1'] != 'Unknown') & (df['Solution/Defect LV 1'] != '-') & (df['Status'].str.contains('Complete|Closed', case=False, na=False))]
if not defect_df.empty:
    fig_sunburst = px.sunburst(defect_df, path=['Solution/Defect LV 1', 'Solution/Defect LV 2'], template="plotly_white", color_discrete_sequence=px.colors.sequential.Teal, title="Defect Breakdown (Completed)")
    fig_sunburst.update_traces(textinfo="label+percent parent")
    sunburst_html = pio.to_html(fig_sunburst, full_html=False, include_plotlyjs=False)
else:
    sunburst_html = "<p>No defect data available</p>"

# --- TABLES ---
critical_df = df[df['SLA_Risk'].isin(['Over SLA', 'At Risk (<= 1 Day)'])]
critical_table = critical_df[['TicketID', 'Priority', 'Status', 'SLA_Risk', 'EndSLADate', 'ResponseBy']].to_html(classes="styled-table", index=False)

group_cols = ['Solution/Defect LV 1', 'Solution/Defect LV 2']
if not defect_df.empty:
    kb_df = defect_df.groupby(group_cols).agg(
        Frequency=('TicketID', 'count'),
        Sample_Problem=('DescriptionOfProblem', lambda x: x.mode()[0] if not x.mode().empty else x.iloc[0]),
        Solution_For_User=('SolutionForUser', lambda x: x.mode()[0] if not x.mode().empty else x.iloc[0])
    ).reset_index().sort_values('Frequency', ascending=False).head(10)
    kb_table = kb_df.to_html(classes="styled-table", index=False)
else:
    kb_table = "<p>No data</p>"

# --- GENERATE HTML ---
html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Executive Ticket & Solution Report</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #F4FBF9; color: #333; margin: 0; padding: 20px; }}
        h1, h2, h3 {{ color: #004D40; }}
        .header {{ text-align: center; margin-bottom: 40px; }}
        .kpi-container {{ display: flex; justify-content: space-around; margin-bottom: 40px; flex-wrap: wrap; }}
        .kpi-card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; min-width: 150px; border-top: 4px solid #00897B; margin: 10px; }}
        .kpi-card.danger {{ border-top: 4px solid #D32F2F; }}
        .kpi-card.warning {{ border-top: 4px solid #FBC02D; }}
        .kpi-value {{ font-size: 2em; font-weight: bold; margin-top: 10px; }}
        .chart-container {{ display: flex; justify-content: space-between; flex-wrap: wrap; margin-bottom: 40px; }}
        .chart {{ width: 48%; background: white; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); padding: 10px; box-sizing: border-box; }}
        .section {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 40px; overflow-x: auto; }}
        .styled-table {{ border-collapse: collapse; margin: 25px 0; font-size: 0.9em; width: 100%; box-shadow: 0 0 20px rgba(0, 0, 0, 0.05); }}
        .styled-table thead tr {{ background-color: #00897B; color: #ffffff; text-align: left; }}
        .styled-table th, .styled-table td {{ padding: 12px 15px; border-bottom: 1px solid #dddddd; }}
        .styled-table tbody tr:nth-of-type(even) {{ background-color: #f3f3f3; }}
        .styled-table tbody tr:last-of-type {{ border-bottom: 2px solid #00897B; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Executive Ticket & Solution Report</h1>
        <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    </div>

    <div class="kpi-container">
        <div class="kpi-card">
            <div>Total Tickets</div>
            <div class="kpi-value" style="color:#00796B;">{total_tickets}</div>
        </div>
        <div class="kpi-card">
            <div>Resolved</div>
            <div class="kpi-value" style="color:#00796B;">{resolved_tickets}</div>
        </div>
        <div class="kpi-card danger">
            <div style="color:#D32F2F;">🚨 Over SLA</div>
            <div class="kpi-value" style="color:#C62828;">{over_sla_cases}</div>
        </div>
        <div class="kpi-card warning">
            <div style="color:#FBC02D;">⚠️ At Risk (&lt;1 Day)</div>
            <div class="kpi-value" style="color:#F57F17;">{risk_sla_cases}</div>
        </div>
    </div>

    <div class="chart-container">
        <div class="chart">
            {donut_html}
        </div>
        <div class="chart">
            {sunburst_html}
        </div>
    </div>

    <div class="section">
        <h2>⚠️ Critical Tickets (Over SLA & At Risk)</h2>
        {critical_table}
    </div>

    <div class="section">
        <h2>💡 Top 10 Problem & Solution Knowledge Base</h2>
        {kb_table}
    </div>

</body>
</html>
"""

# Write to file
with open('Dashboard_Report.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print("HTML report generated successfully at Dashboard_Report.html")
