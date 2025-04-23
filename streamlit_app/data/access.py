import pyodbc
from utils.db import db_connection

def get_user_access(user_id):
    try: 
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                        SELECT a.area_name, ar.access_level
                        FROM access_rights ar
                        JOIN application_areas a ON a.id = ar.area_id
                        WHERE ar.user_id = ? 
                        """, (user_id))
            rows = cursor.fetchall()
            return {row[0]: row[1] for row in rows}
    except pyodbc.Error as e:
        print(f"[ACCESS ERROR] {e}")
        return []