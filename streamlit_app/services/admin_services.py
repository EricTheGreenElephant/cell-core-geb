from sqlalchemy import text, select
from sqlalchemy.orm import Session
from schemas.audit_schemas import FieldChangeAudit
from models.production_models import ProductSKU
from utils.db_transaction import transactional
from services.audit_services import update_record_with_audit

def get_print_specs_for_sku(db: Session, sku_id: int) -> dict | None:
    row = db.execute(
        text("""
            SELECT sku_id, height_mm, diameter_mm, average_weight_g, weight_buffer_g
            FROM product_print_specs
            WHERE sku_id = :sku_id
        """),
        {"sku_id": sku_id},
    ).mappings().first()
    return dict(row) if row else None

def upsert_print_specs(
        db: Session, 
        sku_id: int, 
        height_mm: float, 
        diameter_mm: float,
        average_weight_g: float, 
        weight_buffer_g: float,
        reason: str,
        changed_by: int
    ) -> None:
    if height_mm <= 0 or diameter_mm <= 0 or average_weight_g <= 0:
        raise ValueError("Height, diameter, and average weight must be > 0.")
    if weight_buffer_g < 0:
        raise ValueError("Weight buffer must be >= 0.")
    if not reason or not reason.strip():
        raise ValueError("Audit reason is required.")
    if not changed_by:
        raise ValueError("changed_by (user_id) is required.")

    existing = get_print_specs_for_sku(db, sku_id)

    new_vals = {
        "height_mm": height_mm,
        "diameter_mm": diameter_mm,
        "average_weight_g": average_weight_g,
        "weight_buffer_g": weight_buffer_g
    }

    if existing is None:
        db.execute(text("""
            INSERT INTO product_print_specs
                (sku_id, height_mm, diameter_mm, average_weight_g, weight_buffer_g)
            VALUES
                (:sku_id, :h, :d, :awg, :wbg)
        """), {"sku_id": sku_id, "h": height_mm, "d": diameter_mm, "awg": average_weight_g, "wbg": weight_buffer_g})

        # --- Audit each field as "created" (old=None) ---
        for field, new_value in new_vals.items():
            audit = FieldChangeAudit(
                table="product_print_specs",
                record_id=sku_id,          # record_id will be sku_id for this table
                field=field,
                old_value=None,
                new_value=new_value,
                reason=reason,
                changed_by=changed_by,
            )
            update_record_with_audit(db, audit, update=False)

    else:
        # --- Update row ---
        db.execute(text("""
            UPDATE product_print_specs
            SET height_mm = :h,
                diameter_mm = :d,
                average_weight_g = :awg,
                weight_buffer_g = :wbg
            WHERE sku_id = :sku_id
        """), {"sku_id": sku_id, "h": height_mm, "d": diameter_mm, "awg": average_weight_g, "wbg": weight_buffer_g})

        # --- Audit only changed fields ---
        for field, new_value in new_vals.items():
            old_value = existing.get(field)
            audit = FieldChangeAudit(
                table="product_print_specs",
                record_id=sku_id,
                field=field,
                old_value=old_value,
                new_value=new_value,
                reason=reason,
                changed_by=changed_by,
            )
            update_record_with_audit(db, audit, update=False)

    db.commit()

@transactional
def get_skus_with_print_specs_flag(db: Session) -> list[dict]:
    sql = """
        SELECT
            ps.id,
            ps.sku,
            ps.name,
            ps.is_active,
            CASE WHEN pps.sku_id IS NULL THEN 0 ELSE 1 END AS has_print_specs
        FROM product_skus ps
        LEFT JOIN product_print_specs pps ON pps.sku_id = ps.id
        ORDER BY ps.name, ps.sku
    """
    return [dict(r) for r in db.execute(text(sql)).mappings().all()]