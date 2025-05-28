from sqlalchemy.orm import Session
from sqlalchemy import text
from schemas.qc_schemas import ProductQCInput
from utils.db_transaction import transactional


@transactional
def get_printed_products(db: Session) -> list[dict]:
    sql = """
        SELECT
            ph.id as harvest_id,
            pr.id AS request.id,
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
    """
    result = db.execute(text(sql))
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]


@transactional
def insert_product_qc(db: Session, data: ProductQCInput):
    db.execute(
        text("""
            INSERT INTO product_quality_control (
                harvest_id, inspected_by, weight_grams, pressure_drop,
                visual_pass, inspection_result, notes
            )
            VALUES (:h_id, :inspector, :weight, :pressure, :visual, :result, :notes)
        """),
        {
            "h_id": data.harvest_id,
            "insepctor": data.inspected_by,
            "weight": data.weight_grams,
            "pressure": data.pressure_drop,
            "visual": data.visual_pass,
            "result": data.inspection_result,
            "notes": data.notes
        }
    )

    new_status = {
        "Passed": "QC Passed",
        "B-Ware": "QC B-Ware",
        "Quarantine": "QC Quarantine",
        "Waste": "QC Failed"
    }.get(data.inspection_result, "QC Completed")

    db.execute(
        text("""
            UPDATE product_tracking
            SET current_status = :status, last_updated_at = GETDATE()
            WHERE harvest_id = :h_id
        """),
        {"status": new_status, "h_id": data.harvest_id}
    )

    db.execute(
        text("""
            UPDATE product_harvest
            SET print_status = 'Inspected'
            WHERE id = :h_id
        """),
        {"h_id": data.harvest_id}
    )

    db.execute(
        text("""
            UPDATE fm
            SET fm.remaining_weight = fm.remaining_weight - :weight
            FROM filament_mounting fm
            JOIN product_harvest ph ON ph.filament_mounting_id = fm.id
            WHERE ph.id = :h_id
        """),
        {"weight": data.weight_grams, "h_id": data.harvest_id}
    )
    db.commit()