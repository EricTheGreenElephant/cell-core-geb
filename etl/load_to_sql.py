import os 
import struct
import pyodbc
import pandas as pd
from sqlalchemy import create_engine, text 
from streamlit_app.config import SQLALCHEMY_URL

def make_mssql_engine():
    """
    Creates a SQLAlchemy engine.

    - If Azure_SQL_ACCESS_TOKEN is present (e.g., in GitHub Actions),
      connects using AAD token (no username/password).
    - Otherwise, falls back to SQLALCHEMY_URL (local dev connection)
    """
    aad_token = os.getenv("AZURE_SQL_ACCESS_TOKEN")

    # Cloud / CI path: use AAD access token
    if aad_token:
        server = os.getenv("DB_SERVER")
        dbname = os.getenv("DB_NAME")
        driver = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")

        if not server or not dbname:
            raise RuntimeError(
                "DB_SERVER and DB_NAME must be set when using AZURE_SQL_ACCESS_TOKEN."
            )
        
        # Standard encrypted ODBC connection string
        odbc_str = (
            f"Driver={{{driver}}};"
            f"Server={server};"
            f"Database={dbname};"
            "Encrypt=yes;"
            "TrustServerCertificate=no;"
        )

        # Azure tokens must be UTF-16-LE bytes
        token_bytes = bytes(aad_token, "utf-16-le")
        token_struct = struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)

        SQL_COPT_SS_ACCESS_TOKEN = 1256

        def _creator():
            return pyodbc.connect(
                odbc_str,
                attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct}
            )
        
        return create_engine(
            "mssql+pyodbc:///?autocommit=False",
            creator=_creator,
            fast_executemany=True,
            future=True,      
        )
    return create_engine(
        SQLALCHEMY_URL, 
        fast_executemany=True,
        pool_pre_ping=True,
        future=True,      
    )

    # server = os.getenv("DB_SERVER", "localhost")
    # database = os.getenv("DB_NAME", "master")
    # auth = os.getenv("DB_AUTH_METHOD", "windows").lower()

    # if auth == "sql":
    #     username = os.getenv("DB_USERNAME")
    #     password = os.getenv("DB_PASSWORD")
    #     if not username or not password:
    #         raise ValueError("DB_USERNAME and DB_PASSWORD must be set for SQL auth.")

    #     conn_str = (
    #         f"mssql+pyodbc://{username}:{password}@{server}/{database}"
    #         "?driver=ODBC+Driver+18+for+SQL+Server"
    #         "&Encrypt=yes&TrustServerCertificate=yes"
    #     )

    # elif auth == "windows":
    #     conn_str = (
    #         f"mssql+pyodbc://@{server}/{database}"
    #         "?driver=ODBC+Driver+18+for+SQL+Server"
    #         "&Trusted_Connection=yes"
    #         "&Encrypt=yes&TrustServerCertificate=yes"
    #     )
    
    # else:
    #     raise ValueError(f"Unsupported DB_AUTH_METHOD: {auth}")
    
    # return create_engine(conn_str, fast_executemany=True, pool_pre_ping=True)

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
            chunksize=chunksize,
            method=None,
        )