from pathlib import Path 
from dotenv import load_dotenv
import re
from sqlalchemy import text 

from extract_from_excel import read_table_from_excel
from load_to_sql import load_staging, make_mssql_engine

load_dotenv()


def exec_and_print_all(conn, sql: str):
    """
    Execute a T-SQL batch that may return multiple result sets (SELECTs),
    and print each one with headers.
    """
    result = conn.exec_driver_sql(sql)
    cur = result.cursor  # DBAPI cursor (pyodbc)
    rs_idx = 0
    while True:
        if cur.description:  # there is a result set here
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
            rs_idx += 1
            print(f"\n[RESULT SET {rs_idx}] {', '.join(cols)}")
            for r in rows:
                print("  " + " | ".join("" if v is None else str(v) for v in r))
        # Move to next result set; break when none
        if not cur.nextset():
            break

def main():
    # path = "etl/data/2025825_Backup-ExcelTool_ErSi_Copy.xlsm"
    # df = read_table_from_excel(
    #     Path(path),
    #     sheet_name="Flaschen",
    #     start_cell="D12"
    # )

    # df2 = read_table_from_excel(
    #     Path(path),
    #     sheet_name="Filament",
    #     start_cell="E12"
    # )

    # df3 = read_table_from_excel(
    #     Path(path),
    #     sheet_name="TreatmentID",
    #     start_cell="G12"
    # )

    # df4 = read_table_from_excel(
    #     Path(path),
    #     sheet_name="VCID",
    #     start_cell="D22"
    # )

    # load_staging(df, table="stg_excel_data", schema="dbo", truncate=True)
    # load_staging(df2, table="stg_filament_excel_data", schema="dbo", truncate=True)
    # load_staging(df3, table="stg_treatment_excel_data", schema="dbo", truncate=True)
    # load_staging(df4, table="stg_vcid_excel_data", schema="dbo", truncate=True)
    

    engine = make_mssql_engine()
    # with engine.begin() as conn:
    #     rows = conn.execute(text("SELECT COUNT(*) FROM dbo.stg_excel_data")).scalar()
    #     print(f"[INFO] Rows in staging: {rows}")

    sql_file = Path("etl/transform_filaments_debug.sql")
    if sql_file.exists():
        transform_sql = sql_file.read_text(encoding="utf-8-sig")
        with engine.begin() as conn:
            exec_and_print_all(conn, transform_sql)  # <-- prints staging_rows, resolved_rows, inserts/updates, etc.
        print("[INFO] filaments upsert complete.")

        # Quick post-checks
        with engine.begin() as conn:
            staged = conn.execute(text("SELECT COUNT(*) FROM dbo.stg_filament_excel_data")).scalar()
            live   = conn.execute(text("SELECT COUNT(*) FROM dbo.filaments")).scalar()
            print(f"[CHECK] staging rows: {staged} | filaments rows now: {live}")

if __name__ == "__main__":
    main()