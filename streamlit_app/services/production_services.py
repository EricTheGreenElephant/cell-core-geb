from sqlalchemy.orm import Session
from sqlalchemy import text, select
from datetime import datetime
from models.production_models import ProductRequest, ProductHarvest, ProductTracking, ProductType
from schemas.production_schemas import ProductRequestCreate
from schemas.audit_schemas import FieldChangeAudit
from services.audit_services import update_record_with_audit
from utils.db_transaction import transactional


def generate_lot_number() -> str:
    return f"LOT-{datetime.now().strftime('%Y%d%m%H%S')}"

@transactional
def get_product_types(db: Session) -> list[tuple[int, str]]:
    stmt = select(ProductType.id, ProductType.name).order_by(ProductType.name)
    return db.execute(stmt).all()

@transactional
def insert_product_request(db: Session, data: ProductRequestCreate):
    lot = generate_lot_number()
    for _ in range(data.quantity):
        request = ProductRequest(
            requested_by=data.requested_by,
            product_id=data.product_id,
            lot_number=lot,
            notes=data.notes
        )
        db.add(request)
    db.commit()

@transactional
def get_pending_requests(db: Session) -> list[dict]:
    sql = """
        SELECT
            pr.id,
            pt.name AS product_type,
            u.display_name AS requested_by,
            pr.lot_number,
            pr.status,
            pr.requested_at,
            pt.average_weight,
            pt.buffer_weight
        FROM product_requests pr
        JOIN product_types pt ON pt.id = pr.product_id
        JOIN users u ON u.id = pr.requested_by
        WHERE pr.status = 'Pending'
        ORDER BY pr.requested_at ASC
    """
    result = db.execute(text(sql))
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]

@transactional
def insert_product_harvest(db: Session, request_id: int, filament_mount_id: int, printed_by: int, lid_id: int):
    harvest = ProductHarvest(
        request_id=request_id,
        filament_mounting_id=filament_mount_id,
        printed_by=printed_by,
        print_status="Printed",
        lid_id=lid_id
    )
    db.add(harvest)
    db.flush()

    tracking = ProductTracking(
        harvest_id=harvest.id,
        current_status="Printed"
    )
    db.add(tracking)

    db.execute(
        text("UPDATE product_requests SET status = 'Fulfilled' WHERE id = :id"),
        {"id": request_id}
    )
    db.commit()

@transactional
def cancel_product_request(db: Session, request_id: int):
    db.execute(
        text("UDPATE product_requests SET status = 'Cancelled' WHERE id = :id"),
        {"id": request_id}
    )
    db.commit()

@transactional
def get_harvested_products(db: Session) -> list[dict]:
    sql = """
        SELECT
            ph.id AS harvest_id,
            ph.filament_mounting_id AS mount_id,
            ph.lid_id AS lid_id,
            pr.id AS request_id,
            pt.name AS product_type,
            f.serial_number AS filament_serial,
            p.name AS printer_name,
            l.serial_number AS lid_serial,
            u.display_name AS printed_by,
            ph.print_date,
            ph.print_status
        FROM product_harvest ph
        JOIN product_requests pr ON ph.request_id = pr.id
        JOIN product_types pt ON pr.product_id = pt.id
        JOIN filament_mounting fm ON ph.filament_mounting_id = fm.id
        JOIN filaments f ON fm.filament_id = f.id
        JOIN printers p ON fm.printer_id = p.id
        JOIN lids l ON ph.lid_id = l.id
        JOIN users u ON ph.printed_by = u.id
        ORDER BY ph.print_date DESC
    """
    result = db.execute(text(sql))
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]

@transactional
def update_harvest_fields(
    db: Session,
    harvest_id: int,
    updates: dict[str, tuple],
    reason: str,
    user_id: int
):
    for field, (old_value, new_value) in updates.items():
        audit = FieldChangeAudit(
            table="product_harvest",
            record_id=harvest_id,
            field=field,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            changed_by=user_id
        )
        update_record_with_audit(db, audit)
    db.commit()

@transactional
def undo_product_harvest(db: Session, harvest_id: int, user_id: int, reason: str):
    harvest = db.get(ProductHarvest, harvest_id)
    if not harvest:
        raise ValueError(f"Harvest record with id={harvest_id} not found.")
    
    tracking_stmt = select(ProductTracking).where(ProductTracking.harvest_id == harvest_id)
    tracking = db.scalars(tracking_stmt).first()
    if tracking:
        db.delete(tracking)
        db.flush()

    request = db.get(ProductRequest, harvest.request_id)
    if request: 
        audit = FieldChangeAudit(
            table="product_requests",
            record_id=request.id,
            field="status",
            old_value=request.status,
            new_value="Pending",
            reason=reason,
            changed_by=user_id
        )
        update_record_with_audit(db, audit)
        request.status = "Pending"
    
    db.delete(harvest)
    db.commit()