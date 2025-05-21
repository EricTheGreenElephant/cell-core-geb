import pyodbc
from utils.db import db_connection


VALID_TABLES = {
    "Filaments": "filaments",
    "Products": "product_tracking",
    "Lids": "lids"
}

def get_product_record(tracking_id):
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    pt.id AS tracking_id, 
                    pt.current_status, 
                    pt.location_id, 
                    pti.visual_pass, 
                    pti.surface_treated, 
                    pti.sterilized, 
                    pti.qc__result
                FROM product_tracking pt
                LEFT JOIN post_treatment_inspections pti ON pt.id = pti.product_id
                WHERE pt.id = ?
            """, (tracking_id,))
            row = cursor.fetchone()
            if not row:
                return None
            columns = [col[0] for col in cursor.description]
            return dict(zip(columns, row))
    except Exception as e:
        print(f"[DB ERROR] Failed to fetch record: {e}" )
        return None
    
def update_product_field(tracking_id, field, new_value, user_id):
    try:
        with db_connection() as conn:
            cursor = conn.cursor()

            # Log the change
            cursor.execute("""
                INSERT INTO audit_log (product_id, field_name, new_value, changed_by)
                VALUES (?, ?, ?, ?)
            """, (tracking_id, field, str(new_value), user_id))

            # Update record
            cursor.execute(f"""
                UPDATE product_tracking
                SET {field} = ?
                WHERE id = ?
            """, (new_value, tracking_id))

            conn.commit()
            return True
    except Exception as e:
        print(f"[DB ERROR] Failed to update field: {e}")
        return False
    

def get_all_filaments():
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, serial_number FROM filaments ORDER BY serial_number")
            rows = cursor.fetchall()
            return [dict(zip([col[0] for col in cursor.description], row)) for row in rows]
    except pyodbc.Error as e:
        raise RuntimeError(f"[DB ERROR] Failed to fetch filaments: {e}")
    
def get_all_product_ids():
    try: 
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM product_tracking ORDER BY id")
            rows = cursor.fetchall()
            return [{"id": row[0]} for row in rows]
    except pyodbc.Error as e:
        raise RuntimeError(f"[DB ERROR] Failed to fetch product IDs: {e}")
    
def get_all_lids():
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, serial_number FROM lids ORDER BY serial_number")
            rows = cursor.fetchall()
            return [dict(zip([col[0] for col in cursor.description], row)) for row in rows]
    except pyodbc.Error as e:
        raise RuntimeError(f"[DB ERROR] Failed to fetch lids: {e}")
    
def get_record_by_id(table_name: str, record_id: int):
    try:
        with db_connection() as conn:
            cursor = conn.cursor()

            if table_name not in VALID_TABLES:
                raise ValueError("Invalidd table name")
            
            safe_table = VALID_TABLES[table_name]
            cursor.execute(f"SELECT * FROM {safe_table} WHERE id = ?", (record_id,))
            row = cursor.fetchone()
            if not row:
                return None
            cols = [col[0] for col in cursor.description]
            return dict(zip(cols, row))
    except pyodbc.Error as e:
        raise RuntimeError(f"[DB ERROR] Failed to fetch record from {table_name}: {e}")
    
def update_record_with_audit(table_name: str, record_id: int, changes: dict, user_id: int):
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            if table_name not in VALID_TABLES:
                raise ValueError("Invalidd table name")
            
            safe_table = VALID_TABLES[table_name]
            for field, change in changes.items():
                old_value = change["old"]
                new_value = change["new"]

                # 1. Update field in table
                query = f"UPDATE {safe_table} SET {field} = ? WHERE id = ?"
                cursor.execute(query, (new_value, record_id))

                # 2. Insert audit Log entry
                cursor.execute("""
                    INSERT INTO audit_log (table_name, record_id, field_name, old_value, new_value, changed_by)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (table_name, record_id, field, str(old_value), str(new_value), user_id))
            
            conn.commit()
    except pyodbc.Error as e:
        raise RuntimeError(f"[DB ERROR] Failed to update record or log audit: {e}")