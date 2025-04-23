from utils.db import db_connection


def get_qc_passed_products():
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                pt.id AS tracking_id,
                pt.current_status,
                pt.last_updated_at,
                pr.lot_number,
                ptype.name AS product_type,
                pt.location_id
            FROM product_tracking pt
            JOIN product_harvest ph ON pt.harvest_id = ph.id
            JOIN product_requests pr ON ph.request_id = pr.id
            JOIN product_types ptype ON pr.product_id = ptype.id
            WHERE pt.current_status = 'QC Passed'                
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