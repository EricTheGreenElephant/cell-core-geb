import pyodbc
from utils.db import db_connection


def get_lid_inventory():
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM v_lid_inventory ORDER BY received_at DESC")
            cols = [col[0] for col in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
    except pyodbc.Error as e:
        print(f"[DB ERROR] Failed to fetch lid inventory: {e}")
        return []
    
def insert_lid(serial_number, location_id, qc_result, received_by):
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO lids (serial_number, location_id, qc_result, received_by)
                VALUES (?, ?, ?, ?)
            """, (serial_number, location_id, qc_result, received_by))
            conn.commit()
    except pyodbc.Error as e:
        raise RuntimeError(f"[DB ERROR] Failed to insert lid: {e}")