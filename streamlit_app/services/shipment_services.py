from sqlalchemy import text, bindparam
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from schemas.audit_schemas import FieldChangeAudit
from services.audit_services import update_record_with_audit
from services.tracking_service import update_product_stage
from models.shipment_models import Shipment, ShipmentItem
from models.sales_models import Order
from utils.db_transaction import transactional


def get_open_order_headers(db: Session) -> list[dict]:
    result = db.execute(text(
        """
            SELECT
                o.id AS order_id,
                c.customer_name,
                o.order_date,
                o.notes,
                o.parent_order_id,
                o.status,
                o.updated_at,
                o.updated_by,
                o.customer_id
            FROM orders o
            JOIN customers c On o.customer_id = c.id
            WHERE o.status = 'Processing'
            ORDER BY o.order_date ASC
        """
    )).fetchall()
    return [dict(r._mapping) for r in result]

def get_open_orders_with_items(db: Session, order_id: int) -> dict:
    product_items = db.execute(text(
        """
            SELECT pt.name AS product_type, oi.quantity
            FROM order_items oi
            JOIN product_types pt ON oi.product_type_id = pt.id
            WHERE oi.order_id = :oid
        """
    ), {"oid": order_id}).fetchall()

    supplements = db.execute(text(
        """
            SELECT s.name AS supplement_name, os.quantity
            FROM order_supplements os
            JOIN supplements s ON os.supplement_id = s.id
            WHERE os.order_id = :oid
        """
    ), {"oid": order_id}).fetchall()

    return {
        "items": [dict(row._mapping) for row in product_items],
        "supplements": [dict(row._mapping) for row in supplements]
    }

def get_fifo_inventory_by_type(db: Session, product_type_name: str, limit: int):
    result = db.execute(text(
        """
            SELECT
                pt.id AS product_id,
                pt.tracking_id,
                ph.print_date,
                pt.last_updated_at
            FROM product_tracking pt
            JOIN product_harvest ph ON pt.harvest_id = ph.id
            JOIN product_requests pr ON ph.request_id = pr.id
            JOIN product_types ptype ON pr.product_id = ptype.id
            JOIN product_statuses ps ON pt.current_status_id = ps.id
            JOIN lifecycle_stages ls ON pt.current_stage_id = ls.id
            WHERE
                ptype.name = :ptype
                AND ls.stage_code = 'QMSalesApproval'
                AND ps.status_name = 'A-Ware'
                AND ph.print_date >= DATEADD(year, -1, GETDATE())
            ORDER BY ph.print_date ASC
            OFFSET 0 ROWS FETCH NEXT :limit ROWS ONLY
        """
    ), {"ptype": product_type_name, "limit": limit}).fetchall()

    return [dict(row._mapping) for row in result]

@transactional
def create_shipment_from_order(
    db: Session,
    *,
    order_id: int,
    customer_id: int,
    creator_id: int,
    selected_products_by_type: dict[str, list[dict]],
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

    for product_list in selected_products_by_type.values():
        for product in product_list:
            item = ShipmentItem(
                shipment_id=shipment.id,
                product_id=product["product_id"],
                quantity=1
            )
            db.add(item)

            update_product_stage(
                db=db,
                product_id=product["product_id"],
                new_stage_id=pending_shipment_stage_id,
                reason="Marked for Shipment",
                user_id=creator_id
            )

    # === Fetch Order ===
    order = db.query(Order).filter(Order.id == order_id).first()

    # === Update Audit Logs ===
    now_str = str(datetime.now(timezone.utc))

    fields_to_audit = [
        ("status", order.status, "Completed"),
        ("updated_by", order.updated_by, updated_by),
        ("updated_at", str(order.updated_at), now_str)
    ]

    for field, old, new in fields_to_audit:
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
    result = db.execute(text(
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

    return [dict(row._mapping) for row in result]

def get_products_in_shipments(db: Session, shipment_id: int):
    result = db.execute(text(
        """
            SELECT
                pt.id AS product_id,
                pt.tracking_id,
                ptype.name AS product_type,
                ph.print_date
            FROM shipment_items si
            JOIN product_tracking pt ON si.product_id = pt.id
            JOIN product_harvest ph ON pt.harvest_id = ph.id
            JOIN product_requests pr ON ph.request_id = pr.id
            JOIN product_types ptype ON pr.product_id = ptype.id
            WHERE si.shipment_id = :sid
            ORDER BY ph.print_date
        """
    ), {"sid": shipment_id}).fetchall()

    return [dict(row._mapping) for row in result]

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

    products = db.execute(text("SELECT product_id FROM shipment_items WHERE shipment_id = :sid"),
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
    fields_to_update = [
        ("status", old_status, "Canceled"),
        ("updated_by", old_updated_by, user_id),
        ("updated_at", old_updated_at, datetime.now(timezone.utc))
    ]

    for field, old_value, new_value in fields_to_update:
        audit = FieldChangeAudit(
            table="orders",
            record_id=order_id,
            field=field,
            old_value=old_value,
            new_value=new_value,
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