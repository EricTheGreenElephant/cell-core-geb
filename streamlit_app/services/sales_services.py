from sqlalchemy import text
from sqlalchemy.orm import Session
from schemas.sales_schemas import SalesOrderInput
from models.sales_models import Order, OrderItem
from models.production_models import ProductType
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
    return db.query(ProductType).order_by(ProductType.name).all()

@transactional
def create_sales_order(db: Session, data: SalesOrderInput):
    # === Create Order Object === 
    order = Order(
        customer_id=data.customer_id,
        order_creator_id=data.created_by,
        status="Processing"
    )
    db.add(order)
    db.flush()

    # === Get product_type ===
    types = db.query(ProductType).all()
    type_lookup = {t.name: t.id for t in types}

    # === Insert order_items
    for type_name, qty in data.product_quantities.items():
        if qty <= 0:
            continue
        type_id = type_lookup.get(type_name)
        if not type_id:
            raise ValueError(f"Invalid product type: {type_name}")
        
        item = OrderItem(
            order_id=order.id,
            product_type_id=type_id,
            quantity=qty
        )
        db.add(item)

    db.commit()