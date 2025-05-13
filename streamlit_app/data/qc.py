from utils.db import db_connection

def get_printed_products():
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
                    SELECT
                        ph.id as harvest_id,
                        pr.id AS request_id,
                        pt.name AS product_type,
                        pt.average_weight,
                        pt.buffer_weight,
                        pr.lot_number,
                        ph.print_date
                    FROM product_harvest ph 
                    JOIN product_requests pr ON ph.request_id = pr.id
                    JOIN product_types pt ON pr.product_id = pt.id
                    WHERE ph.print_status = 'Printed'
                       AND NOT EXISTS (
                            SELECT 1 FROM product_quality_control qc
                            WHERE qc.harvest_id = ph.id
                       )
                       ORDER BY ph.print_date
                    """)
        cols = [col[0] for col in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
    
def insert_product_qc(harvest_id, inspected_by, weight_grams, pressure_drop, visual_pass, inspection_result, notes):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO product_quality_control (
                harvest_id, inspected_by, weight_grams, pressure_drop,
                visual_pass, inspection_result, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            harvest_id,
            inspected_by,
            weight_grams,
            pressure_drop,
            visual_pass,
            inspection_result,
            notes
        ))

        # Determine new status based on result
        new_status = {
            "Passed": "QC Passed",
            "B-Ware": "QC B-Ware",
            "Quarantine": "QC Quarantine",
            "Waste": "QC Failed"
        }.get(inspection_result, "QC Completed")

        # Update product_tracking status
        cursor.execute("""
            UPDATE product_tracking
            SET current_status = ?, last_updated_at = GETDATE()
            WHERE harvest_id = ?
        """, (new_status, harvest_id))

        cursor.execute("""
            UPDATE product_harvest
            SET print_status = 'Inspected'
            WHERE id = ?
        """, (harvest_id,))

        # Get filament_mounting id from harvest
        cursor.execute("""
            SELECT fm.id
            FROM product_harvest ph
            JOIN filament_mounting fm ON ph.filament_mounting_id = fm.id
            WHERE ph.id = ?
        """, (harvest_id,))
        result = cursor.fetchone()

        if result:
            filament_mount_id = result[0]
            cursor.execute("""
                UPDATE filament_mounting
                SET remaining_weight = remaining_weight - ?
                WHERE id = ?
            """, (weight_grams, filament_mount_id))

        conn.commit()

