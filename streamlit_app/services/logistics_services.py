from sqlalchemy.orm import Session
from sqlalchemy import text
from models.logistics_models import TreatmentBatch, TreatmentBatchProduct
from schemas.logistics_schemas import TreatmentBatchCreate
from utils.db_transaction import transactional


@transactional
def get_qc_passed_products(db: Session) -> list[dict]:
    sql = """
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
        WHERE pt.current_status = 'In Interim Storage'
            AND pt.id NOT IN (
                SELECT product_id FROM treatment_batch_products
            )
    """
    result = db.execute(text(sql))
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]


@transactional
def create_treatment_batch(db: Session, data: TreatmentBatchCreate):
    batch = TreatmentBatch(sent_by=data.sent_by, notes=data.notes, status="Shipped")
    db.add(batch)
    db.flush()

    for item in data.tracking_data:
        product = TreatmentBatchProduct(
            batch_id=batch.id,
            product_id=item.tracking_id,
            surface_treat=bool(item.surface_treat),
            sterilize=bool(item.sterilize)
        )
        db.add(product)
        db.execute(
            text("""
                 UPDATE product_tracking
                 SET current_status = 'Sent for Treatment', last_updated_at = GETDATE()
                 WHERE id = :id
                """),
                {"id": item["tracking_id"]}
        )
    db.commit()


@transactional
def get_qc_products_needing_storage(db: Session) -> list[dict]:
    sql = """
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
    """
    result = db.execute(text(sql))
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]


@transactional
def get_post_treatment_products_needing_storage(db: Session) -> list[dict]:
    sql = """
        SELECT
            pt.id AS tracking_id,
            ph.id AS harvest_id,
            t.name AS product_type,
            pqi.qc_result AS inspection_result
        FROM product_tracking pt
        JOIN product_harvest ph ON pt.harvest_id = ph.id
        JOIN product_requests pr ON pr.id = ph.request_id
        JOIN product_types t ON pr.product_id = t.id
        JOIN post_treatment_inspections pqi ON pt.id = pqi.product_id
        WHERE pt.current_status IN ('Post-Treatment Inspected')
            AND pqi.qc_result IN ('Internal Use', 'QM Request')
    """
    result = db.execute(text(sql))
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]


@transactional
def assign_storage_to_products(db: Session, product_ids: list[int], location_id: int, status: str):
    for pid in product_ids:
        db.execute(
            text("""
                UPDATE product_tracking
                SET location_id = :loc_id, current_status = :status, last_updated_at = GETDATE()
                WHERE id = :pid
            """),
            {"loc_id": location_id, "status": status, "pid": pid}
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
            pt.id AS tracking_id,
            pt.current_status,
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
        LEFT JOIN product_quality_control pqc ON ph.id = pqc.harvest_id
        WHERE tbp.batch_id = :batch_id
    """
    result = db.execute(text(sql), {"batch_id": batch_id})
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]


@transactional
def update_post_treatment_qc(db: Session, product_qc: list[dict], inspected_by: int):
    for item in product_qc:
        db.execute(
            text("""
                INSERT INTO post_treatment_inspections (
                    product_id, surface_treated, sterilized, visual_pass, qc_result, inspected_by
                )
                VALUES (:pid, :treated, :sterilized, :visual, :qc_result, :inspector)
            """),
            {
                "pid": item["tracking_id"],
                "treated": item["surface_treat"],
                "sterilized": item["sterilize"],
                "visual": item["visual_pass"],
                "qc_result": item["qc_result"],
                "inspector": inspected_by
            }
        )
        db.execute(
            text("""
                UPDATE product_tracking
                SET current_status = 'Post-Treatment Inspected', last_updated_at = GETDATE()
                WHERE id = :pid
            """),
            {"pid": item["tracking_id"]}
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