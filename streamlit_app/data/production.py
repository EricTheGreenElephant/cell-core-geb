import pyodbc
from datetime import datetime
from utils.db import db_connection

def get_product_types():
    try: 
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM product_types ORDER BY name")
            rows = cursor.fetchall()
            return [(row[0], row[1]) for row in rows]
    except pyodbc.Error as e:
        print(f"[DB ERROR] Failed to fetch product types: {e}")
        return []
    
def generate_lot_number():
    timestamp = datetime.now().strftime("%Y%m%d%H%S")
    return f"LOT-{timestamp}"
    
def insert_product_request(requested_by, product_id, quantity, notes=""):
    lot = generate_lot_number()
    try: 
        with db_connection() as conn:
            cursor = conn.cursor()
            for _ in range(quantity):
                cursor.execute("""
                            INSERT INTO product_requests (requested_by, product_id, lot_number, notes)
                            VALUES (?, ?, ?, ?)
                            """, (requested_by, product_id, lot, notes))
            conn.commit()
    except pyodbc.Error as e:
        raise RuntimeError(f"[DB INSERT ERROR] {e}")
    

def get_pending_requests(): 
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
                    SELECT 
                        pr.id,
                        pt.name AS product_type,
                        u.display_name AS requested_by,
                        pr.lot_number,
                        pr.status,
                        pr.requested_at,
                        pt.average_weight,
                        pt.percentage_change
                    FROM product_requests pr
                    JOIN product_types pt ON pt.id = pr.product_id
                    JOIN users u ON u.id = pr.requested_by
                    WHERE pr.status = 'Pending'
                    ORDER BY pr.requested_at ASC
                """)
        cols = [col[0] for col in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
    

def get_active_filament_mount():
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
                    SELECT fm.id, f.serial_number, p.name AS printer_name, fm.remaining_weight
                    FROM filament_mounting fm
                    JOIN filaments f ON fm.filament_id = f.id
                    JOIN printers p ON fm.printer_id = p.id
                    WHERE fm.remaining_weight > 0
                """)
        return cursor.fetchall()
    
def get_mountable_filament_mounts(required_weight: float):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                fm.id,
                f.serial_number,
                p.name AS printer_name,
                fm.remaining_weight
            FROM filament_mounting fm
            JOIN filaments f ON fm.printer_id = f.id
            JOIN printers p ON fm.printer_id = p.id
            WHERE fm.remaining_weight >= ?
                AND fm.unmounted_at IS NULL
        """, (required_weight,))
        cols = [col[0] for col in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
    

def insert_product_harvest(request_id, filament_mount_id, printed_by):
    with db_connection() as conn:
        cursor = conn.cursor()

        # Insert into product_harvest
        cursor.execute("""
                    INSERT INTO product_harvest (request_id, filament_mounting_id, printed_by, print_date, print_status)
                    OUTPUT INSERTED.id
                    VALUES (?, ?, ?, GETDATE(), 'Printed')
                """, (request_id, filament_mount_id, printed_by))
        harvest_id = cursor.fetchone()[0]
        
        # Insert into product_tracking
        cursor.execute("""
                    INSERT INTO product_tracking (harvest_id, current_status, last_updated_at)
                    VALUES (?, 'Printed', GETDATE())
                """, (harvest_id,))
 
        # Update product_requests status
        cursor.execute("""
                    UPDATE product_requests
                    SET status = 'Fulfilled'
                    WHERE id = ?
                """, (request_id,))
        conn.commit()
        
def cancel_product_request(request_id):
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                        UPDATE product_requests
                        SET status = 'Cancelled'
                        WHERE id = ?
                    """, (request_id,))
            conn.commit()
    except pyodbc.Error as e:
        raise RuntimeError(f"[DB UPDATE ERROR] {e}")