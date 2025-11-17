import os
from dotenv import load_dotenv
from extract_from_excel import read_table_from_excel


load_dotenv()
df = read_table_from_excel(os.environ["EXCEL_PATH"], os.getenv("EXCEL_SHEET", "Data"), os.getenv("EXCEL_START","D12"))
print(df.head(20).to_string(index=False))
print("\nRows:", len(df), " | Cols:", df.shape[1])
print("\nNulls (top 20):")
print(df.isna().sum().sort_values(ascending=False).head(20))
df.to_csv("etl/data/_staging_preview.csv", index=False)
print("\nWrote CSV preview to etl/data/_staging_preview.csv")