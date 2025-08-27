from sqlalchemy import select, text, bindparam, or_, and_
from sqlalchemy.orm import Session, aliased
from typing import Optional
from models.production_models import ProductTracking, ProductHarvest, ProductType, ProductRequest, ProductStatuses
from models.lifecycle_stages_models import LifecycleStages
from models.users_models import User
from models.investigation_models import ProductInvestigation
from models.product_quality_control_models import ProductQualityControl, PostTreatmentInspection
from models.quarantined_products_models import QuarantinedProducts
from models.storage_locations_models import StorageLocation
from models.logistics_models import TreatmentBatchProduct
from schemas.quality_management_schemas import (
    ProductQMReview, 
    PostTreatmentApprovalCandidate, 
    QuarantinedProductRow, 
    InvestigationEntry,
    InvestigatedProductRow,
    ProductQuarantineSearchResult
)
from services.tracking_service import log_product_status_change, update_product_stage, update_product_status
from utils.db_transaction import transactional
from constants.product_status_constants import STATUS_MAP_QC_TO_BUSINESS
from datetime import datetime, timezone


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
def approve_products_for_treatment(db: Session, products: list[dict], user_id: int):
    if not products:
        return
    
    stmt = select(LifecycleStages.id).where(LifecycleStages.stage_code == "QMTreatmentApproval")
    new_stage_id = db.scalar(stmt)
    if not new_stage_id:
        raise ValueError("Target stage QMTreatmentApproval not found!")
    
    for product in products:
        product_id = product["pid"]
        reason = product.get("reason", "").strip()

        approval_reason = (
            f"QM Approved for Treatment{': ' + reason if reason else ''}"
        )
        update_product_stage(
            db=db,
            product_id=product_id,
            new_stage_id=new_stage_id,
            reason=approval_reason,
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
def approve_products_for_sales(db: Session, products: list[dict], user_id: int):
    if not products:
        return
    
    target_stage_id_passed = db.scalar(
        select(LifecycleStages.id).where(LifecycleStages.stage_code == "QMSalesApproval")
    )

    target_stage_id_bware = db.scalar(
        select(LifecycleStages.id).where(LifecycleStages.stage_code == "Internal Use")
    )

    if not target_stage_id_passed:
        raise ValueError("Target stage QMSalesApproval not found!")
    if not target_stage_id_bware:
        raise ValueError("Target stage Internal Use not found!")
    
    for product in products:
        product_id = product["pid"]
        result = product["result"]
        reason = product.get("reason", "").strip()

        if result == "Passed":
            final_target_stage = target_stage_id_passed
            approval_reason = (
                f"QM Approved for Sales{': ' + reason if reason else ''}"
            )
        else:
            final_target_stage = target_stage_id_bware
            approval_reason = f"QM Approved for Internal Use{': ' + reason if reason else ''}"

        update_product_stage(
            db=db,
            product_id=product_id,
            new_stage_id=final_target_stage,
            reason=approval_reason,
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
def decline_products_for_disposal(db: Session, products: list[dict], comment: str, user_id: int):
    """
    Moves products to the Disposed stage and updates status to Waste.
    """
    target_stage_id = db.scalar(
        select(LifecycleStages.id).where(LifecycleStages.stage_code == "Disposed")
    )
    if not target_stage_id:
        raise ValueError("Target stage 'Disposed' not found!")
    
    for product in products:
        product_id = product["pid"]

        update_product_stage(
            db=db,
            product_id=product_id,
            new_stage_id=target_stage_id,
            reason=f"Declined by QM: {comment}",
            user_id=user_id
        )

        update_product_status(db, product_id, "Waste")
    
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
            ProductTracking.tracking_id,
            ProductType.name.label("product_type"),
            StagePrev.stage_name.label("previous_stage_name"),
            LifecycleStages.stage_name.label("current_stage_name"),
            StorageLocation.location_name,
            ProductQualityControl.inspection_result,
            PostTreatmentInspection.qc_result,
            QuarantinedProducts.quarantine_date,
            QuarantinedProducts.quarantine_reason,
            User.display_name.label("quarantined_by"),
            ProductQualityControl.weight_grams,
            ProductQualityControl.pressure_drop,
            ProductTracking.last_updated_at
        )
        .join(QuarantinedProducts, QuarantinedProducts.product_id == ProductTracking.id)
        .join(ProductHarvest, ProductTracking.harvest_id == ProductHarvest.id)
        .join(ProductRequest, ProductHarvest.request_id == ProductRequest.id)
        .join(ProductType, ProductRequest.product_id == ProductType.id)
        .outerjoin(ProductQualityControl, ProductQualityControl.product_id == ProductTracking.id)
        .outerjoin(PostTreatmentInspection, ProductTracking.id == PostTreatmentInspection.product_id)
        .outerjoin(StorageLocation, ProductTracking.location_id == StorageLocation.id)
        .join(LifecycleStages, ProductTracking.current_stage_id == LifecycleStages.id)
        .outerjoin(StagePrev, ProductTracking.previous_stage_id == StagePrev.id)
        .outerjoin(ProductInvestigation, ProductTracking.id == ProductInvestigation.product_id)
        .join(User, QuarantinedProducts.quarantined_by == User.id)
        .where(QuarantinedProducts.quarantine_status == "Active")
        .where(QuarantinedProducts.location_id.is_not(None))
        .where(
            (ProductInvestigation.id.is_(None)) |
            (ProductInvestigation.status != "Under Investigation")
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

# @transactional
# def resolve_quarantine_approval(
#     db: Session, product_id: int, resolution: str, user_id: int, comment: str = ""
# )

@transactional
def sort_qm_reviewed_products(db: Session, product_id: int, stage_name: str, resolution: str, user_id: int):
    if resolution == "Waste":
        new_stage_name = "Discarded Product"
    elif stage_name == "Harvest QC Complete; Pending Storage":
        new_stage_name = "QM Approved for Treatment; Pending Treatment"
    
    elif resolution == "B-Ware" and stage_name == "Returned / Post-Treatment QC; Pending Storage":
        new_stage_name = "Internal Use/Client" 

    elif stage_name == "Returned / Post-Treatment QC; Pending Storage":
        new_stage_name = "QM Approved For Sales; Pending Sales"

    else:
        new_stage_name = stage_name
    
    stmt = select(LifecycleStages.id).where(LifecycleStages.stage_name == new_stage_name)
    stage_id = db.scalar(stmt)

    update_product_stage(
        db=db,
        product_id=product_id,
        new_stage_id=stage_id,
        reason="QM Decision",
        user_id=user_id
    )

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
            StagePrev.stage_name.label("previous_stage_name"),
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
        .outerjoin(StagePrev, ProductTracking.previous_stage_id == StagePrev.id)
        .join(ProductInvestigation, ProductInvestigation.product_id == ProductTracking.id)
        .join(User, ProductInvestigation.created_by == User.id)
        .where(ProductInvestigation.status == "Under Investigation")
    )
    result = db.execute(stmt).all()
    return [InvestigatedProductRow(**row._mapping) for row in result]

@transactional
def resolve_investigation(db: Session, product_id: int, resolution: str, user_id: int, comment: str):
    """
    Marks the product investigation as resolved and also updates the quarantined_products table if applicable.

    """
    resolution_note = f"[Resolution {datetime.now().strftime('%Y-%m-%d %H:%M')}]: {resolution}"
    if comment:
        resolution_note += f" — {comment}"
    if resolution == "Passed":
        status = "Cleared A-Ware"
    elif resolution == "B-Ware":
        status = "Cleared B-Ware"
    else:
        status = "Disposed"
    
    q_status = status if status == "Disposed" else "Released"

    # === Update product_investigations ===
    db.execute(
        text("""
            UPDATE product_investigations
            SET
                status = :status,
                resolved_at = GETDATE(),
                resolved_by = :resolved_by,
                comment = 
                    CASE 
                        WHEN comment IS NULL OR comment = '' THEN :note
                        ELSE comment + CHAR(13) + :note
                    END
            WHERE product_id = :product_id AND status = 'Under Investigation'
        """),
        {
            "status": status,
            "resolved_by": user_id,
            "product_id": product_id,
            "note": resolution_note
        }
    )

    # === Update the quarantined_products record === 
    db.execute(
        text("""
            UPDATE quarantined_products
            SET
                quarantine_status = :q_status,
                result = :q_result,
                resolved_at = GETDATE(),
                resolved_by = :resolved_by
            WHERE product_id = :product_id AND quarantine_status = 'Active'
        """),
        {
            "q_status": q_status,
            "q_result": resolution,
            "resolved_by": user_id,
            "product_id": product_id
        }
    ) 

    status_name = STATUS_MAP_QC_TO_BUSINESS.get(resolution, "Pending")
    update_product_status(
        db=db,
        product_id=product_id,
        status_name=status_name
    )

@transactional
def resolve_quarantine_record(
    db: Session,
    product_id: int,
    result: str,
    resolved_by: int,
    comment: str
):
    """
    Updates a quarantine record once QM reviews the product.
    """
    status = "Released" if result in ("Passed", "B-Ware") else "Disposed"

    resolution_note = f"[Resolution {datetime.now().strftime('%Y-%m-%d %H:%M')}]: {result}"
    if comment:
        resolution_note += f" — {comment}"

    db.execute(
        text("""
            UPDATE quarantined_products
            SET
                quarantine_status = :status,
                result = :result,
                resolved_at = :resolved_at,
                resolved_by = :resolved_by,
                quarantine_reason = 
                    CASE 
                        WHEN quarantine_reason IS NULL OR quarantine_reason = '' THEN :note
                        ELSE quarantine_reason + CHAR(13) + :note
                    END
            WHERE product_id = :pid AND quarantine_status = 'Active'
        """),
        {
            "status": status,
            "result": result,
            "resolved_at": datetime.now(timezone.utc),
            "resolved_by": resolved_by,
            "pid": product_id,
            "note": resolution_note
        }
    )

    status_name = STATUS_MAP_QC_TO_BUSINESS.get(result, "Pending")
    update_product_status(
        db=db,
        product_id=product_id,
        status_name=status_name
    )

@transactional
def create_quarantine_record(
    db: Session,
    product_id: int,
    source: str,
    quarantined_by: int,
    reason: str | None = None
):
    from_stage_id = db.scalar(
        text("SELECT current_stage_id FROM product_tracking WHERE id = :pid"),
        {"pid": product_id}
    )
    db.execute(
        text("""
            INSERT INTO quarantined_products (
                product_id, from_stage_id, source, quarantined_by, quarantine_reason, quarantine_status, quarantine_date
            )
            VALUES (:pid, :stage, :source, :user, :reason, 'Active', :q_date)
        """),
        {
            "pid": product_id,
            "stage": from_stage_id,
            "source": source,
            "user": quarantined_by,
            "reason": reason or None,
            "q_date": datetime.now(timezone.utc)
        }
    )

@transactional
def search_products_for_quarantine(db: Session, mode:str, value: str) -> list[ProductQuarantineSearchResult]:
    """
    Searches products for ad-hoc quarantine
    """

    stmt = (
        select(
            ProductTracking.id.label("product_id"),
            ProductTracking.tracking_id,
            ProductType.name.label("product_type"),
            ProductRequest.lot_number,
            ProductRequest.id.label("request_id"),
            ProductHarvest.id.label("harvest_id"),
            LifecycleStages.stage_name.label("current_stage_name"),
            ProductStatuses.status_name.label("current_status"),
            StorageLocation.location_name,
            ProductTracking.last_updated_at,
        )
        .join(ProductHarvest, ProductTracking.harvest_id == ProductHarvest.id)
        .join(ProductRequest, ProductHarvest.request_id == ProductRequest.id)
        .join(ProductType, ProductRequest.product_id == ProductType.id)
        .join(LifecycleStages, ProductTracking.current_stage_id == LifecycleStages.id)
        .outerjoin(ProductStatuses, ProductTracking.current_status_id == ProductStatuses.id)
        .outerjoin(StorageLocation, ProductTracking.location_id == StorageLocation.id)
        .outerjoin(
            QuarantinedProducts,
            (QuarantinedProducts.product_id == ProductTracking.id) &
            (QuarantinedProducts.quarantine_status == "Active")
        )
        .where(
            (ProductStatuses.status_name != "Waste") | (ProductStatuses.status_name.is_(None))
        )
        .where(QuarantinedProducts.id.is_(None))
    )
    
    # Add filters based on mode
    if mode == "Product ID":
        stmt = stmt.where(ProductTracking.id == int(value))

    elif mode == "Lot Number":
        stmt = stmt.where(ProductRequest.lot_number == value)
    
    elif mode == "Treatment Batch":
        stmt = stmt.join(
            TreatmentBatchProduct,
            TreatmentBatchProduct.product_id == ProductTracking.id
        ).where(TreatmentBatchProduct.batch_id == int(value))

    elif mode == "Filament Mount ID":
        stmt = stmt.where(ProductHarvest.filament_mounting_id == int(value))

    results = db.execute(stmt).all()
    return [ProductQuarantineSearchResult(**row._mapping) for row in results]

@transactional
def mark_products_ad_hoc_quarantine(db: Session, product_ids: list[int], user_id: int, reason_ids: list[int], comment: str):
    """
    Marks products for ad-hoc quarantine, updates stage & status, and logs the reason.
    """
    if not product_ids:
        return
    
    reason_ids = list(dict.fromkeys(reason_ids))

    quarantine_stage_id = db.scalar(
        select(LifecycleStages.id).where(LifecycleStages.stage_code == "Quarantine")
    )
    if not quarantine_stage_id:
        raise ValueError("Stage 'Quarantine' not found.")
    
    for product_id in product_ids:
        qp = QuarantinedProducts(
            product_id=product_id,
            from_stage_id=db.scalar(
                select(ProductTracking.current_stage_id).where(ProductTracking.id == product_id)
            ),
            source="Ad-Hoc",
            quarantined_by=user_id,
            quarantine_reason=comment,
            quarantine_status="Active"
        )
        db.add(qp)
        db.flush()

        db.execute(
            text(
                """
                    INSERT INTO quarantined_product_reasons
                        (quarantine_id, reason_id)
                    VALUES (:qp_id, :rid)
                """
            ),
            [{"qp_id": qp.id, "rid": rid} for rid in reason_ids]
        )
        update_product_stage(
            db=db,
            product_id=product_id,
            new_stage_id=quarantine_stage_id,
            reason=f"Ad-Hoc Quarantine: {comment}",
            user_id=user_id
        )
        update_product_status(db, product_id, "In Quarantine")

    db.commit()