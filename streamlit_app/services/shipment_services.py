from sqlalchemy import text
from sqlalchemy.orm import Session
from services.tracking_service import update_product_stage
from models.shipment_models import Shipment, ShipmentItem
from models.sales_models import Order
from utils.db_transaction import transactional


def get_open_orders_with_items(db: Session):
    result = db.execute(text(
        """
            SELECT
                o.id AS order_id,
                o.customer_id,
                c.customer_name,
                o.order_date,
                pt.name AS product_type,
                oi.quantity
            FROM orders o 
            JOIN customers c ON o.customer_id = c.id
            JOIN order_items oi ON o.id = oi.order_id
            JOIN product_types pt ON oi.product_type_id = pt.id
            WHERE o.status = 'Processing'
            ORDER BY o.order_date ASC
        """
    )).fetchall()

    orders = {}
    for row in result:
        oid = row.order_id
        if oid not in orders:
            orders[oid] = {
                "customer_id": row.customer_id,
                "customer": row.customer_name,
                "order_date": row.order_date,
                "items": []
            }
        orders[oid]["items"].append({
            "product_type": row.product_type,
            "quantity": row.quantity
        })

    return orders

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
    selected_products_by_type: dict[str, list[dict]]
):
    shipment = Shipment(
        order_id=order_id,
        customer_id=customer_id,
        creator_id=creator_id,
        status="Pending"
    )
    db.add(shipment)
    db.flush()

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

    order = db.query(Order).filter(Order.id == order_id).first()
    order.status = "Completed"

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
                s.delivery_date
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
def mark_shipment_as_shipped(db: Session, shipment_id: int, user_id: int):
    db.execute(text(
        """
            UPDATE shipments
            SET status = 'Shipped',
                ship_date = GETDATE(),
                updated_at = GETDATE()
            WHERE id = :sid
        """
    ), {"sid": shipment_id})

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