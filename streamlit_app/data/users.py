import pyodbc
from utils.db import db_connection

def get_user_by_email(email):
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, display_name FROM users WHERE user_principal_name = ?", (email,))
            result = cursor.fetchone()
            return result
    except pyodbc.Error as e:
        print(f"[DB ERROR] Failed to fetch user: {e}")
        return None