import os 
import pandas as pd
from sqlalchemy import create_engine, text 

def make_mssql_engine():
    server = os.getenv("DB_SERVER", "localhost")
    database = os.getenv("DB_NAME", "master")
    auth = os.getenv("DB_AUTH_METHOD", "windows").lower()

    if auth == "sql":
        username = os.getenv("DB_USERNAME")
        password = os.getenv("DB_PASSWORD")
        if not username or not password:
            raise ValueError("DB_USERNAME and DB_PASSWORD must be set for SQL auth.")

        conn_str = (
            f"mssql+pyodbc://{username}:{password}@{server}/{database}"
            "?driver=ODBC+Driver+18+for+SQL+Server"
            "&Encrypt=yes&TrustServerCertificate=yes"
        )

    elif auth == "windows":
        conn_str = (
            f"mssql+pyodbc://@{server}/{database}"
            "?driver=ODBC+Driver+18+for+SQL+Server"
            "&Trusted_Connection=yes"
            "&Encrypt=yes&TrustServerCertificate=yes"
        )
    
    else:
        raise ValueError(f"Unsupported DB_AUTH_METHOD: {auth}")
    
    return create_engine(conn_str, fast_executemany=True, pool_pre_ping=True)

def load_staging(
        df: pd.DataFrame,
        table: str = "stg_excel_data",
        schema: str = "dbo",
        truncate: bool = True,
        chunksize: int = 5_000
):
    if df is None or df.empty:
        raise ValueError("load_staging: DataFrame is empty.")
    
    eng = make_mssql_engine()
    with eng.begin() as conn:
        if truncate:
            conn.execute(text(
                f"IF OBJECT_ID('{schema}.{table}', 'U') IS NOT NULL "
                f"TRUNCATE TABLE {schema}.{table};"
            ))
        df.to_sql(
            name=table,
            con=conn,
            schema=schema,
            if_exists="append",
            index=False,
            chunksize=chunksize
        )