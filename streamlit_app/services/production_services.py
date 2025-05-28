from sqlalchemy.orm import Session
from sqlalchemy import text, select
from datetime import datetime
from models.production_models import ProductRequest, ProductHarvest, ProductTracking, ProductType
from schemas.production_schemas import ProductRequestCreate
from utils.db_transaction import transactional



@transactional
def get_product_types(db: Session) -> list[tuple[int, str]]:
    stmt = select(ProductType.id, ProductType.name).order_by(ProductType.name)
    return db.execute(stmt).all()

@transactional
def generate_lot_number() -> str:
    return f"LOT-{datetime.now().strftime('%Y%d%m%H%S')}"

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