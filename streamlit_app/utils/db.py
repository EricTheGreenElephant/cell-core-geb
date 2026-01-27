# import pyodbc
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from config import SQLALCHEMY_URL
from db.base import get_engine
# from config import CONNECTION_STRING

# debug 
import os, time
import streamlit as st

def _db_debug_banner():
    # show only non-secret config
    st.write({
        "DB_AUTH_METHOD": os.getenv("DB_AUTH_METHOD"),
        "DB_SERVER": os.getenv("DB_SERVER"),
        "DB_NAME": os.getenv("DB_NAME"),
        "DB_DRIVER": os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server"),
        "WEBSITE_SITE_NAME": os.getenv("WEBSITE_SITE_NAME"),
        "IDENTITY_ENDPOINT_set": bool(os.getenv("IDENTITY_ENDPOINT")),
        "IDENTITY_HEADER_set": bool(os.getenv("IDENTITY_HEADER")),
        "MSI_ENDPOINT_set": bool(os.getenv("MSI_ENDPOINT")),  # older
        "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })

@contextmanager
def db_connection():
    """
    Provides a transactional scope around a database connection.
    Uses SQLAlchemy connection pooling for performance and reliability.
    """
    conn = None
    try:
        conn = get_engine().connect()
        yield conn 
    except SQLAlchemyError as e:
        raise RuntimeError(f"[DB ERROR] {e}")
    finally:
        if conn: 
            conn.close()

# Currently unused - could be used for future versions to cut down on code.
def run_query(sql: str, params: dict | None = None):
    if os.getenv("DB_DEBUG", "0") == "1":
        _db_debug_banner()

    """Quick helper to run a SQL string and return rows as dicts."""
    # with db_connection() as conn:
    #     result = conn.execute(text(sql), params or {})
    #     return [dict(row) for row in result]
