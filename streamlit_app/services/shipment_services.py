from sqlalchemy import text, bindparam
from collections import defaultdict
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from schemas.audit_schemas import FieldChangeAudit
from services.audit_services import update_record_with_audit
from services.tracking_service import update_product_stage
from services.sales_services import _get_order_header_query
from models.shipment_models import Shipment, ShipmentSKUItems, ShipmentUnitItems
from models.sales_models import Order
from utils.db_transaction import transactional


def get_open_order_headers(db: Session) -> list[dict]:
    query = _get_order_header_query() + " WHERE o.status = 'Processing' ORDER BY o.order_date ASC"
    result = db.execute(text(query)).fetchall()
    return [dict(r._mapping) for r in result]

def get_open_orders_with_items(db: Session, order_id: int) -> dict:
    items = db.execute(text(
        """
            SELECT
                oi.id,
                oi.product_sku_id, 
                s.sku, 
                s.name AS sku_name,
                s.is_bundle,
                s.is_serialized, 
                s.pack_qty,
                oi.quantity
            FROM order_items oi
            JOIN product_skus s ON oi.product_sku_id = s.id
            WHERE oi.order_id = :oid
        """
    ), {"oid": order_id}).mappings().all()

    return {
        "items": [dict(r) for r in items]
    }

def build_unit_requirements(db: Session, order_items: list[dict]) -> dict[int, dict]:
    out: dict[int, dict] = {}
    for row in order_items:
        sku_id = int(row["product_sku_id"])
        pack_qty = int(row.get("pack_qty") or 1)
        order_qty = int(row["quantity"])
        required_units = order_qty * pack_qty
        out[sku_id] = {
            "required_units": required_units,
            "order_qty": order_qty,
            "sku": row["sku"],
            "sku_name": row["sku_name"],
            "pack_qty": pack_qty,
            "is_bundle": bool(row.get("is_bundle")),
            "is_serialized": bool(row.get("is_serialized"))
        }
    return out

def expand_sku_to_components(db: Session, parent_sku_id: int, count: int = 1) -> dict[int, int]:
    """
    Returns {component_sku_id: total_required_qty} for 'count' of parent_sku_id.
    If not BOM rows, returns {parent_sku_id: count}
    """
    bom = db.execute(text(
        """
            SELECT component_sku_id, component_qty
            FROM sku_bom
            WHERE parent_sku_id = :pid
        """
    ), {"pid": parent_sku_id}).mappings().all()

    if not bom:
        return {parent_sku_id: count}
    
    need = defaultdict(int)
    for row in bom:
        comp_id = row["component_sku_id"]
        comp_qty = row["component_qty"] * count
        sub = expand_sku_to_components(db, comp_id, comp_qty)
        for k, v in sub.items():
            need[k] += v
    return dict(need)

    # expanded_components: list[dict] = []
    # for it in items:
    #     if it["is_bundle"]:
    #         comps = db.execute(text(
    #             """
    #                 SELECT component_sku_id, component_qty
    #                 FROM sku_bom
    #                 WHERE parent_sku_id = :pid
    #             """
    #         ), {"pid": it["sku_id"]}).mappings().all()
    #         for c in comps:
    #             expanded_components.append({
    #                 "sku_id": it["sku_id"],
    #                 "required_qty": it["quantity"]
    #             })
    #     else:
    #         expanded_components.append({
    #             "sku_id": it["sku_id"],
    #             "required_qty": it["quantity"]
    #         })
    
    # collapsed: dict[int, int] = {}
    # for row in expanded_components:
    #     collapsed[row["sku_id"]] = collapsed.get(row["sku_id"], 0) + int(row["required_qty"])

    # expanded = []
    # if collapsed:
    #     rows = db.execute(text(
    #         """
    #             SELECT id AS sku_id, sku, name AS sku_name, is_serialized
    #             FROM product_skus
    #             WHERE id IN :ids
    #         """
    #     ).bindparams(bindparam("ids", expanding=True)), {"ids": list(collapsed.keys())}).mappings().all()
    #     meta = {r["sku_id"]: dict(r) for r in rows}
    #     for sid, qty in collapsed.items():
    #         expanded.append({**meta[sid], "required_qty": qty})

    # return {
    #     "items_by_sku": items,
    #     "components_required": expanded
    # }

def get_fifo_inventory_by_sku(db: Session, sku_id: int, limit: int):
    """
    Returns FIFO unites (serialized) available for a given SKU.
    """
    rows = db.execute(text(
        """
            SELECT
                pt.id AS product_id,
                pt.tracking_id,
                ph.print_date,
                pt.last_updated_at
            FROM product_tracking pt
            JOIN product_harvest ph ON pt.harvest_id = ph.id
            JOIN product_requests pr ON ph.request_id = pr.id
            JOIN product_skus s ON pr.sku_id = s.id
            JOIN product_statuses ps ON pt.current_status_id = ps.id
            JOIN lifecycle_stages ls ON pt.current_stage_id = ls.id
            WHERE 
                pr.sku_id = :sku_id
                AND s.is_serialized = 1
                AND s.is_bundle = 0
                AND ls.stage_code = 'QMSalesApproval'
                AND ps.status_name IN ('A-Ware', 'B-Ware')
                AND ph.print_date >= DATEADD(year, -1, GETDATE())
            ORDER BY ph.print_date ASC
            OFFSET 0 ROWS FETCH NEXT :limit ROWS ONLY
        """
    ), {"sku_id": sku_id, "limit": limit}).mappings().all()

    return [dict(r) for r in rows]

def expand_order_skus_to_components(db: Session, order_items: list[dict]) -> dict[int, dict]:
    sku_meta = {
        r["id"]: r for r in db.execute(text(
            "SELECT id, sku, name AS sku_name, is_serialized FROM product_skus"
        )).mappings().all()
    }

    need = defaultdict(int)
    for row in order_items:
        expanded = expand_sku_to_components(db, row["product_sku_id"], row["quantity"])
        for cid, qty in expanded.items():
            need[cid] += qty
    
    out = {}
    for cid, qty in need.items():
        meta = sku_meta[cid]
        out[cid] = {"required_qty": qty, "sku": meta["sku"], "sku_name": meta["sku_name"], "is_serialized": bool(meta["is_serialized"])}
    return out 

@transactional
def create_shipment_from_order(
    db: Session,
    *,
    order_id: int,
    customer_id: int,
    creator_id: int,
    picked_by_sku: dict[int, list[dict]],
    non_serialized_counts: dict[int, int],
    updated_by: int,
    notes: str = ""
):
    # === Create Shipment ===
    shipment = Shipment(
        order_id=order_id,
        customer_id=customer_id,
        creator_id=creator_id,
        updated_by=updated_by,
        status="Pending",
        notes=notes
    )
    db.add(shipment)
    db.flush()

    # === Product Lifecycle Update ===
    pending_shipment_stage_id = db.scalar(
        text("SELECT id FROM lifecycle_stages WHERE stage_code = 'PendingShipment'")
    )

    sku_meta = {
        r["id"]: (int(r["pack_qty"] or 1), bool(r["is_bundle"]))
        for r in db.execute(text("SELECT id, pack_qty, is_bundle FROM product_skus")).mappings().all()
    }

    per_sku_units_inserted: dict[int, int] = defaultdict(int)

    for sku_id, units in picked_by_sku.items():
        for unit in (units or []):
            item = ShipmentUnitItems(
                shipment_id=shipment.id,
                product_id=unit["product_id"],
            )
            db.add(item)

            per_sku_units_inserted[sku_id] += 1

            if pending_shipment_stage_id:
                update_product_stage(
                    db=db,
                    product_id=unit["product_id"],
                    new_stage_id=pending_shipment_stage_id,
                    reason="Marked for Shipment",
                    user_id=creator_id
                )

    for sku_id, units in per_sku_units_inserted.items():
        pack_qty, is_bundle = sku_meta.get(int(sku_id), (1, False))
        qty = (units // pack_qty) if is_bundle and pack_qty > 0 else units
        if qty > 0:
            item = ShipmentSKUItems(
                shipment_id=shipment.id,
                product_sku_id=int(sku_id),
                quantity=int(qty)
            )
            db.add(item)

    for sku_id, qty in (non_serialized_counts or {}).items():
        if qty and qty > 0:
            db.add(ShipmentSKUItems(
                shipment_id=shipment.id,
                product_sku_id=int(sku_id),
                quantity=int(qty)
            ))
    # === Fetch Order ===
    order = db.query(Order).filter(Order.id == order_id).first()

    # === Update Audit Logs ===
    now_str = str(datetime.now(timezone.utc))

    for field, old, new in [
        ("status", order.status, "Completed"),
        ("updated_by", order.updated_by, updated_by),
        ("updated_at", str(order.updated_at), now_str)
    ]:
        update_record_with_audit(
            db=db,
            data=FieldChangeAudit(
                table="orders",
                record_id=order_id,
                field=field,
                old_value=old,
                new_value=new,
                reason="Shipment created",
                changed_by=updated_by
            ),
            update=False
        )
    
    # === Perform Final Update on Order ===
    order.status = "Completed"
    order.updated_by = updated_by
    order.updated_at = datetime.now(timezone.utc)

    db.commit()

def get_active_shipments(db: Session):
    rows = db.execute(text(
        """
            SELECT s.id AS shipment_id,
                s.status,
                s.order_id,
                s.customer_id,
                c.customer_name,
                s.created_date,
                s.ship_date,
                s.delivery_date,
                s.carrier,
                s.tracking_number
            FROM shipments s
            JOIN customers c ON s.customer_id = c.id
            WHERE s.status IN ('Pending', 'Shipped')
            ORDER BY s.created_date ASC
        """
    )).fetchall()

    return [dict(row._mapping) for row in rows]

def get_products_in_shipments(db: Session, shipment_id: int):
    rows = db.execute(text(
        """
            SELECT
                pt.id AS product_id,
                pt.tracking_id,
                s.sku,
                s.name AS sku_name,
                ph.print_date
            FROM shipment_unit_items si
            JOIN product_tracking pt ON si.product_id = pt.id
            JOIN product_harvest ph ON pt.harvest_id = ph.id
            JOIN product_requests pr ON ph.request_id = pr.id
            JOIN product_skus s ON pr.sku_id = s.id
            WHERE si.shipment_id = :sid
            ORDER BY ph.print_date
        """
    ), {"sid": shipment_id}).fetchall()

    return [dict(row._mapping) for row in rows]

def get_non_serialized_in_shipment(db: Session, shipment_id: int):
    rows = db.execute(text(
        """
            SELECT 
                ssi.product_sku_id AS sku_id,
                ps.sku,
                ps.name AS sku_name,
                ssi.quantity
            FROM shipment_sku_items ssi
            JOIN product_skus ps ON ps.id = ssi.product_sku_id
            WHERE ssi.shipment_id = :sid
            ORDER BY ps.sku
        """
    ), {"sid": shipment_id}).fetchall()

    return [dict(row._mapping) for row in rows]

@transactional
def mark_shipment_as_shipped(db: Session, shipment_id: int, user_id: int, carrier: str, tracking_number: str):
    db.execute(text(
        """
            UPDATE shipments
            SET status = 'Shipped',
                ship_date = GETDATE(),
                updated_at = GETDATE(),
                carrier = :carrier,
                tracking_number = :tracking
            WHERE id = :sid
        """
    ), {"sid": shipment_id, "carrier": carrier, "tracking": tracking_number})

    products = db.execute(text("SELECT product_id FROM shipment_unit_items WHERE shipment_id = :sid"),
                    {"sid": shipment_id}
                ).fetchall()
    
    shipped_stage_id = db.scalar(text("SELECT id FROM lifecycle_stages WHERE stage_code = 'Shipped'"))

    offsite_id = db.execute(
        text("SELECT id FROM storage_locations WHERE location_name = 'Offsite'")
    ).scalar_one()
    
    if not offsite_id:
         raise ValueError("Offsite storage location not found.")

    for row in products:
        update_product_stage(
            db=db,
            product_id=row.product_id,
            new_stage_id=shipped_stage_id,
            reason="Shipment sent",
            user_id=user_id,
            location_id=offsite_id
        )
    
    db.commit()

@transactional
def mark_shipment_as_delivered(db: Session, shipment_id: int):
    db.execute(text(
        """
            UPDATE shipments
            SET status = 'Delivered',
                delivery_date = GETDATE(),
                updated_at = GETDATE()
            WHERE id = :sid
        """
    ), {"sid": shipment_id})

    db.commit()

@transactional
def cancel_order_request(db: Session, order_id: int, user_id: int, old_status: str, old_updated_by: int, old_updated_at: str, notes: str = ""):
    # === Prepare Audit Logs ===
    for field, old, new in [
        ("status", old_status, "Canceled"),
        ("updated_by", old_updated_by, user_id),
        ("updated_at", old_updated_at, datetime.now(timezone.utc))
    ]:
        audit = FieldChangeAudit(
            table="orders",
            record_id=order_id,
            field=field,
            old_value=old,
            new_value=new,
            reason="Order request canceled",
            changed_by=user_id
        )
        update_record_with_audit(db, audit, update=False)

    # === Perform actual update ===
    db.execute(text(
        """
            UPDATE orders
            SET 
                status = 'Canceled',
                updated_at = GETDATE(),
                updated_by = :user_id,
                notes = :notes
            WHERE id = :oid
        """
        ), 
            {
                "oid": order_id,
                "user_id": user_id,
                "notes": notes
            }
    )

    db.commit()