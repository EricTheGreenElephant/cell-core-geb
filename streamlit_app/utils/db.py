# import pyodbc
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from config import SQLALCHEMY_URL
from db.base import get_engine
# from config import CONNECTION_STRING


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
    """Quick helper to run a SQL string and return rows as dicts."""
    with db_connection() as conn:
        result = conn.execute(text(sql), params or {})
        return [dict(row) for row in result]
# @contextmanager
# def db_connection():
#     conn = None
#     try: 
#         conn = pyodbc.connect(CONNECTION_STRING)
#         yield conn
#     except pyodbc.Error as e:
#         raise RuntimeError(f"[DB ERROR] Failed to connect to database: {e}")
#     finally:
#         if conn:
#             conn.close()