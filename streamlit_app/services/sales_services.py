from datetime import datetime, timezone
from sqlalchemy import text, select
from sqlalchemy.orm import Session, selectinload
from schemas.sales_schemas import SalesOrderInput
from schemas.audit_schemas import FieldChangeAudit
from models.sales_models import Order, OrderItem, OrderSupplement
from models.production_models import ProductType, Supplement
from models.sales_catalogue_models import SalesCatalogue
from services.audit_services import update_record_with_audit
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

def get_active_sales_catalogue(db: Session) -> list[SalesCatalogue]:
    stmt = (
        select(SalesCatalogue)
        .options(
            selectinload(SalesCatalogue.products),
            selectinload(SalesCatalogue.supplements)
        )
        .where(SalesCatalogue.is_active == True)
        .order_by(SalesCatalogue.article_number)
    )
    return db.execute(stmt).scalars().all()

@transactional
def update_sales_order(db: Session, order_id: int, data: SalesOrderInput):
    order = db.query(Order).filter(Order.id == order_id).first()

    now = str(datetime.now(timezone.utc))
    updates = {}

    if order.notes != data.notes:
        updates["notes"] = (order.notes, data.notes)
        order.notes = data.notes

    if order.updated_by != data.updated_by:
        updates["updated_by"] = (order.updated_by, data.updated_by)
    
    if str(order.updated_at) != str(now):
        updates["updated_at"] = (str(order.updated_at, now))
        order.updated_at = now
    
    for field, (old, new) in updates.items():
        audit = FieldChangeAudit(
            table="orders",
            record_id=order_id,
            field=field,
            old_value=old,
            new_value=new,
            reason="Sales order updated",
            changed_by=data.updated_by
        )
        update_record_with_audit(db, audit)

    existing_items = {
        row.product_type_id: row
        for row in db.execute(select(OrderItem).where(OrderItem.order_id == order_id)).scalars()
    }

    for pid, new_qty in data.product_quantities.items():
        old_item = existing_items.get(pid)
        if old_item:
            if old_item.quantity != new_qty:
                update_record_with_audit(
                    db,
                    FieldChangeAudit(
                        table="order_items",
                        record_id=old_item.id,
                        field="quantity",
                        old_value=old_item.quantity,
                        new_value=new_qty,
                        reason="Sales order updated",
                        changed_by=data.updated_by
                    ),
                    update=True
                )
                old_item.quantity = new_qty
            else:
                item = OrderItem(order_id=order_id, product_type_id=pid, quantity=new_qty)
                db.add(item)
                db.flush()
                update_record_with_audit(
                    db,
                    FieldChangeAudit(
                        table="order_items",
                        record_id=item.id,
                        field="quantity",
                        old_value=None,
                        new_value=new_qty,
                        reason="Product item added to order",
                        changed_by=data.updated_by
                    ),
                    update=False
                )
    existing_supps = {
        row.supplement_id: row 
        for row in db.execute(select(OrderSupplement).where(OrderSupplement.order_id == order_id)).scalars()
    }

    for sid, new_qty in data.supplement_quantities.items():
        old_supp = existing_supps.get(sid)
        if old_supp:
            if old_supp.quantity != new_qty:
                update_record_with_audit(
                    db,
                    FieldChangeAudit(
                        table="order_supplements",
                        record_id=old_supp.id,
                        field="quantity",
                        old_value=old_supp.quantity,
                        new_value=new_qty,
                        reason="Sales order updated",
                        changed_by=data.updated_by
                    ),
                    update=True
                )
                old_supp.quantity = new_qty
        
        else:
            supp = OrderSupplement(order_id=order_id, supplement_id=sid, quantity=new_qty)
            db.add(supp)
            db.flush()
            update_record_with_audit(
                db,
                FieldChangeAudit(
                    table="order_supplements",
                    record_id=supp.id,
                    field="quantity",
                    old_value=None,
                    new_value=new_qty,
                    reason="Supplement item added to order",
                    changed_by=data.updated_by
                ),
                update=False
            )
    
    db.commit()

def _get_order_header_query() -> str:
    return """
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
        JOIN customers c ON o.customer_id = c.id

    """

def _get_product_items_query() -> str:
    return """
        SELECT
            oi.id,
            oi.product_type_id,
            pt.name AS product_type,
            oi.quantity
        FROM order_items oi
        JOIN product_types pt ON oi.product_type_id = pt.id
        WHERE oi.order_id = :oid
    """

def _get_supplements_query() -> str:
    return """
        SELECT
            os.id,
            os.supplement_id,
            s.name AS supplement_name,
            os.quantity
        FROM order_supplements os
        JOIN supplements s ON os.supplement_id = s.id
        WHERE os.order_id = :oid
    """

def get_processing_order_with_items(db: Session, order_id: int) -> dict | None: 
    header_query = _get_order_header_query() + " WHERE o.id = :oid AND o.status = 'Processing'"
    order_row = db.execute(text(header_query), {"oid": order_id}).mappings().first()

    if not order_row:
        return None
    
    product_items = db.execute(
        text(_get_product_items_query()), {"oid": order_id}
    ).mappings().all()

    supplements = db.execute(
        text(_get_supplements_query()), {"oid": order_id}
    ).mappings().all()

    return {
        **order_row,
        "product_items": list(product_items),
        "supplements": list(supplements)
    }

def get_product_type_names(db: Session) -> dict[int, str]:
    stmt = select(ProductType.id, ProductType.name).where(ProductType.is_active == True)
    result = db.execute(stmt).fetchall()
    return {id: name for id, name in result}

def get_supplement_names(db: Session) -> dict[int, str]:
    stmt = select(Supplement.id, Supplement.name).where(Supplement.is_active == True)
    result = db.execute(stmt).fetchall()
    return {id: name for id, name in result}