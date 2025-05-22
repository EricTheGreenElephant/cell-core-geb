import pyodbc
from utils.db import db_connection
from streamlit_app.schemas.filament_schemas import FilamentInUse, FilamentCreate

def get_all_filament_statuses():
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM v_filament_status ORDER BY filament_id")
        cols = [col[0] for col in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
    
def get_active_filaments():
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                f.serial_number,
                f.qc_result,
                f.weight_grams AS initial_weight,
                f.received_at,
                sl.location_name,
                'Storage' AS status,
                NULL AS moved_at,
                NULL AS ready_at                 
            FROM filaments f
            LEFT JOIN storage_locations sl ON f.location_id = sl.id
            WHERE f.id NOT IN (
                SELECT filament_id FROM filament_acclimatization
                WHERE status IN ('In Acclimatization', 'In Production')
            )
            UNION
            
            SELECT 
                f.serial_number,
                f.qc_result,
                f.weight_grams AS initial_weight,
                f.received_at,
                sl.location_name,
                fa.status,
                fa.moved_at,
                fa.ready_at
            FROM filaments f
            JOIN filament_acclimatization fa ON f.id = fa.filament_id
            LEFT JOIN storage_locations sl ON f.location_id = sl.id
            WHERE fa.status = 'In Acclimatization'
        """)
        cols = [col[0] for col in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
    
def get_archived_filaments():
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                f.serial_number,
                f.qc_result,
                f.weight_grams AS initial_weight,
                fm.remaining_weight,
                p.name AS printer_name,
                fm.status,
                fm.mounted_at,
                fm.unmounted_at,
                u.display_name AS unmounted_by
            FROM filaments f
            JOIN filament_mounting fm ON f.id = fm.filament_id
            LEFT JOIN printers p ON fm.printer_id = p.id
            LEFT JOIN users u on fm.unmounted_by = u.id
            WHERE fm.unmounted_at IS NOT NULL
        """)
        cols = [col[0] for col in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
    
def get_in_use_filaments(): 
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                f.id,
                f.serial_number,
                f.qc_result,
                f.weight_grams AS initial_weight,
                fm.remaining_weight,
                p.name AS printer_name,
                fm.mounted_at,
                f.received_at,
                u.display_name AS received_by,
                sl.location_name
            FROM filaments f
            JOIN filament_mounting fm ON f.id = fm.filament_id
            JOIN printers p ON fm.printer_id = p.id
            LEFT JOIN users u ON f.received_by = u.id
            LEFT JOIN storage_locations sl ON f.location_id = sl.id
            WHERE fm.unmounted_at IS NULL
        """)
        cols = [col[0] for col in cursor.description]
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
        return [FilamentInUse(**row) for row in rows]
    
def get_filaments():
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    f.id,
                    f.serial_number,
                    f.weight_grams AS initial_weight,
                    fm.remaining_weight,
                    f.qc_result,
                    f.received_at,
                    loc.location_name AS storage_location,
                    u.display_name AS received_by,
                    p.name AS printer_name

                FROM filaments f
                LEFT JOIN filament_mounting fm ON f.id = fm.filament_id AND fm.unmounted_at IS NULL
                LEFT JOIN printers p ON fm.printer_id = p.id
                LEFT JOIN storage_locations loc ON f.location_id = loc.id
                LEFT JOIN users u ON f.received_by = u.id
                ORDER BY f.id ASC"""
            )
            rows = cursor.fetchall()
            cols = [col[0] for col in cursor.description]
            return  [dict(zip(cols, row)) for row in rows]
    except pyodbc.Error as e:
        print(f"Database error: {e}")
        return []

def get_low_filaments(threshold=2500):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT fm.id, f.serial_number, fm.remaining_weight, p.name AS printer_name
            FROM filament_mounting fm
            JOIN filaments f ON fm.filament_id = f.id
            JOIN printers p ON fm.printer_id = p.id
            WHERE fm.remaining_weight < ?
        """, (threshold,))
        cols = [col[0] for col in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

def get_storage_locations():
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, location_name, location_type, description 
                FROM storage_locations 
                ORDER BY location_name
            """)
            cols = [col[0] for col in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
            
    except pyodbc.Error as e:
        print(f"[DB ERROR] Failed to fetch locations: {e}")
        return []
    
# def insert_filament(serial_number, weight_grams, location_id, qc_result, received_by):
def insert_filament(data: FilamentCreate):
    try: 
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                        INSERT INTO filaments (serial_number, weight_grams, location_id, qc_result, received_by)
                        VALUES (?, ?, ?, ?, ?)
                        """, (data.serial_number, data.weight_grams, data.location_id, data.qc_result, data.received_by))
            conn.commit()
    except pyodbc.Error as e:
        raise RuntimeError(f"[DB INSERT ERROR] {e}")
    
def get_acclimatized_filaments():
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT f.id, f.serial_number, f.weight_grams,
                    a.id AS acclimatization_id, a.ready_at, loc.location_name
                FROM filament_acclimatization a
                JOIN filaments f ON a.filament_id = f.id
                JOIN storage_locations loc ON f.location_id = loc.id
                WHERE a.ready_at <= GETDATE()
                AND a.status = 'In Acclimatization'
                AND NOT EXISTS (
                    SELECT 1 FROM filament_mounting m WHERE m.filament_id = f.id
                )
                ORDER BY a.ready_at ASC
            """)
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except pyodbc.Error as e:
        print(f"[DB ERROR] Failed to fetch acclimatized filaments: {e}")
        return []
    
def get_available_printers():
    try: 
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.id, p.name
                FROM printers p
                WHERE p.status = 'Active'
                AND p.id NOT IN (
                    SELECT printer_id
                    FROM filament_mounting
                    WHERE unmounted_at IS NULL
                )
            """)
            cols = [col[0] for col in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
    except pyodbc.Error as e:
        print(f"[DB ERROR] Failed to fetch printers: {e}")
        return []
    
def insert_filament_mount(filament_id, printer_id, mounted_by, acclimatization_id):
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            # Get the initial filament weight 
            cursor.execute("SELECT weight_grams FROM filaments WHERE id = ?", (filament_id))
            row = cursor.fetchone()
            if not row:
                raise ValueError("Filament not found.")
            
            full_weight = row[0]

            # Insert filament mounting data
            cursor.execute("""
                           INSERT INTO filament_mounting (filament_id, printer_id, mounted_by, remaining_weight)
                           VALUES (?, ?, ?, ?)
                           """, (filament_id, printer_id, mounted_by, full_weight))

            # Update filament on filament_acclimatization table to In Production
            cursor.execute("""
                           UPDATE filament_acclimatization
                           SET status = 'In Production'
                           WHERE id = ?
                           """, (acclimatization_id,))
            conn.commit()
    except pyodbc.Error as e:
        print(f"[DB ERROR] Failed to create filament mounting: {e}")
        return []
    
def get_mounted_filaments():
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                fm.id AS mount_id,
                f.serial_number,
                p.name AS printer_name,
                fm.remaining_weight
            FROM filament_mounting fm
            JOIN filaments f ON fm.filament_id = f.id
            JOIN printers p ON fm.printer_id = p.id
            WHERE fm.unmounted_at IS NULL
            ORDER BY p.name
        """)
        cols = [col[0] for col in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
    
def unmount_filament(mount_id: int, user_id: int):
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE filament_mounting
                SET unmounted_at = GETDATE(),
                    unmounted_by = ?,
                    status = 'Unmounted'
                WHERE id = ?
            """, (user_id, mount_id))
            conn.commit()
    except Exception as e:
        raise RuntimeError(f"[DB ERROR] Failed to unmount filament: {e}")
    
def get_filaments_not_acclimatizing():
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT f.id, f.serial_number
            FROM filaments f
            WHERE f.qc_result = 'PASS'
                AND f.id NOT IN (
                    SELECT filament_id
                    FROM filament_acclimatization
                    WHERE status IN ('In Acclimatization', 'In Production')
                )
        """)
        cols = [col[0] for col in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
    
def insert_filament_acclimatization(filament_id: int, user_id: int):
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO filament_acclimatization (filament_id, status, moved_at, moved_by)
                VALUES (?, 'In Acclimatization', GETDATE(), ?)
            """, (filament_id, user_id))
            conn.commit()
    except Exception as e:
        raise RuntimeError(f"[DB ERROR] Failed to insert filament acclimatization: {e}")
    