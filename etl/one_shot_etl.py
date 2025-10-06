from pathlib import Path 
from dotenv import load_dotenv
import re
from sqlalchemy import text 

from extract_from_excel import read_table_from_excel
from load_to_sql import load_staging, make_mssql_engine

load_dotenv()

def main():
    path = "etl/data/2025825_Backup-ExcelTool_ErSi_Copy.xlsm"
    df = read_table_from_excel(
        Path(path),
        sheet_name="Flaschen",
        start_cell="D12"
    )

    df2 = read_table_from_excel(
        Path(path),
        sheet_name="Filament",
        start_cell="E12"
    )

    df3 = read_table_from_excel(
        Path(path),
        sheet_name="TreatmentID",
        start_cell="G12"
    )

    df4 = read_table_from_excel(
        Path(path),
        sheet_name="VCID",
        start_cell="D22"
    )

    load_staging(df, table="stg_excel_data", schema="dbo", truncate=True)
    load_staging(df2, table="stg_filament_excel_data", schema="dbo", truncate=True)
    load_staging(df3, table="stg_treatment_excel_data", schema="dbo", truncate=True)
    load_staging(df4, table="stg_vcid_excel_data", schema="dbo", truncate=True)
    

    engine = make_mssql_engine()
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT COUNT(*) FROM dbo.stg_excel_data")).scalar()
        print(f"[INFO] Rows in staging: {rows}")

    # sql_file = Path("etl/transform.sql")
    # if sql_file.exists():
    #     transform_sql = sql_file.read_text(encoding="utf-8")
    #     with engine.begin() as conn:
    #         conn.execute(text(transform_sql))
    #     print("[INFO] Transform.sql executed")

if __name__ == "__main__":
    main()