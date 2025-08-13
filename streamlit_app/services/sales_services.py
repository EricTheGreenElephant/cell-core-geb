from sqlalchemy import text, select
from sqlalchemy.orm import Session
from schemas.sales_schemas import SalesOrderInput
from models.sales_models import Order, OrderItem, OrderSupplement
from models.production_models import ProductType, Supplement
from utils.db_transaction import transactional


def get_sales_ready_inventory(db: Session):
    query = text(
        """
            SELECT 
                pt.id,
                ptype.name AS product_type,
                pr.lot_number,
                ps.status_name AS product_status,
                ls.stage_name AS current_stage,
                pt.last_updated_at,
                u.display_name AS printed_by
            FROM product_tracking pt
            JOIN product_harvest ph ON pt.harvest_id = ph.id
            JOIN product_requests pr ON ph.request_id = pr.id
            JOIN product_types ptype ON pr.product_id = ptype.id
            JOIN users u ON ph.printed_by = u.id
            JOIN product_statuses ps ON pt.current_status_id = ps.id
            JOIN lifecycle_stages ls ON pt.current_stage_id = ls.id
            WHERE 
                ls.stage_code = 'QMSalesApproval'
                AND ps.status_name IN ('A-Ware')
                AND ph.print_date >= DATEADD(year, -1, GETDATE())
            ORDER BY pt.last_updated_at DESC
        """
    )
    result = db.execute(query).fetchall()
    return [dict(row._mapping) for row in result]

def get_customers(db: Session):
    rows = db.execute(text("SELECT id, customer_name FROM customers ORDER BY customer_name")).fetchall()
    return [dict(row._mapping) for row in rows]

def get_sales_ready_quantities_by_type(db: Session):
    query = text(
        """
            SELECT
                pt.name AS product_type,
                COUNT(*) AS available_quantity
            FROM product_tracking tr
            JOIN product_harvest ph ON tr.harvest_id = ph.id
            JOIN product_requests pr ON ph.request_id = pr.id
            JOIN product_types pt ON pr.product_id = pt.id
            JOIN product_statuses ps ON tr.current_status_id = ps.id
            JOIN lifecycle_stages ls ON tr.current_stage_id = ls.id
            WHERE
                ls.stage_code = 'QMSalesApproval'
                AND ps.status_name IN ('A-Ware')
                AND ph.print_date >= DATEADD(year, -1, GETDATE())
            GROUP BY pt.name
            ORDER BY pt.name
        """
    )
    result = db.execute(query).fetchall()
    return [dict(row._mapping) for row in result]

def get_orderable_product_types(db: Session) -> list[ProductType]:
    stmt = select(ProductType).where(ProductType.is_active == True).order_by(ProductType.name)
    return db.execute(stmt).scalars().all()

def get_active_supplements(db: Session) -> list[dict]:
    stmt = select(Supplement).where(Supplement.is_active == True).order_by(Supplement.name)
    return db.execute(stmt).scalars().all()

@transactional
def create_sales_order(db: Session, data: SalesOrderInput):
    # === Create Order Object === 
    order = Order(
        customer_id=data.customer_id,
        parent_order_id=data.parent_order_id,
        order_creator_id=data.created_by,
        updated_by=data.updated_by,
        status="Processing",
        notes=data.notes
    )
    db.add(order)
    db.flush()

    # === Insert product items ===
    for product_type_id, qty in data.product_quantities.items():
        if qty > 0:
            db.add(OrderItem(order_id=order.id, product_type_id=product_type_id, quantity=qty))

    # === Insert supplements ===
    for supplement_id, qty in data.supplement_quantities.items():
        if qty > 0:
            db.add(OrderSupplement(order_id=order.id, supplement_id=supplement_id, quantity=qty))

    db.commit()

def get_canceled_order_headers(db: Session) -> list[dict]:
    rows = db.execute(text(
        """
            SELECT
                o.id AS order_id,
                o.customer_id,
                c.customer_name,
                o.order_date,
                o.notes
            FROM orders o 
            JOIN customers c ON o.customer_id = c.id
            WHERE 
                o.status = 'Canceled'
                AND NOT EXISTS (
                    SELECT 1
                    FROM orders child
                    WHERE child.parent_order_id = o.id
                )
            ORDER BY o.order_date DESC
        """
    )).fetchall()
    return [dict(r._mapping) for r in rows]

def get_canceled_orders_with_items(db: Session, order_id: int) -> dict:
    product_rows = db.execute(text(
        """
            SELECT
                oi.product_type_id,
                pt.name AS product_type,
                oi.quantity
            FROM order_items oi
            JOIN product_types pt ON oi.product_type_id = pt.id
            WHERE oi.order_id = :order_id
        """
    ), {"order_id": order_id}).fetchall()

    supplement_rows = db.execute(text(
        """
            SELECT
                os.supplement_id,
                s.name AS supplement_name,
                os.quantity
            FROM order_supplements os
            JOIN supplements s ON os.supplement_id = s.id
            WHERE os.order_id = :order_id
        """
    ), {"order_id": order_id}).fetchall()


    return {
        "product_items": [dict(r._mapping) for r in product_rows],
        "supplements": [dict(r._mapping) for r in supplement_rows]
    }
