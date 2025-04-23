from utils.db import db_connection


def get_all_product_status():
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM v_product_status ORDER BY last_updated_at DESC")
            cols = [col[0] for col in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
    except Exception as e:
        raise RuntimeError(f"[DB ERROR] Failed to fetch product status: {e}")
    