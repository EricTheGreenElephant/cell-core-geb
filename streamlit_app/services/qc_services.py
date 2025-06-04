from sqlalchemy.orm import Session
from sqlalchemy import text
from schemas.qc_schemas import ProductQCInput
from schemas.audit_schemas import FieldChangeAudit
from services.audit_services import update_record_with_audit
from utils.db_transaction import transactional


@transactional
def get_printed_products(db: Session) -> list[dict]:
    sql = """
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
            "inspector": data.inspected_by,
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

@transactional
def get_completed_qc_products(db: Session) -> list[dict]:
    sql = """
        SELECT 
            qc.id AS qc_id,
            qc.harvest_id,
            pt.name AS product_type,
            pr.lot_number,
            qc.weight_grams,
            qc.pressure_drop,
            qc.visual_pass,
            qc.inspection_result,
            qc.notes,
            ph.print_date
        FROM product_quality_control qc
        JOIN product_harvest ph ON qc.harvest_id = ph.id
        JOIN product_requests pr ON ph.request_id = pr.id
        JOIN product_types pt ON pr.product_id = pt.id
        ORDER BY qc.id DESC
    """
    result = db.execute(text(sql))
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]

@transactional
def update_qc_fields(
    db: Session,
    harvest_id: int,
    updates: dict[str, tuple],
    reason: str,
    user_id: int
):
    inspection_result_updated = False
    new_result = None

    for field, (old_value, new_value) in updates.items():
        if field == "inspection_result":
            inspection_result_updated = True
            new_result = new_value

        audit = FieldChangeAudit(
            table="product_quality_control",
            record_id=harvest_id,
            field=field,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            changed_by=user_id
        )
        update_record_with_audit(db, audit)
    
    if inspection_result_updated:
        new_status = {
            "Passed": "QC Passed",
            "B-Ware": "QC B-Ware",
            "Quarantine": "QC Quarantine",
            "Waste": "QC Failed"
        }.get(new_result, "QC Completed")
        
        db.execute(
            text("""
                UPDATE product_tracking
                SET current_status = :status, last_updated_at = GETDATE()
                WHERE harvest_id = :h_id
            """),
            {"status": new_status, "h_id": harvest_id}
        )
    db.commit()

@transactional
def get_completed_post_treatment_qc(db: Session) -> list[dict]:
    sql = """
        SELECT
            pti.id AS inspection_id,
            pti.product_id,
            pt.name AS product_type,
            pti.surface_treated,
            pti.sterilized,
            pti.visual_pass,
            pti.qc_result,
            pti.inspected_by,
            pti.inspected_at
        FROM post_treatment_inspections pti
        JOIN product_tracking t ON pti.product_id = t.id
        JOIN product_harvest ph ON t.harvest_id = ph.id
        JOIN product_requests pr on ph.request_id = pr.id
        JOIN product_types pt ON pr.product_id = pt.id
        ORDER BY pti.inspected_at DESC
    """
    result = db.execute(text(sql))
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]

@transactional
def update_post_treatment_qc_fields(
    db: Session,
    inspection_id: int,
    updates: dict[str, tuple],
    reason: str,
    user_id: int
):
    for field, (old_value, new_value) in updates.items():
        audit = FieldChangeAudit(
            table="post_treatment_inspections",
            record_id=inspection_id,
            field=field,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            changed_by=user_id
        )
        update_record_with_audit(db, audit)
    db.commit()