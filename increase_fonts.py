import glob

css_injection = """
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
"""

files = glob.glob('*.py') + glob.glob('pages/*.py')
for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Inject CSS
    if '/* Increase font sizes' not in content:
        content = content.replace('</style>', css_injection + '\n</style>')
        
    # Increase Plotly font size
    import re
    # We will use regex to find all update_layout and insert font=dict(size=14) if not present
    # But string replacement is safer if we just replace the ones we know
    
    replace_targets = [
        'fig.update_layout(',
        'fig1.update_layout(',
        'fig2.update_layout(',
        'fig3.update_layout(',
        'fig_sla.update_layout(',
        'fig_prod.update_layout(',
        'fig_staff.update_layout(',
        'fig_kb.update_layout('
    ]
    
    for t in replace_targets:
        if t in content and 'font=dict(size=14)' not in content:
            content = content.replace(t, t + 'font=dict(size=14), ')
            
    with open(file, 'w', encoding='utf-8') as f:
        f.write(content)
