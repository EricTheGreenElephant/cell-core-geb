from sqlalchemy.orm import Session
from sqlalchemy import text, select
from schemas.qc_schemas import ProductQCInput
from schemas.audit_schemas import FieldChangeAudit
from models.lifecycle_stages_models import LifecycleStages
from services.audit_services import update_record_with_audit
from services.tracking_service import update_product_stage, update_product_status, record_filament_usage_post_qc
from services.quality_management_services import create_quarantine_record
from utils.db_transaction import transactional
from constants.product_status_constants import STATUS_MAP_QC_TO_BUSINESS


@transactional
def get_printed_products(db: Session) -> list[dict]:
    sql = """
        SELECT
            pt.id AS product_id,
            pt.harvest_id,
            pr.id AS request_id,
            ps.sku AS sku,
            ps.name AS sku_name,
            sps.average_weight_g,
            sps.weight_buffer_g,
            pr.lot_number,
            ph.print_date
        FROM product_tracking pt
        JOIN product_harvest ph ON pt.harvest_id = ph.id
        JOIN product_requests pr ON ph.request_id = pr.id
        JOIN product_skus ps ON ps.id = pr.sku_id
        LEFT JOIN sku_print_specs sps ON sps.sku_id = ps.id
        LEFT JOIN lifecycle_stages lc ON pt.current_stage_id = lc.id
        WHERE lc.stage_order = 1
        ORDER BY ph.print_date
    """
    result = db.execute(text(sql))
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]


@transactional
def insert_product_qc(db: Session, data: ProductQCInput):
    # === Insert QC Result ===
    qc_id = db.execute(
        text("""
            INSERT INTO product_quality_control (
                product_id, inspected_by, weight_grams, pressure_drop,
                visual_pass, inspection_result, notes
            )
            OUTPUT INSERTED.id
            VALUES (:pid, :inspector, :weight, :pressure, :visual, :result, :notes)
        """),
        {
            "pid": data.product_id,
            "inspector": data.inspected_by,
            "weight": data.weight_grams,
            "pressure": data.pressure_drop,
            "visual": data.visual_pass,
            "result": data.inspection_result,
            "notes": data.notes
        }
    ).scalar_one()

    # === Link selected reasons (HarvestQC context) ===
    if data.reason_ids: 
        ids = list(dict.fromkeys(data.reason_ids))
        db.execute(
            text(
                """
                    INSERT INTO product_quality_control_reasons (qc_id, reason_id)
                    VALUES (:qc_id, :rid)
                """
            ), [{"qc_id": qc_id, "rid": rid} for rid in ids]
        )
        
    # === Get harvest ID from tracking table ===
    result = db.execute(text("""
        SELECT harvest_id
        FROM product_tracking
        WHERE id = :pid
    """), {"pid": data.product_id}).fetchone()

    if not result:
        raise ValueError(f"No harvest found for product ID {data.product_id}")
    
    harvest_id = result.harvest_id

    # === Record the filament usage ===
    record_filament_usage_post_qc(
        db=db,
        harvest_id=harvest_id,
        product_id=data.product_id,
        weight_grams=data.weight_grams,
        user_id=data.inspected_by
    )

    # === Update Lifecycle Stage ===
    stage_code = "HarvestQCComplete"
    new_stage_id = db.scalar(
        text("SELECT id FROM lifecycle_stages WHERE stage_code = :code"),
        {"code": stage_code}
    )
    update_product_stage(
        db=db,
        product_id=data.product_id,
        new_stage_id=new_stage_id,
        reason="Harvest QC Complete",
        user_id=data.inspected_by
    )

    # === Create Quarantine Record if Needed ===
    if data.inspection_result == "Quarantine":
        create_quarantine_record(
            db=db,
            product_id=data.product_id,
            source="Harvest QC",
            quarantined_by=data.inspected_by,
            reason=data.notes
        )

    # === Update the Current Product Status ===
    status_name = STATUS_MAP_QC_TO_BUSINESS.get(data.inspection_result, "Pending")
    update_product_status(db, data.product_id, status_name)
    
    # === Update the Remaining Filament Weight ===
    db.execute(
        text("""
            UPDATE fm
            SET fm.remaining_weight = fm.remaining_weight - :weight
            FROM filament_mounting fm 
            JOIN product_harvest ph ON ph.filament_mounting_id = fm.id
            JOIN product_tracking pt ON ph.id = pt.harvest_id
            WHERE pt.id = :pid
        """),
        {"weight": data.weight_grams, "pid": data.product_id}
    )
    db.commit()

@transactional
def get_completed_qc_products(db: Session) -> list[dict]:
    sql = """
        SELECT 
            qc.id AS qc_id,
            pt.id AS product_id,
            ph.id AS harvest_id,
            ps.sku,
            ps.name AS sku_name,
            pr.lot_number,
            qc.weight_grams,
            qc.pressure_drop,
            qc.visual_pass,
            qc.inspection_result,
            qc.notes,
            ph.print_date
        FROM product_quality_control qc
        JOIN product_tracking pt ON qc.product_id = pt.id
        JOIN product_harvest ph ON pt.harvest_id = ph.id
        JOIN product_requests pr ON ph.request_id = pr.id
        JOIN product_skus ps ON pr.sku_id = ps.id
        ORDER BY qc.id DESC
    """
    result = db.execute(text(sql))
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]

@transactional
def update_qc_fields(
    db: Session,
    qc_id: int,
    product_id: int,
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
            record_id=qc_id,
            field=field,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            changed_by=user_id
        )
        update_record_with_audit(db, audit)
    
    if inspection_result_updated:
        new_status = STATUS_MAP_QC_TO_BUSINESS.get(new_result, "A-Ware")
        update_product_status(db, product_id=product_id, status_name=new_status)

        if new_result == "Quarantine":
            create_quarantine_record(
                db=db,
                product_id=product_id,
                source="Harvest QC",
                quarantined_by=user_id,
                reason=reason
            )

            new_stage_id = db.scalar(
                text("SELECT id FROM lifecycle_stages WHERE stage_code = :code"),
                {"code": "Quarantine"}
            )
            if new_stage_id:
                update_product_stage(
                    db=db,
                    product_id=product_id,
                    new_stage_id=new_stage_id,
                    reason="QC edit: moved to Quarantine",
                    user_id=user_id
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
    product_id: int,
    updates: dict[str, tuple],
    reason: str,
    q_reason: str,
    user_id: int
):
    
    # === Insert Product to Quarantine if Applicable ===
    if updates["qc_result"][1] == "Quarantine":
        create_quarantine_record(
            db=db,
            product_id=product_id,
            source="Post-Treatment QC",
            quarantined_by=user_id,
            reason=q_reason
        )

        stmt_stage = select(LifecycleStages.id).where(LifecycleStages.stage_code == "Quarantine")
        new_stage_id = db.scalar(stmt_stage)
        update_product_stage(
            db=db,
            product_id=product_id,
            new_stage_id=new_stage_id,
            reason="Moved to quarantine",
            user_id=user_id
        )


    status_name = STATUS_MAP_QC_TO_BUSINESS.get(updates["qc_result"][1], "Pending")
    update_product_status(
        db=db,
        product_id=product_id,
        status_name=status_name
    )

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

