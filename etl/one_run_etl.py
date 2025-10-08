from __future__ import annotations
from pathlib import Path
import argparse, hashlib, json, os
from dotenv import load_dotenv
from sqlalchemy import text

from extract_from_excel import read_table_from_excel
from load_to_sql import load_staging, make_mssql_engine

CACHE_PATH = Path("etl/.sheet_cache.json")

def sha256_df(df) -> str:
    return hashlib.sha256(df.to_csv(index=False).encode("utf-8")).hexdigest()

def load_cache() -> dict:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {}

def save_cache(cache: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2), encoding="utf-8")

def stage_sheet(path: Path, sheet_name: str, start_cell: str, table: str,
                do_truncate: bool, smart: bool, only: set[str] | None):
    label = table
    if only and label not in only:
        return

    print(f"[EXTRACT] {sheet_name} @{start_cell} -> {table}")
    df = read_table_from_excel(path, sheet_name=sheet_name, start_cell=start_cell)
    if df.empty:
        print(f"[WARN] {sheet_name} produced 0 rows; skipping stage.")
        return

    cache = load_cache()
    new_hash = sha256_df(df)
    old_hash = cache.get(label)
    if smart and old_hash == new_hash:
        print(f"[SKIP] {table}: unchanged (smart cache).")
        return

    load_staging(df, table=table, schema="dbo", truncate=do_truncate)
    print(f"[STAGED] {table}: {len(df)} rows. truncate={do_truncate}")
    cache[label] = new_hash
    save_cache(cache)

def run_transform(sql_path: Path, label: str, only: set[str] | None):
    if only and label not in only:
        return
    if not sql_path.exists():
        print(f"[SKIP] {label}: {sql_path} not found.")
        return
    sql = sql_path.read_text(encoding="utf-8-sig")
    eng = make_mssql_engine()
    with eng.begin() as conn:
        conn.exec_driver_sql(sql)
        # minimal post-check if relevant
        if label == "filaments":
            live = conn.execute(text("SELECT COUNT(*) FROM dbo.filaments")).scalar()
            print(f"[TRANSFORMED] {label} | filaments row count now: {live}")
        else:
            print(f"[TRANSFORMED] {label}")

def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="One-shot ETL")
    parser.add_argument("--excel", default=os.getenv("EXCEL_PATH", "etl/data/2025825_Backup-ExcelTool_ErSi_Copy.xlsm"))
    parser.add_argument("--no-truncate", action="store_true", help="Do not truncate staging tables before loading.")
    parser.add_argument("--no-stage", action="store_true", help="Skip all staging loads.")
    parser.add_argument("--no-transform", action="store_true", help="Skip all transforms.")
    parser.add_argument("--smart", action="store_true", help="Skip staging if sheet content unchanged since last run.")
    parser.add_argument("--only", nargs="*", default=[],
                        help=("Restrict to specific labels. Labels: "
                              "stg_excel_data, stg_filament_excel_data, stg_treatment_excel_data, stg_vcid_excel_data, filaments"))
    args = parser.parse_args()
    only_set = set(args.only) if args.only else None

    excel_path = Path(args.excel)

    # Staging ranges
    ranges = {
        "stg_excel_data":            ("Flaschen",   "D12"),
        "stg_filament_excel_data":   ("Filament",   "E12"),
        "stg_treatment_excel_data":  ("TreatmentID","G12"),
        "stg_vcid_excel_data":       ("VCID",       "D22"),
    }

    if not args.no_stage:
        for label, (sheet, cell) in ranges.items():
            stage_sheet(excel_path, sheet, cell, table=label,
                        do_truncate=not args.no_truncate, smart=args.smart, only=only_set)
        # Optional quick count
        eng = make_mssql_engine()
        with eng.begin() as conn:
            rows = conn.execute(text("SELECT COUNT(*) FROM dbo.stg_filament_excel_data")).scalar()
            print(f"[INFO] Rows in dbo.stg_filament_excel_data: {rows}")

    if not args.no_transform:
        run_transform(Path("etl/transform_filaments.sql"), "filaments", only_set)
        run_transform(Path("etl/transform_filament_mounting.sql"), "filament_mounting", only_set)

if __name__ == "__main__":
    main()