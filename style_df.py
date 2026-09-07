import glob
import re

files = glob.glob('*.py') + glob.glob('pages/*.py')
for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Inject dataframe style
    content = content.replace(
        "st.dataframe(filtered_df[disp_cols].style.set_properties(**{'font-size': '14px'})",
        "st.dataframe(filtered_df[disp_cols].style.set_properties(**{'font-size': '14px'}).style.set_properties(**{'font-size': '14px'})"
    )
    content = content.replace(
        "st.dataframe(out_df.style.set_properties(**{'font-size': '14px'})",
        "st.dataframe(out_df.style.set_properties(**{'font-size': '14px'}).style.set_properties(**{'font-size': '14px'})"
    )
    content = content.replace(
        "st.dataframe(kb_df.style.set_properties(**{'font-size': '14px'})",
        "st.dataframe(kb_df.style.set_properties(**{'font-size': '14px'}).style.set_properties(**{'font-size': '14px'})"
    )
    
    with open(file, 'w', encoding='utf-8') as f:
        f.write(content)
