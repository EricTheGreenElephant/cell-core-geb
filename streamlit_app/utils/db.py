import pyodbc
from contextlib import contextmanager
from config import CONNECTION_STRING

@contextmanager
def db_connection():
    conn = None
    try: 
        conn = pyodbc.connect(CONNECTION_STRING)
        yield conn
    except pyodbc.Error as e:
        raise RuntimeError(f"[DB ERROR] Failed to connect to database: {e}")
    finally:
        if conn:
            conn.close()