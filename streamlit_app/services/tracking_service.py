from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session
from models.production_models import ProductTracking
from utils.db_transaction import transactional


def generate_tracking_id(db: Session, date=None) -> str:
    if not date:
        date = datetime.today()
    
    prefix = date.strftime("PRD-%Y%d%m")

    count = db.query(ProductTracking).filter(
        ProductTracking.tracking_id.like(f"{prefix}-%")
    ).count()

    return f"{prefix}-{count + 1:05d}"

def log_product_status_change(db: Session, product_id: int, from_stage_id: int, to_stage_id: int, reason: str, user_id: int):
    db.execute(
        text("""
            INSERT INTO product_status_history
                (product_id, from_stage_id, to_stage_id, reason, changed_by, changed_at)
            VALUES
                (:product_id, :from_stage_id, :to_stage_id, :reason, :user_id, GETDATE())
        """),
        {
            "product_id": product_id,
            "from_stage_id": from_stage_id,
            "to_stage_id": to_stage_id,
            "reason": reason, 
            "user_id": user_id
        }
    )

def update_product_stage(
        db: Session,
        product_id: int,
        new_stage_id: int,
        reason: str,
        user_id: int,
        location_id: Optional[int] = None
):
    from_stage_id = db.scalar(
        text("SELECT current_stage_id FROM product_tracking WHERE id = :product_id"),
        {"product_id": product_id}
    )

    update_fields = [
        "current_stage_id = :new_stage_id",
        "last_updated_at = GETDATE()",
        "previous_stage_id = :prev"
    ]
    params = {
        "new_stage_id": new_stage_id,
        "prev": from_stage_id,
        "product_id": product_id
    }

    if location_id is not None:
        update_fields.append("location_id = :location_id")
        params["location_id"] = location_id
    
    update_sql = f"""
        UPDATE product_tracking
        SET {", ".join(update_fields)}
        WHERE id = :product_id
    """

    db.execute(text(update_sql), params)

    log_product_status_change(
        db=db,
        product_id=product_id,
        from_stage_id=from_stage_id,
        to_stage_id=new_stage_id,
        reason=reason,
        user_id=user_id
    )

def update_product_status(db: Session, product_id: int, status_name: str):
    """
    Updates the product's business status (A-Ware, B-Ware, In Quarantine, Waste)
    """
    status_id = db.scalar(
        text("SELECT id FROM product_statuses WHERE status_name = :name"),
        {"name": status_name}
    )
    if not status_id:
        raise ValueError(f"Status '{status_name}' not found in product_statuses table.")

    db.execute(
        text("""
            UPDATE product_tracking
            SET current_status_id = :status_id, last_updated_at = GETDATE()
            WHERE id = :pid
        """),
        {"status_id": status_id, "pid": product_id}
    )

def get_material_usage_summary(db: Session) -> list[dict]:
    """
    Queries the v_material_usage_summary view and returns summary rows as dictionaries.
    """
    sql = """
        SELECT * FROM v_material_usage_summary
        ORDER BY product_type
    """
    result = db.execute(text(sql))
    columns = result.keys()
    return [dict(zip(columns, row)) for row in result.fetchall()]

def record_materials_post_harvest(db: Session, product_id: int, harvest_id: int, user_id: int):
    """
    Records usage of lid and seal immediately after harvest.
    """
    # Get lid_id and harvest linkage
    row = db.execute(text("""
        SELECT
            ph.lid_id,
            ph.seal_id,
            l.serial_number AS lid_lot_number,
            s.serial_number AS seal_lot_number                        
        FROM product_harvest ph
        JOIN lids l ON ph.lid_id = l.id
        JOIN seals s ON ph.seal_id = s.id
        WHERE ph.id = :harvest_id
    """), {"harvest_id": harvest_id}).fetchone()
    
    if not row:
        raise ValueError(f"Harvest ID {harvest_id} not found.")
    
    materials = [
        {"type": "Lid", "id": row.lid_id, "lot": row.lid_lot_number},
        {"type": "Seal", "id": row.seal_id, "lot": row.seal_lot_number}
    ]
    now = datetime.now(timezone.utc)

    for material in materials:
        db.execute(text("""
            INSERT INTO material_usage (
                product_id, harvest_id, material_type, lot_number, used_quantity, used_at, used_by
            )
            VALUES (:product_id, :harvest_id, :material_type, :lot_number, 1, :timestamp,  :user_id)
        """), {
            "product_id": product_id,
            "harvest_id": harvest_id,
            "material_type": material["type"],
            "lot_number": material["lot"],
            "timestamp": now,
            "user_id": user_id,
        })
    
    db.commit()

def record_filament_usage_post_qc(db: Session, product_id: int, harvest_id: int, weight_grams: float, user_id: int):
    """
    Records filament usage based on weight measured during QC.
    """
    row = db.execute(text("""
        SELECT
            fm.filament_id,
            f.lot_number
        FROM product_harvest ph
        JOIN filament_mounting fm ON ph.filament_mounting_id = fm.id
        JOIN filaments f ON fm.filament_id = f.id
        WHERE ph.id = :harvest_id
    """), {"harvest_id": harvest_id}).fetchone()

    db.execute(text("""
        INSERT INTO material_usage (
            product_id, harvest_id, material_type, lot_number, used_quantity, used_at, used_by
        )
        VALUES (:product_id, :harvest_id, 'Filament', :lot_number, :qty, :timestamp, :user_id)
    """), {
        "product_id": product_id,
        "harvest_id": harvest_id,
        "lot_number": row.lot_number,
        "qty": weight_grams,
        "timestamp": datetime.now(timezone.utc),
        "user_id": user_id
    })

    db.commit()

def validate_materials_available(db: Session, sku_id: int, quantity: int):
    """
    Validates whether there is sufficient material from a single lot/batch of
    filament, lids, and seals to fulfill the product request.
    Returns a list of error messages. Empty list means validation passed. 
    """
    errors = []
    info_message = None

    # === Get weight requirement ===
    spec = db.execute(text(
        """
            SELECT sps.average_weight_g, sps.weight_buffer_g
            FROM product_skus ps
            LEFT JOIN sku_print_specs sps ON sps.sku_id = ps.id
            WHERE ps.id = :sid
        """
    ), {"sid": sku_id}).fetchone()

    if not spec or spec.average_weight_g is None or spec.weight_buffer_g is None:
        return (["Selected SKU has no print specs (average_weight_g/weight_buffer_g)."], None)
    
    weight_per_unit = float(spec.average_weight_g) + float(spec.weight_buffer_g)
    total_required_weight = weight_per_unit * quantity

    # === Filament availability ===
    filament_lots = db.execute(text(
        """
            SELECT f.lot_number, SUM(fm.remaining_weight) AS available_grams
            FROM filament_mounting fm
            JOIN filaments f ON fm.filament_id = f.id
            WHERE fm.status = 'In Use' AND f.qc_result = 'PASS'
            GROUP BY f.lot_number
        """
    )).fetchall()

    # used_filament = db.execute(text(
    #     """
    #         SELECT lot_number, SUM(used_quantity) AS used_grams
    #         FROM material_usage
    #         WHERE material_type = 'Filament' AND lot_number IS NOT NULL
    #         GROUP BY lot_number
    #     """
    # )).fetchall()
    # used_filament_map = {row.lot_number: float(row.used_grams or 0) for row in used_filament}
    
    
    best_filament = None
    max_units_filament = 0
    for row in filament_lots:
        # remaining = float(row.available_grams or 0) - used_filament_map.get(row.lot_number, 0.0)
        remaining = float(row.available_grams or 0)
        units = int(remaining // weight_per_unit)
        if units > max_units_filament:
            max_units_filament = units
            best_filament = row.lot_number
            best_remaining = remaining
    
    if max_units_filament < quantity:
        errors.append(f"Not enough filament from any single lot fulfill {total_required_weight:.2f}g. Only {best_remaining:.2f}g from LOT {best_filament}.")

    # === Lid availability ===
    lid_batches = db.execute(text(
        """
            SELECT serial_number, SUM(quantity) AS available_units
            FROM lids
            WHERE qc_result = 'PASS'
            GROUP BY serial_number
        """
    )).fetchall()

    used_lids = db.execute(text(
        """
            SELECT lot_number, COUNT(*) AS used_units
            FROM material_usage
            WHERE material_type = 'Lid' AND lot_number IS NOT NULL
            GROUP BY lot_number
        """
    )).fetchall()
    used_lids_map = {row.lot_number: int(row.used_units or 0) for row in used_lids}

    best_lid = None
    max_units_lid = 0
    for row in lid_batches:
        remaining = int(row.available_units or 0) - used_lids_map.get(row.serial_number, 0)
        if remaining > max_units_lid:
            max_units_lid = remaining
            best_lid = row.serial_number
    
    if max_units_lid < quantity:
        errors.append(f"Not enough lids from any single batch to fulfill {quantity} units.")

    # === Seal availability ===
    seal_batches = db.execute(text(
        """
            SELECT serial_number, SUM(quantity) AS available_units
            FROM seals
            WHERE qc_result = 'PASS'
            GROUP BY serial_number
        """
    )).fetchall()

    used_seals = db.execute(text(
        """
            SELECT lot_number, COUNT(*) AS used_units
            FROM material_usage
            WHERE material_type = 'Seal' AND lot_number IS NOT NULL
            GROUP BY lot_number
        """
    )).fetchall()
    used_seals_map = {row.lot_number: int(row.used_units or 0) for row in used_seals}

    best_seal = None
    max_units_seal = 0
    for row in seal_batches:
        remaining = int(row.available_units or 0) - used_seals_map.get(row.serial_number, 0)
        if remaining > max_units_seal:
            max_units_seal = remaining
            best_seal = row.serial_number

    if max_units_seal < quantity:
        errors.append(f"Not enough seals from any single batch to fulfill {quantity} units.")
    
    if errors:
        max_possible_unit = min(max_units_filament, max_units_lid, max_units_seal)
        info_message = (
            f"The max number of units based on available materials from "
            f"filament lot: {best_filament}, lid batch: {best_lid}, and seal batch: {best_seal} "
            f"is {max_possible_unit} units."
        )
    
    return errors, info_message