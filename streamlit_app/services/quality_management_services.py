from sqlalchemy import select, text, bindparam
from sqlalchemy.orm import Session
from models.production_models import ProductTracking, ProductHarvest, ProductType, ProductRequest
from models.lifecycle_stages_models import LifecycleStages
from models.users_models import User
from models.product_quality_control_models import ProductQualityControl, PostTreatmentInspection
from models.storage_locations_models import StorageLocation
from schemas.quality_management_schemas import ProductQMReview, PostTreatmentApprovalCandidate
from utils.db_transaction import transactional


@transactional
def get_qm_review_products(db: Session) -> list[ProductQMReview]:
    stmt = (
        select(
            ProductTracking.id.label("tracking_id"),
            LifecycleStages.stage_name.label("current_stage_name"),
            ProductTracking.last_updated_at,
            ProductHarvest.id.label("harvest_id"),
            ProductRequest.lot_number,
            ProductType.name.label("product_type_name"),
            ProductQualityControl.inspection_result,
            User.display_name.label("inspected_by"),
            ProductQualityControl.weight_grams,
            ProductQualityControl.pressure_drop,
            ProductQualityControl.visual_pass,
            ProductQualityControl.notes,
            StorageLocation.location_name.label("current_location"),
        )
        .join(LifecycleStages, ProductTracking.current_stage_id == LifecycleStages.id)
        .join(ProductHarvest, ProductTracking.harvest_id == ProductHarvest.id)
        .join(ProductRequest, ProductHarvest.request_id == ProductRequest.id)
        .join(ProductType, ProductRequest.product_id == ProductType.id)
        .join(ProductQualityControl, ProductQualityControl.harvest_id == ProductHarvest.id)
        .join(User, ProductQualityControl.inspected_by == User.id)
        .outerjoin(StorageLocation, ProductTracking.location_id == StorageLocation.id)
        .where(LifecycleStages.stage_code.in_(["InInterimStorage", "Quarantine"]))
        .order_by(ProductTracking.last_updated_at.desc())
    )

    results = db.execute(stmt).all()

    products = [
        ProductQMReview(
            tracking_id=row.tracking_id,
            current_stage_name=row.current_stage_name,
            last_updated_at=row.last_updated_at,
            current_location=row.current_location,
            harvest_id=row.harvest_id,
            lot_number=row.lot_number,
            product_type_name=row.product_type_name,
            inspection_result=row.inspection_result,
            inspected_by=row.inspected_by,
            weight_grams=float(row.weight_grams),
            pressure_drop=float(row.pressure_drop),
            visual_pass=row.visual_pass,
            qc_notes=row.notes,
        )
        for row in results
    ]

    return products

@transactional
def get_post_treatment_qm_candidates(db: Session) -> list[PostTreatmentApprovalCandidate]:
    stmt = (
        select(
            ProductTracking.id.label("tracking_id"),
            LifecycleStages.stage_name.label("current_stage_name"),
            ProductTracking.last_updated_at,
            ProductHarvest.id.label("harvest_id"),
            ProductType.name.label("product_type_name"),
            PostTreatmentInspection.qc_result.label("inspection_result"),
            User.display_name.label("inspected_by"),
            PostTreatmentInspection.visual_pass,
            PostTreatmentInspection.surface_treated,
            PostTreatmentInspection.sterilized,
            StorageLocation.location_name.label("current_location")
        )
        .join(ProductHarvest, ProductTracking.harvest_id == ProductHarvest.id)
        .join(ProductRequest, ProductHarvest.request_id == ProductRequest.id)
        .join(ProductType, ProductRequest.product_id == ProductType.id)
        .join(LifecycleStages, ProductTracking.current_stage_id == LifecycleStages.id)
        .outerjoin(PostTreatmentInspection, PostTreatmentInspection.product_id == ProductTracking.id)
        .outerjoin(User, PostTreatmentInspection.inspected_by == User.id)
        .outerjoin(StorageLocation, ProductTracking.location_id == StorageLocation.id)
        .where(LifecycleStages.stage_code == "PostTreatmentStorage")
        .order_by(ProductTracking.last_updated_at.desc())
    )
    results = db.execute(stmt).all()
    return [PostTreatmentApprovalCandidate(**row._mapping) for row in results]

@transactional
def approve_products_for_treatment(db: Session, tracking_ids: list[int]):
    if not tracking_ids:
        return
    
    stmt = select(LifecycleStages.id).where(LifecycleStages.stage_code == "QMTreatmentApproval")
    new_stage_id = db.scalar(stmt)
    if not new_stage_id:
        raise ValueError("Target stage QMTreatmentApproval not found!")
    
    update_stmt = text("""
        UPDATE product_tracking
        SET current_stage_id = :new_stage_id,
            last_updated_at = GETDATE()
        WHERE id IN :tracking_ids
    """).bindparams(bindparam("tracking_ids", expanding=True))

    db.execute(update_stmt, {"new_stage_id": new_stage_id, "tracking_ids": tuple(tracking_ids)})
    db.commit()

@transactional
def approve_products_for_sales(db: Session, tracking_ids: list[int]):
    if not tracking_ids:
        return
    
    target_stage_id = db.scalar(
        select(LifecycleStages.id).where(LifecycleStages.stage_code == "QMSalesApproval")
    )
    if not target_stage_id:
        raise ValueError("Target stage QMSalesApproval not found!")
    
    update_stmt = text("""
        UPDATE product_tracking
        SET current_stage_id = :new_stage_id,
            last_updated_at = GETDATE()
        WHERE id IN :tracking_ids
    """).bindparams(bindparam("tracking_ids", expanding=True))

    db.execute(update_stmt, {"new_stage_id": target_stage_id, "tracking_ids": tracking_ids})
    db.commit()

@transactional
def get_audit_log_entries(db: Session) -> list[dict]:
    sql = """
        SELECT
            table_name,
            record_id,
            field_name,
            old_value,
            new_value,
            reason,
            changed_by,
            changed_at
        FROM audit_log
        ORDER BY changed_at DESC
    """
    result = db.execute(text(sql))
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]