import string
from sqlalchemy.orm import Session
from sqlalchemy import text, select, or_
from datetime import datetime
from models.production_models import ProductRequest, ProductHarvest, ProductTracking, ProductSKU
from schemas.production_schemas import ProductRequestCreate
from schemas.audit_schemas import FieldChangeAudit
from services.audit_services import update_record_with_audit
from services.tracking_service import generate_tracking_id, record_materials_post_harvest
from utils.db_transaction import transactional


_ALPHABET = string.digits + string.ascii_uppercase

def to_base36(n: int) -> str:
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0:
        return "0"
    out = []
    while n:
        n, r = divmod(n, 36)
        out.append(_ALPHABET[r])
    return "".join(reversed(out))

def generate_lot_number(db: Session) -> str:
    yy = f"{datetime.now().year % 100:02d}"
    batch_number = db.execute(text("SELECT NEXT VALUE FOR dbo.seq_batch_number")).scalar_one()
    cc = to_base36(int(batch_number)).rjust(2, "0")
    return f"{yy}{cc}"

def allocate_seq_for_lot(db: Session, lot_number: str) -> int:
    row = db.execute(
        text("EXEC dbo.AllocateNextSeqForLot @lot_number=:lot"),
        {"lot": lot_number},
    ).mappings().one()

    return int(row["item_seq"])

def build_product_code(db: Session, request_id: int) -> str:
    lot = db.execute(
        text("SELECT lot_number FROM dbo.product_requests WHERE id=:rid"),
        {"rid": request_id},
    ).scalar_one()

    if not lot or len(lot) < 4:
        raise ValueError("Request lot_number (YYCC) is missing/invalid")
    
    seq = allocate_seq_for_lot(db, lot)

    return f"{lot}{seq:04d}"

@transactional
def get_requestable_skus(db: Session) -> list[tuple[int, str, str]]:
    """
    Return (sku_id, sku_code, name) for SKUs a user can request to print:
    serialized single units, not bundles, active.
    """
    stmt = select(
        ProductSKU.id,
        ProductSKU.sku,
        ProductSKU.name,
        ProductSKU.is_bundle,
        ProductSKU.pack_qty,
    ).where(
        ProductSKU.is_active == True,
        or_(ProductSKU.is_serialized == True, ProductSKU.is_bundle == True,)
    ).order_by(ProductSKU.name)
    return db.execute(stmt).all()

# @transactional
# def get_product_types(db: Session) -> list[tuple[int, str]]:
#     stmt = select(ProductType.id, ProductType.name).order_by(ProductType.name)
#     return db.execute(stmt).all()

@transactional
def insert_product_request(db: Session, data: ProductRequestCreate):
    lot = generate_lot_number(db)
    for _ in range(data.quantity):
        request = ProductRequest(
            requested_by=data.requested_by,
            sku_id=data.sku_id,
            lot_number=lot,
            notes=data.notes,
            is_tech_transfer=bool(getattr(data, "is_tech_transfer", False)),
        )
        db.add(request)
    db.commit()

@transactional
def get_pending_requests(db: Session) -> list[dict]:
    sql = """
        SELECT
            pr.id,
            ps.sku AS sku,
            ps.name AS sku_name,
            u.display_name AS requested_by,
            pr.lot_number,
            pr.status,
            pr.requested_at,
            pr.is_tech_transfer,  
            sps.average_weight_g,
            sps.weight_buffer_g
        FROM product_requests pr
        JOIN product_skus ps ON ps.id = pr.sku_id
        LEFT JOIN product_print_specs sps ON sps.sku_id = ps.id
        JOIN users u ON u.id = pr.requested_by
        WHERE pr.status = 'Pending'
        AND lot_number <> 'LEGACY_LOT'
        ORDER BY pr.requested_at ASC
    """
    result = db.execute(text(sql))
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]

@transactional
def insert_product_harvest(db: Session, request_id: int, filament_mount_id: int, printed_by: int, lid_id: int, seal_id: str):
    # === Insert Harvest Record ===
    harvest = ProductHarvest(
        request_id=request_id,
        filament_mounting_id=filament_mount_id,
        printed_by=printed_by,
        lid_id=lid_id,
        seal_id=seal_id
    )
    db.add(harvest)
    db.flush()

    # === Creates a Unique Tracking ID === 
    # tracking_id = generate_tracking_id(db)

    # === Gets the Status ID ===
    pending_status_id = db.scalar(
        text("SELECT id FROM product_statuses WHERE status_name = 'Pending'")
    )

    # === Derive the SKU for this unit (direct via request) ===
    req = db.execute(
        text("SELECT sku_id, is_tech_transfer FROM product_requests WHERE id = :rid"),
        {"rid": request_id},
    ).mappings().one()

    sku_id = int(req["sku_id"])
    is_tt = bool(req.get("is_tech_transfer", 0))

    product_type_id = db.scalar(text("SELECT product_type_id FROM product_skus WHERE id = :sid"), {"sid": sku_id})

    product_code = build_product_code(db, request_id)

    # === Insert Product Tracking Record ===
    tracking = ProductTracking(
        harvest_id=harvest.id,
        sku_id=sku_id,
        product_type_id=product_type_id,
        current_stage_id=1,
        current_status_id=pending_status_id,
        product_code=product_code,
        was_tech_transfer=is_tt,
    )
    db.add(tracking)
    db.flush()

    # === Records the lid + seal usage ===
    record_materials_post_harvest(db=db, product_id=tracking.id, harvest_id=harvest.id, user_id=printed_by)

    # === Updates the product request status ===
    db.execute(
        text("UPDATE product_requests SET status = 'Fulfilled' WHERE id = :id"),
        {"id": request_id}
    )
    
    db.commit()
    return {"id": tracking.product_id, "product_code": tracking.product_code}

@transactional
def cancel_product_request(db: Session, request_id: int):
    db.execute(
        text("UPDATE product_requests SET status = 'Cancelled' WHERE id = :id"),
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
            ph.seal_id,
            pr.id AS request_id,
            ps.sku AS sku,
            ps.name AS sku_name,
            f.serial_number AS filament_serial,
            p.name AS printer_name,
            l.serial_number AS lid_serial,
            u.display_name AS printed_by,
            ph.print_date
        FROM product_harvest ph
        JOIN product_requests pr ON ph.request_id = pr.id
        JOIN product_skus ps ON pr.sku_id = ps.id
        JOIN filament_mounting fm ON ph.filament_mounting_id = fm.id
        JOIN filaments f ON fm.filament_tracking_id = f.id
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