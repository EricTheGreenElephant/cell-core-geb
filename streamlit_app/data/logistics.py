import pyodbc
from utils.db import db_connection


def get_qc_passed_products():
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                pt.id AS tracking_id,
                pt.current_status,
                pt.last_updated_at,
                ph.id AS harvest_id,
                ptype.name AS product_type,
                pqc.inspection_result,
                loc.location_name
            FROM product_tracking pt
            JOIN product_harvest ph ON pt.harvest_id = ph.id
            JOIN product_requests pr ON ph.request_id = pr.id
            JOIN product_types ptype ON pr.product_id = ptype.id
            JOIN product_quality_control pqc ON ph.id = pqc.harvest_id
            LEFT JOIN storage_locations loc ON pt.location_id = loc.id
            WHERE pt.current_status = 'In Interim Storage'
                AND pt.id NOT IN (
                    SELECT product_id FROM treatment_batch_products
                )
        """)
        cols = [col[0] for col in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
    
def create_treatment_batch(sent_by_id: int, tracking_data: list[dict], notes=None):
    try:
        with db_connection() as conn:
            cursor = conn.cursor()

            # Insert new treatment batch
            cursor.execute("""
                INSERT INTO treatment_batches (sent_by, sent_at, status, notes)
                OUTPUT INSERTED.id
                VALUES (?, GETDATE(), 'Shipped', ?)
            """, (sent_by_id, notes))
            batch_id = cursor.fetchone()[0]

            # Link products to this batch
            for item in tracking_data:
                cursor.execute("""
                    INSERT INTO treatment_batch_products (batch_id, product_id, surface_treat, sterilize)
                    VALUES (?, ?, ?, ?)
                """, (
                    batch_id, 
                    item["tracking_id"],
                    int(item["surface_treat"]),
                    int(item["sterilize"])
                ))

                # Update product status
                cursor.execute("""
                    UPDATE product_tracking
                    SET current_status = 'Sent for Treatment', last_updated_at = GETDATE()
                    WHERE id = ?
                """, (item["tracking_id"],))

            conn.commit()

    except Exception as e:
        raise RuntimeError(f"[DB ERROR] Failed to create treatment batch: {e}")

def get_qc_products_needing_storage():
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                pt.id AS tracking_id,
                pt.current_status,
                pt.location_id,
                ph.id AS harvest_id,
                pt.harvest_id,
                pt.last_updated_at,
                pqc.inspection_result,
                f.serial_number AS filament_serial,
                ptype.name AS product_type,
                u.display_name AS printed_by,
                ph.print_date
            FROM product_tracking pt
            JOIN product_harvest ph ON pt.harvest_id = ph.id
            JOIN product_quality_control pqc ON pqc.harvest_id = ph.id
            JOIN filament_mounting fm ON ph.filament_mounting_id = fm.id
            JOIN filaments f ON fm.filament_id = f.id
            JOIN product_requests pr ON ph.request_id = pr.id
            JOIN product_types ptype ON pr.product_id = ptype.id
            LEFT JOIN users u ON ph.printed_by = u.id
            WHERE pt.location_id IS NULL
                AND pqc.inspection_result IN ('Passed', 'B-Ware', 'Quarantine')
                AND pt.id NOT IN (
                       SELECT product_id FROM treatment_batch_products
                )
        """)
        cols = [col[0] for col in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
    
def assign_storage_to_products(product_ids: list[int], location_id: int, status: str):
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            for pid in product_ids:
                cursor.execute("""
                    UPDATE product_tracking
                    SET location_id = ?, current_status = ?, last_updated_at = GETDATE()
                    WHERE id = ?
                """, (location_id, status, pid))
            conn.commit()
    except Exception as e:
        raise RuntimeError(f"[DB ERROR] Failed to assign storage: {e}")

def get_shipped_batches():
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, sent_at, notes
            FROM treatment_batches
            WHERE status = 'Shipped'
            ORDER BY sent_at DESC
        """)
        cols = [col[0] for col in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
    
def get_products_by_batch_id(batch_id: int):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                tbp.id,
                pt.id AS tracking_id,
                pt.current_status,
                pt.location_id,
                t.name AS product_type,
                pqc.inspection_result,
                tbp.surface_treat,
                tbp.sterilize,
                NULL AS visual_pass
            FROM treatment_batch_products tbp
            JOIN product_tracking pt ON tbp.product_id = pt.id
            JOIN product_harvest ph ON ph.id = pt.harvest_id
            JOIN product_requests pr ON pr.id = ph.request_id
            JOIN product_types t ON t.id = pr.product_id
            LEFT JOIN product_quality_control pqc ON ph.id = pqc.harvest_id
            WHERE tbp.batch_id = ?
        """, (batch_id, ))
        cols = [col[0] for col in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
    
def update_post_treatment_qc(product_qc: list[dict], inspected_by: int):
    with db_connection() as conn:
        cursor = conn.cursor()

        for item in product_qc:
            cursor.execute("""
                INSERT INTO post_treatment_inspections (
                    product_id, surface_treated, sterilized, visual_pass, qc_result, inspected_by
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                item["tracking_id"],
                item["surface_treat"],
                item["sterilize"],
                item["visual_pass"],
                item["qc_result"],
                inspected_by
            ))

            cursor.execute("""
                UPDATE product_tracking
                SET current_status = 'Post-Treatment Inspected',
                    last_updated_at = GETDATE()
                WHERE id = ?
            """, (item["tracking_id"],))
        
        conn.commit()

def mark_batch_as_inspected(batch_id: int):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE treatment_batches
            SET status = 'Inspected', received_at = GETDATE()
            WHERE id = ?
        """, (batch_id,))
        conn.commit()

def get_post_treatment_products_needing_storage():
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    pt.id AS tracking_id,
                    ph.id AS harvest_id,
                    t.name AS product_type,
                    pqi.qc_result AS inspection_result
                FROM product_tracking pt
                JOIN product_harvest ph ON pt.harvest_id = ph.id
                JOIN product_requests pr ON pr.id = ph.request_id
                JOIN product_types t ON pr.product_id = t.id
                JOIN post_treatment_inspections pqi ON pt.id = pqi.product_id
                WHERE pt.current_status IN ('Post-Treatment Inspected')
                    AND pqi.qc_result IN ('Internal Use', 'QM Request')
            """)
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except pyodbc.Error as e:
        raise RuntimeError(f"[DB ERROR] Failed to fetch post-treatment products: {e}")