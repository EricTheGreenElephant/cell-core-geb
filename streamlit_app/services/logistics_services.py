from sqlalchemy.orm import Session
from sqlalchemy import text, select
from models.filament_models import Filament, FilamentMounting
from models.production_models import ProductTracking, ProductHarvest, ProductRequest, ProductType
from models.lifecycle_stages_models import LifecycleStages
from models.product_quality_control_models import ProductQualityControl, PostTreatmentInspection
from models.storage_locations_models import StorageLocation
from models.logistics_models import TreatmentBatch, TreatmentBatchProduct
from models.users_models import User
from schemas.logistics_schemas import TreatmentBatchCreate, TreatmentBatchProductCandidate, PostHarvestStorageCandidate, PostTreatmentStorageCandidate
from schemas.audit_schemas import FieldChangeAudit
from services.audit_services import update_record_with_audit
from services.tracking_service import log_product_status_change, update_product_stage, update_product_status
from services.quality_management_services import create_quarantine_record
from constants.product_status_constants import STATUS_MAP_QC_TO_BUSINESS
from utils.db_transaction import transactional


@transactional
def get_qc_passed_products(db: Session) -> list[TreatmentBatchProductCandidate]:
    stmt = (
        select(
            ProductTracking.id.label("product_id"),
            LifecycleStages.stage_name.label("current_status"),
            ProductTracking.last_updated_at,
            ProductHarvest.id.label("harvest_id"),
            ProductType.name.label("product_type"),
            ProductQualityControl.inspection_result,
            StorageLocation.location_name.label("location_name"),
        )
        .join(LifecycleStages, ProductTracking.current_stage_id == LifecycleStages.id)
        .join(ProductHarvest, ProductTracking.harvest_id == ProductHarvest.id)
        .join(ProductRequest, ProductHarvest.request_id == ProductRequest.id)
        .join(ProductType, ProductRequest.product_id == ProductType.id)
        .join(ProductQualityControl, ProductQualityControl.product_id == ProductTracking.id)
        .outerjoin(StorageLocation, ProductTracking.location_id == StorageLocation.id)
        .where(LifecycleStages.stage_code == "QMTreatmentApproval")
        .order_by(ProductTracking.last_updated_at.desc())
    )
    results = db.execute(stmt).all()
    products = [
        TreatmentBatchProductCandidate(
            product_id=row.product_id,
            current_stage_name=row.current_status,
            last_updated_at=row.last_updated_at,
            harvest_id=row.harvest_id,
            product_type=row.product_type,
            inspection_result=row.inspection_result,
            location_name=row.location_name,
        )
        for row in results
    ]
    return products

@transactional
def create_treatment_batch(db: Session, data: TreatmentBatchCreate):
    batch = TreatmentBatch(sent_by=data.sent_by, notes=data.notes, status="Shipped")
    db.add(batch)
    db.flush()

    offsite_id = db.execute(
        text("SELECT id FROM storage_locations WHERE location_name = 'Offsite'")
    ).scalar_one()
    
    if not offsite_id:
         raise ValueError("Offsite storage location not found.")
    
    stmt_stage = select(LifecycleStages.id).where(LifecycleStages.stage_code == "InTreatment")
    new_stage_id = db.scalar(stmt_stage)
    if not new_stage_id:
        raise ValueError("Target stage InTreatment not found!")
    
    for item in data.tracking_data:
        product = TreatmentBatchProduct(
            batch_id=batch.id,
            product_id=item.product_id,
            surface_treat=bool(item.surface_treat),
            sterilize=bool(item.sterilize)
        )
        db.add(product)

        update_product_stage(
            db=db,
            product_id=item.product_id,
            new_stage_id=new_stage_id,
            reason="Sent for Treatment (batch creation)",
            user_id=data.sent_by,
            location_id=offsite_id
        )
        
    db.commit()

@transactional
def get_qc_products_needing_storage(db: Session) -> list[PostHarvestStorageCandidate]:
    stmt = (
        select(
            ProductTracking.id.label("product_id"),
            LifecycleStages.stage_name.label("current_stage_name"),
            ProductTracking.location_id,
            ProductHarvest.id.label("harvest_id"),
            ProductTracking.last_updated_at,
            ProductQualityControl.inspection_result,
            Filament.serial_number.label("filament_serial"),
            ProductType.name.label("product_type"),
            User.display_name.label("printed_by"),
            ProductHarvest.print_date
        )
        .join(LifecycleStages, ProductTracking.current_stage_id == LifecycleStages.id)
        .join(ProductHarvest, ProductTracking.harvest_id == ProductHarvest.id)
        .join(ProductRequest, ProductHarvest.request_id == ProductRequest.id)
        .join(ProductType, ProductRequest.product_id == ProductType.id)
        .join(ProductQualityControl, ProductQualityControl.product_id == ProductTracking.id)
        .join(FilamentMounting, ProductHarvest.filament_mounting_id == FilamentMounting.id)
        .join(Filament, FilamentMounting.filament_id == Filament.id)
        .outerjoin(User, ProductHarvest.printed_by == User.id)
        .where(LifecycleStages.stage_code == "HarvestQCComplete")
        .where(ProductTracking.location_id.is_(None))
        .order_by(ProductTracking.last_updated_at.desc())
    )
    results = db.execute(stmt).all()

    return [PostHarvestStorageCandidate(**row._mapping) for row in results]

@transactional
def get_post_treatment_products_needing_storage(db: Session) -> list[PostTreatmentStorageCandidate]:
    stmt = (
        select(
            ProductTracking.id.label("product_id"),
            ProductHarvest.id.label("harvest_id"),
            ProductType.name.label("product_type"),
            PostTreatmentInspection.qc_result.label("inspection_result"),
        )
        .join(ProductHarvest, ProductTracking.harvest_id == ProductHarvest.id)
        .join(ProductRequest, ProductHarvest.request_id == ProductRequest.id)
        .join(ProductType, ProductRequest.product_id == ProductType.id)
        .join(PostTreatmentInspection, ProductTracking.id == PostTreatmentInspection.product_id)
        .join(LifecycleStages, ProductTracking.current_stage_id == LifecycleStages.id)
        .where(LifecycleStages.stage_code == "PostTreatmentQC")
    )
    results = db.execute(stmt).all()
    return [PostTreatmentStorageCandidate(**row._mapping) for row in results]

@transactional
def assign_storage_to_products(db: Session, assignments: list[tuple[str, int, str]], user_id: int):
    for product_id, location_id, stage_code in assignments:
        to_stage_id = db.scalar(
            text("SELECT id FROM lifecycle_stages WHERE stage_code = :code"),
            {"code": stage_code}
        )

        if stage_code == "Quarantine":
            reason = "Moved to Quarantine"
            db.execute(
                text("""
                    UPDATE quarantined_products
                    SET location_id = :loc
                    WHERE product_id = :pid AND quarantine_status = 'Active'
                """),
                {"loc": location_id, "pid": product_id}
            )

        elif stage_code == "Disposed":
            reason = "Disposed"
        else:
            reason = "Storage assignment"

        update_product_stage(
            db=db,
            product_id=product_id,
            new_stage_id=to_stage_id,
            reason=reason,
            user_id=user_id,
            location_id=location_id
        )

    db.commit()

@transactional
def get_shipped_batches(db: Session) -> list[dict]:
    sql = """
        SELECT id, sent_at, notes
        FROM treatment_batches
        WHERE status = 'Shipped'
        ORDER BY sent_at DESC
    """
    result = db.execute(text(sql))
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]


@transactional
def get_products_by_batch_id(db: Session, batch_id: int) -> list[dict]:
    sql = """
        SELECT
            tbp.id,
            pt.id AS product_id,
            ps.status_name AS current_status,
            lc.stage_name AS current_stage,
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
        LEFT JOIN product_quality_control pqc ON pt.id = pqc.product_id
        LEFT JOIN lifecycle_stages lc ON pt.current_stage_id = lc.id
        LEFT JOIN product_statuses ps ON pt.current_status_id = ps.id
        WHERE tbp.batch_id = :batch_id
    """
    result = db.execute(text(sql), {"batch_id": batch_id})
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]


@transactional
def update_post_treatment_qc(db: Session, product_qc: list[dict], inspected_by: int):
    stmt_stage = select(LifecycleStages.id).where(LifecycleStages.stage_code == "PostTreatmentQC")
    new_stage_id = db.scalar(stmt_stage)
    if not new_stage_id:
        raise ValueError("Target stage PostTreatmentQC not found!")
    
    # === Insert Inspection Result ===
    for item in product_qc:
        product_id = item["product_id"]

        inspection_id = db.execute(
            text("""
                INSERT INTO post_treatment_inspections (
                    product_id, surface_treated, sterilized, visual_pass, qc_result, inspected_by, notes
                )
                OUTPUT INSERTED.id
                VALUES (:pid, :treated, :sterilized, :visual, :qc_result, :inspector, :notes)
            """),
            {
                "pid": product_id,
                "treated": item["surface_treat"],
                "sterilized": item["sterilize"],
                "visual": item["visual_pass"],
                "qc_result": item["qc_result"],
                "inspector": inspected_by,
                "notes": item.get("notes")
            }
        ).scalar_one()

        reason_ids = item.get("reason_ids") or []
        if reason_ids:
            reason_ids = list(dict.fromkeys(reason_ids))
            db.execute(
                text(
                    """
                        INSERT INTO post_treatment_inspection_reasons (inspection_id, reason_id)
                        VALUES (:iid, :rid)
                    """
                ),
                [{"iid": inspection_id, "rid": rid} for rid in reason_ids]
            )
        # === Insert Product to Quarantine if Applicable ===
        if item["qc_result"] == "Quarantine":
            create_quarantine_record(
                db=db,
                product_id=product_id,
                source="Post-Treatment QC",
                quarantined_by=inspected_by,
                reason=item.get("quarantine_reason")
            )

        update_product_stage(
            db=db,
            product_id=product_id,
            new_stage_id=new_stage_id,
            reason="Post-Treatment QC Complete",
            user_id=inspected_by
        )

        status_name = STATUS_MAP_QC_TO_BUSINESS.get(item["qc_result"], "Pending")
        update_product_status(
            db=db,
            product_id=product_id,
            status_name=status_name
        )

    db.commit()


@transactional
def mark_batch_as_inspected(db: Session, batch_id: int):
    db.execute(
        text("""
            UPDATE treatment_batches
            SET status = 'Inspected', received_at = GETDATE()
            WHERE id = :id
        """),
        {"id": batch_id}
    )
    db.commit()

@transactional
def get_stored_products(db: Session, product_id: str | None = None) -> list[dict]:
    sql = """
        SELECT
            t.id AS product_id,
            ph.id AS harvest_id,
            pt.name AS product_type,
            lc.stage_name AS current_status,
            sl.id AS location_id,
            sl.location_name,
            sl.description
        FROM product_tracking t
        JOIN product_harvest ph ON t.harvest_id = ph.id
        JOIN product_requests pr ON ph.request_id = pr.id
        JOIN product_types pt ON pr.product_id = pt.id
        JOIN storage_locations sl ON t.location_id = sl.id
        LEFT JOIN lifecycle_stages lc ON t.current_stage_id = lc.id
        
    """
    if product_id:
        sql += " WHERE t.id = :product_id"

    result = db.execute(text(sql), {"product_id": product_id} if product_id else {})
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]

@transactional
def update_tracking_storage(
    db: Session,
    product_id: int,
    updates: dict[str, tuple],
    reason: str,
    user_id: int
):
    for field, (old_value, new_value) in updates.items():
        audit = FieldChangeAudit(
            table="product_tracking",
            record_id=product_id,
            field=field,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            changed_by=user_id
        )
        update = False if field == "current_status" else True
        update_record_with_audit(db, audit, update)

        if field == "current_status":
            stmt_stage = select(LifecycleStages.id).where(LifecycleStages.stage_name == new_value)
            new_stage_id = db.scalar(stmt_stage)
            from_stage_id = db.scalar(
                text("SELECT current_stage_id FROM product_tracking WHERE id = :product_id"),
                {"product_id": product_id}
            )
            db.execute(
                text("""
                    UPDATE product_tracking
                    SET current_stage_id = :new_stage_id, last_updated_at = GETDATE()
                    WHERE id = :pid
                """),
                {"new_stage_id": new_stage_id, "pid": product_id}
            )
            log_product_status_change(
                db=db,
                product_id=product_id,
                from_stage_id=from_stage_id,
                to_stage_id=new_stage_id,
                reason="Update from storage location edit.",
                user_id=user_id 
            )
    db.commit()

@transactional
def remove_product_from_batch(
    db: Session, 
    batch_product_id: int, 
    product_id: int,
    user_id: int,
    reason: str
):
    audit = FieldChangeAudit(
        table="treatment_batch_products",
        record_id=batch_product_id,
        field="DELETED",
        old_value="No",
        new_value="Yes",
        reason=reason,
        changed_by=user_id
    )
    update_record_with_audit(db, audit, update=False)

    db.execute(
        text("DELETE FROM treatment_batch_products WHERE id = :id"),
        {"id": batch_product_id}    
    )

    stmt_stage = select(LifecycleStages.id).where(LifecycleStages.stage_code == "QMTreatmentApproval")
    new_stage_id = db.scalar(stmt_stage)
    update_product_stage(
        db=db,
        product_id=product_id,
        new_stage_id=new_stage_id,
        reason="Removed from treatment batch",
        user_id=user_id
    )

    db.commit()

@transactional
def update_treatment_batch_fields(
    db: Session,
    batch_product_id: int,
    updates: dict[str, tuple],
    reason: str,
    user_id: int
):
    for field, (old_value, new_value) in updates.items():
        audit = FieldChangeAudit(
            table="treatment_batch_products",
            record_id=batch_product_id,
            field=field,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            changed_by=user_id
        )
        update_record_with_audit(db, audit)
    db.commit()