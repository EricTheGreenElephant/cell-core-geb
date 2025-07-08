from sqlalchemy import select, text, bindparam, or_, and_
from sqlalchemy.orm import Session, aliased
from typing import Optional
from models.production_models import ProductTracking, ProductHarvest, ProductType, ProductRequest
from models.lifecycle_stages_models import LifecycleStages
from models.users_models import User
from models.investigation_models import ProductInvestigation
from models.product_quality_control_models import ProductQualityControl, PostTreatmentInspection
from models.storage_locations_models import StorageLocation
from schemas.quality_management_schemas import (
    ProductQMReview, 
    PostTreatmentApprovalCandidate, 
    QuarantinedProductRow, 
    InvestigationEntry,
    InvestigatedProductRow
)
from services.tracking_service import log_product_status_change, update_product_stage
from utils.db_transaction import transactional


StagePrev = aliased(LifecycleStages)


@transactional
def get_qm_review_products(db: Session) -> list[ProductQMReview]:
    stmt = (
        select(
            ProductTracking.id.label("product_id"),
            LifecycleStages.stage_name.label("current_stage_name"),
            ProductTracking.last_updated_at,
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
        .join(ProductQualityControl, ProductQualityControl.product_id == ProductTracking.id)
        .join(User, ProductQualityControl.inspected_by == User.id)
        .outerjoin(StorageLocation, ProductTracking.location_id == StorageLocation.id)
        .where(LifecycleStages.stage_code == "InInterimStorage")
        .order_by(ProductTracking.last_updated_at.desc())
    )

    results = db.execute(stmt).all()

    products = [
        ProductQMReview(
            product_id=row.product_id,
            current_stage_name=row.current_stage_name,
            last_updated_at=row.last_updated_at,
            current_location=row.current_location,
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
            ProductTracking.id.label("product_id"),
            LifecycleStages.stage_name.label("current_stage_name"),
            ProductTracking.last_updated_at,
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
def approve_products_for_treatment(db: Session, product_ids: list[int], user_id: int):
    if not product_ids:
        return
    
    stmt = select(LifecycleStages.id).where(LifecycleStages.stage_code == "QMTreatmentApproval")
    new_stage_id = db.scalar(stmt)
    if not new_stage_id:
        raise ValueError("Target stage QMTreatmentApproval not found!")
    
    for product_id in product_ids:
        update_product_stage(
            db=db,
            product_id=product_id,
            new_stage_id=new_stage_id,
            reason="QM Approved for Treatment",
            user_id=user_id
        )
        # from_stage_id = db.scalar(
        #     text("SELECT current_stage_id FROM product_tracking WHERE id = :product_id"),
        #     {"product_id": product_id}
        # )
    
        # db.execute(
        #     text("""
        #         UPDATE product_tracking
        #         SET current_stage_id = :new_stage_id,
        #             last_updated_at = GETDATE()
        #         WHERE id = :product_id
        #     """),
        #     {"new_stage_id": new_stage_id, "product_id": product_id}
        # )

        # log_product_status_change(
        #     db=db,
        #     product_id=product_id,
        #     from_stage_id=from_stage_id,
        #     to_stage_id=new_stage_id,
        #     reason="QM Approved for Treatment",
        #     user_id=user_id
        # )

    db.commit()

@transactional
def approve_products_for_sales(db: Session, product_ids: list[int], user_id: int):
    if not product_ids:
        return
    
    target_stage_id = db.scalar(
        select(LifecycleStages.id).where(LifecycleStages.stage_code == "QMSalesApproval")
    )
    if not target_stage_id:
        raise ValueError("Target stage QMSalesApproval not found!")
    
    for product_id in product_ids:
        update_product_stage(
            db=db,
            product_id=product_id,
            new_stage_id=target_stage_id,
            reason="QM Approved for Sales",
            user_id=user_id
        )
        # from_stage_id = db.scalar(
        #     text("SELECT current_stage_id FROM product_tracking WHERE id = :product_id"),
        #     {"product_id": product_id}
        # )
        # db.execute(
        #     text("""
        #         UPDATE product_tracking
        #         SET current_stage_id = :new_stage_id,
        #             last_updated_at = GETDATE()
        #         WHERE id = :product_id
        #     """),
        #     {"new_stage_id": target_stage_id, "product_id": product_id}
        # )

        # log_product_status_change(
        #     db=db,
        #     product_id=product_id,
        #     from_stage_id=from_stage_id,
        #     to_stage_id=target_stage_id,
        #     reason="QM Approved for Sales",
        #     user_id=user_id
        # )

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

@transactional
def get_quarantined_products(db: Session) -> list[QuarantinedProductRow]:
    stmt = (
        select(
            ProductTracking.id.label("product_id"),
            ProductHarvest.id.label("harvest_id"),
            ProductType.name.label("product_type"),
            StagePrev.stage_name.label("previous_stage_name"),
            LifecycleStages.stage_name.label("current_stage_name"),
            StorageLocation.location_name,
            ProductQualityControl.inspection_result,
            ProductQualityControl.weight_grams,
            ProductQualityControl.pressure_drop,
            ProductTracking.last_updated_at
        )
        .join(ProductHarvest, ProductTracking.harvest_id == ProductHarvest.id)
        .join(ProductRequest, ProductHarvest.request_id == ProductRequest.id)
        .join(ProductType, ProductRequest.product_id == ProductType.id)
        .outerjoin(ProductQualityControl, ProductQualityControl.product_id == ProductTracking.id)
        .outerjoin(StorageLocation, ProductTracking.location_id == StorageLocation.id)
        .join(LifecycleStages, ProductTracking.current_stage_id == LifecycleStages.id)
        .outerjoin(StagePrev, ProductTracking.previous_stage_id == StagePrev.id)
        .outerjoin(ProductInvestigation, ProductTracking.id == ProductInvestigation.product_id)
        .where(
            LifecycleStages.stage_code == "Quarantine",
            or_(
                ProductInvestigation.id.is_(None),                      
                ProductInvestigation.status != "Under Investigation"     
            )
        )
    )
    results = db.execute(stmt).all()
    return [QuarantinedProductRow(**row._mapping) for row in results]

@transactional
def create_product_investigation(
    db: Session,
    product_id: int,
    status: str,
    created_by: int,
    deviation_number: Optional[str] = None,
    comment: Optional[str] = None
):
    db.execute(
        text("""
            INSERT INTO product_investigations (
                product_id, status, deviation_number, comment, created_by
            )
            VALUES (:pid, :status, :dev, :comment, :uid)
        """),
        {"pid": product_id, "status": status, "dev": deviation_number, "comment": comment, "uid": created_by}
    )

@transactional
def escalate_to_investigation(db: Session, entry: InvestigationEntry):
    investigation = ProductInvestigation(
        product_id=entry.product_id,
        deviation_number=entry.deviation_number,
        comment=entry.comment,
        created_by=entry.created_by,
        status=entry.status
    )
    db.add(investigation)

    # log_product_status_change(
    #     db=db,
    #     product_id=entry.product_id,
    #     from_stage_id=None,
    #     to_stage_id=None,
    #     status="Under Investigation",
    #     reason="Flagged by QM",
    #     user_id=entry.created_by
    # )

    db.commit()

# @transactional
# def resolve_quarantine_approval(
#     db: Session, product_id: int, resolution: str, user_id: int, comment: str = ""
# )

@transactional
def sort_qm_reviewed_products(db: Session, product_id: int, stage_name: str, resolution: str, user_id: int):
    if resolution == "Waste":
        new_stage_name = "Discarded Product"
    elif stage_name == "Stored; Pending QM Approval for Treatment":
        new_stage_name = "QM Approved for Treatment; Pending Treatment"
    elif stage_name == "Stored; Pending QM Approval for Sales":
        new_stage_name = "QM Approved For Sales; Pending Sales"
    else:
        new_stage_name = stage_name
    
    stmt = select(LifecycleStages.id).where(LifecycleStages.stage_name == new_stage_name)
    stage_id = db.scalar(stmt)

    db.execute(
        text("""
            UPDATE product_quality_control
            SET inspection_result = :resolution
            WHERE product_id = :pid
        """),
        {"resolution": resolution, "pid": product_id}
    )

    update_product_stage(
        db=db,
        product_id=product_id,
        new_stage_id=stage_id,
        reason="QM Decision",
        user_id=user_id
    )

    db.commit()

def get_previous_stage_before_quarantine(db: Session, product_id: int) -> int | None:
    return db.scalar(
        text("""
            SELECT previous_stage_id
            FROM product_tracking
            WHERE id = :pid
        """),
        {"pid": product_id}
    )

@transactional
def get_investigated_products(db: Session) -> list[InvestigatedProductRow]:
    stmt = (
        select(
            ProductTracking.id.label("product_id"),
            ProductType.name.label("product_type"),
            LifecycleStages.stage_name.label("current_stage_name"),
            ProductTracking.last_updated_at,
            StorageLocation.location_name,
            ProductQualityControl.inspection_result,
            ProductInvestigation.deviation_number,
            ProductInvestigation.comment,
            User.display_name.label("created_by"),
            ProductInvestigation.created_at
        )
        .join(LifecycleStages, ProductTracking.current_stage_id == LifecycleStages.id)
        .join(ProductHarvest, ProductTracking.harvest_id == ProductHarvest.id)
        .join(ProductRequest, ProductHarvest.request_id == ProductRequest.id)
        .join(ProductType, ProductRequest.product_id == ProductType.id)
        .outerjoin(StorageLocation, ProductTracking.location_id == StorageLocation.id)
        .outerjoin(ProductQualityControl, ProductQualityControl.product_id == ProductTracking.id)
        .join(ProductInvestigation, ProductInvestigation.product_id == ProductTracking.id)
        .join(User, ProductInvestigation.created_by == User.id)
    )
    result = db.execute(stmt).all()
    return [InvestigatedProductRow(**row._mapping) for row in result]