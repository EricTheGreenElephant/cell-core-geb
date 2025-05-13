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
            WHERE pt.current_status IN ('QC Passed', 'QC B-Ware')
                AND pt.id NOT IN (
                    SELECT product_id FROM treatment_batch_products
                )
        """)
        cols = [col[0] for col in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
    
def create_treatment_batch(sent_by_id, product_ids, notes=None):
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
        for pid in product_ids:
            cursor.execute("""
                INSERT INTO treatment_batch_products (batch_id, product_id)
                VALUES (?, ?)
            """, (batch_id, pid))

            # Update product status
            cursor.execute("""
                UPDATE product_tracking
                SET current_status = 'Sent for Treatment', last_updated_at = GETDATE()
                WHERE id = ?
            """, (pid,))

        conn.commit()

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
    
def assign_storage_to_products(product_ids: list[int], location_id: int):
    with db_connection() as conn:
        cursor = conn.cursor()

        # Conver list of IDs into placeholders
        placeholders = ",".join("?" for _ in product_ids)

        cursor.execute(f"""
            UPDATE product_tracking
            SET 
                location_id = ?,
                current_status =
                       CASE pqc.inspection_result
                            WHEN 'Quarantine' THEN 'In Quarantine'
                            ELSE 'In Interim Storage'
                       END
            FROM product_tracking pt
            JOIN product_quality_control pqc ON pqc.harvest_id = pt.harvest_id
            WHERE pt.id IN ({placeholders})
        """, (location_id, *product_ids))

        conn.commit()