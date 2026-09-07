import pandas as pd
import json

file_path = "Ticket_detail_report_by_owner_flag_20260901_08.38.xlsx"

try:
    xls = pd.ExcelFile(file_path)
    sheets = xls.sheet_names
    print(f"Sheets: {sheets}")
    
    for sheet in sheets:
        print(f"\n--- Sheet: {sheet} ---")
        df = pd.read_excel(file_path, sheet_name=sheet)
        
        info = {
            "columns": df.columns.tolist(),
            "dtypes": df.dtypes.astype(str).to_dict(),
            "shape": df.shape,
            "missing_values": df.isnull().sum().to_dict(),
            "head": df.head(3).to_dict(orient="records"),
            "describe": df.describe(include='all').to_dict()
        }
        print(json.dumps(info, indent=2, default=str))

except Exception as e:
    print(f"Error: {e}")
