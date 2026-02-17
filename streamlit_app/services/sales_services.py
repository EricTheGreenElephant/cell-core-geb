import streamlit as st
from datetime import datetime, timezone
from sqlalchemy import text, select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError
from schemas.sales_schemas import SalesOrderInput
from schemas.audit_schemas import FieldChangeAudit
from models.sales_models import Order, OrderItem
from models.production_models import ProductType, ProductSKU
# from models.sales_catalogue_models import SalesCatalogue
from services.audit_services import update_record_with_audit
from utils.db_transaction import transactional


def get_active_skus(db: Session) -> list[dict]:
    sql = """
        SELECT id, sku, name, is_serialized, is_bundle, product_type_id
        FROM product_skus
        WHERE is_active = 1
        ORDER BY sku
    """
    rows = db.execute(text(sql)).fetchall()
    return [dict(r._mapping) for r in rows]

def get_sales_ready_qty_by_sku(db: Session) -> dict[int, int]:
    """
    Counts A-Ware units in QMSalesApproval for serialized SKUs.
    For bundles (is_bundle=1)
    """
    sql = """
        SELECT pr.sku_id AS sku_id, COUNT(*) AS qty
        FROM product_tracking t
        JOIN product_harvest ph ON t.harvest_id = ph.id
        JOIN product_requests pr ON ph.request_id = pr.id
        JOIN product_skus s ON pr.sku_id = s.id
        JOIN product_statuses ps ON t.current_status_id = ps.id
        JOIN lifecycle_stages ls ON t.current_stage_id = ls.id
        WHERE ls.stage_code IN ('QMSalesApproval', 'Internal Use/Client')
            AND ps.status_name IN ('A-Ware', 'B-Ware')
            AND ph.print_date >= DATEADD(year, -1, GETDATE())
        GROUP BY pr.sku_id
    """
    return {row.sku_id: row.qty for row in db.execute(text(sql)).fetchall()}

def get_sales_ready_inventory(db: Session):
    query = text(
        """
            SELECT 
                pt.id,
                psku.id AS sku_id,
                psku.sku,
                psku.name AS sku_name,
                pr.lot_number,
                ps.status_name AS product_status,
                ls.stage_name AS current_stage,
                pt.last_updated_at,
                u.display_name AS printed_by
            FROM product_tracking pt
            JOIN product_harvest ph ON pt.harvest_id = ph.id
            JOIN product_requests pr ON ph.request_id = pr.id
            JOIN product_skus psku ON psku.id = pt.sku_id
            JOIN users u ON ph.printed_by = u.id
            JOIN product_statuses ps ON pt.current_status_id = ps.id
            JOIN lifecycle_stages ls ON pt.current_stage_id = ls.id
            WHERE 
                ls.stage_code = 'QMSalesApproval'
                AND ps.status_name IN ('A-Ware', 'B-Ware')
                AND ph.print_date >= DATEADD(year, -1, GETDATE())
            ORDER BY pt.last_updated_at DESC
        """
    )
    result = db.execute(query).fetchall()
    return [dict(row._mapping) for row in result]

def customer_exists(db: Session, customer_name: str) -> bool:
    row = db.execute(
        text("SELECT 1 FROM customers WHERE customer_name = :name"),
        {"name": customer_name},
    ).first()
    return row is not None 

def create_customer(db: Session, customer_name: str) -> int:
    """
    Inserts a customer and returns the new customer's id.
    
    Raises:
        ValueError if duplicate
    """
    name = (customer_name or "").strip()
    if not name:
        raise ValueError("Customer name cannot be empty.")
    
    if customer_exists(db, name):
        raise ValueError("That customer already exists.")
    
    try:
        row = db.execute(
            text("""
                INSERT INTO customers (customer_name)
                OUTPUT INSERTED.id
                VALUES (:name)
            """),
            {"name": name},
        ).first()

        db.flush()

        return int(row[0]) if row else None

    except IntegrityError:
        raise ValueError("That customer already exists.")
    
def get_customers(db: Session):
    rows = db.execute(text("SELECT id, customer_name FROM customers ORDER BY customer_name")).fetchall()
    return [dict(row._mapping) for row in rows]

# def get_sales_ready_quantities_by_type(db: Session):
#     query = text(
#         """
#             SELECT
#                 pt.name AS product_type,
#                 COUNT(*) AS available_quantity
#             FROM product_tracking tr
#             JOIN product_harvest ph ON tr.harvest_id = ph.id
#             JOIN product_requests pr ON ph.request_id = pr.id
#             JOIN product_types pt ON pr.product_id = pt.id
#             JOIN product_statuses ps ON tr.current_status_id = ps.id
#             JOIN lifecycle_stages ls ON tr.current_stage_id = ls.id
#             WHERE
#                 ls.stage_code = 'QMSalesApproval'
#                 AND ps.status_name IN ('A-Ware')
#                 AND ph.print_date >= DATEADD(year, -1, GETDATE())
#             GROUP BY pt.name
#             ORDER BY pt.name
#         """
#     )
#     result = db.execute(query).fetchall()
#     return [dict(row._mapping) for row in result]

def get_orderable_product_types(db: Session) -> list[ProductType]:
    stmt = select(ProductType).where(ProductType.is_active == True).order_by(ProductType.name)
    return db.execute(stmt).scalars().all()

# def get_active_supplements(db: Session) -> list[dict]:
#     stmt = select(Supplement).where(Supplement.is_active == True).order_by(Supplement.name)
#     return db.execute(stmt).scalars().all()

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
    for sku_id, qty in data.sku_quantities.items():
        if qty > 0:
            db.add(OrderItem(order_id=order.id, product_sku_id=sku_id, quantity=qty))

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

    return {
        "product_items": [dict(r._mapping) for r in product_rows],
    }


@transactional
def update_sales_order(db: Session, order_id: int, data: SalesOrderInput):
    order = db.query(Order).filter(Order.id == order_id).first()

    now = str(datetime.now(timezone.utc))
    updates = {}

    if (order.notes or "") != (data.notes or ""):
        updates["notes"] = (order.notes, data.notes)
        order.notes = data.notes

    if order.updated_by != data.updated_by:
        updates["updated_by"] = (order.updated_by, data.updated_by)
    
    if str(order.updated_at) != str(now):
        updates["updated_at"] = (str(order.updated_at), now)
        order.updated_at = datetime.now(timezone.utc)
    
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
        row.product_sku_id: row
        for row in db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
    }

    for sku_id, new_qty in data.sku_quantities.items():
        if new_qty < 0: continue
        if sku_id in existing_items:
            item = existing_items[sku_id]
            if item.quantity != new_qty:
                update_record_with_audit(
                    db,
                    FieldChangeAudit(
                        table="order_items",
                        record_id=item.id,
                        field="quantity",
                        old_value=item.quantity,
                        new_value=new_qty,
                        reason="Sales order updated",
                        changed_by=data.updated_by
                    ),
                    update=True
                )
                item.quantity = new_qty
        else:
            if new_qty > 0:
                item = OrderItem(order_id=order_id, product_sku_id=sku_id, quantity=new_qty)
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

    for sku_id, item in list(existing_items.items()):
        if data.sku_quantities.get(sku_id, 0) == 0 and item.quantity != 0:
            update_record_with_audit(
                db,
                FieldChangeAudit(
                    table="order_items",
                    record_id=item.id,
                    field="Deleted",
                    old_value=item.quantity,
                    new_value='Yes',
                    reason="Removed from order",
                    changed_by=data.updated_by
                )
            )
            db.delete(item)

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

def _get_items_query() -> str:
    return """
        SELECT
            oi.id,
            oi.product_sku_id,
            s.sku,
            s.name AS sku_name,
            oi.quantity
        FROM order_items oi
        JOIN product_skus s ON oi.product_sku_id = s.id
        WHERE oi.order_id = :oid
    """

def get_processing_order_with_items(db: Session, order_id: int = None, all_orders: bool = False):
    base_query = _get_order_header_query()

    if all_orders:
        query = base_query + " WHERE o.status = 'Processing' ORDER BY o.order_date ASC"
        orders = db.execute(text(query)).mappings().all()
        results = []

        for order in orders:
            oid = order["order_id"]
            product_items = db.execute(text(_get_items_query()), {"oid": oid}).mappings().all()

            results.append({
                **order,
                "order_items": list(product_items),
            })
        return results
    
    elif order_id is not None:
        query = base_query + " WHERE o.id = :oid AND o.status = 'Processing'"
        order_row = db.execute(text(query), {"oid": order_id}).mappings().first()
        if not order_row:
            return None
        
        product_items = db.execute(text(_get_items_query()), {"oid": order_id}).mappings().all()

        return {
            **order_row,
            "order_items": list(product_items),
        }
    
    return None

# def build_catalogue_quantity_inputs(catalogues, mode: str) -> dict[int, int]:
#     """
#         Display catalogue packages in expandable panels and collect quantity inputs.

#         Returns a dict of {catalogue_id: quantity}
#     """
#     st.markdown("#### Select Catalogue Packages and Quantities")
#     package_quantities = {}

#     for cat in catalogues:
#         key = f"catalogue:{mode}:{cat.id}"

#         with st.expander(f"{cat.package_name} (${cat.price:.2f})"):
#             st.markdown(f"*{cat.package_desc}*")
#             qty = st.number_input(
#                 label="Quantity",
#                 min_value=0,
#                 step=1,
#                 value=st.session_state.get(key, 0),
#                 key=key
#             )
#             package_quantities[cat.id] = qty
    
#     return package_quantities

# def show_order_quantity_summary(product_quantities, supplement_quantities, product_lookup, supplement_lookup):
#     if not product_quantities and not supplement_quantities:
#         return
    
#     st.markdown("#### Summary of Order Quantities")

#     if product_quantities:
#         st.markdown("**Products:**")
#         for pid, qty in product_quantities.items():
#             name = product_lookup.get(pid, f"Unknown Product {pid}")
#             st.markdown(f"- {name}: {qty}")
    
#     if supplement_quantities:
#         st.markdown("**Supplements:**")
#         for sid, qty in supplement_quantities.items():
#             name = supplement_lookup.get(sid, f"Unknown Supplement {sid}")
#             st.markdown(f"- {name}: {qty}")

# def calculate_order_totals_from_catalogue(catalogues: list[SalesCatalogue], package_quantities: dict[int, int]) -> tuple[dict[int, int], dict[int, int]]:
#     """
#     Given cataloge packages and selected package quantities, returns total product
#     quantities and supplement quantities.

#     Returns:
#         - dict[product_type_id, total_quantity]
#         - dict[supplement_id, total_quantity]
#     """
#     product_quantities = defaultdict(int)
#     supplement_quantities = defaultdict(int)

#     for cat in catalogues:
#         count = package_quantities.get(cat.id, 0)
#         if count == 0:
#             continue

#         for p in cat.products:
#             product_quantities[p.product_id] += p.product_quantity * count
        
#         for s in cat.supplements:
#             supplement_quantities[s.supplement_id] += s.supplement_quantity * count
        
#     return dict(product_quantities), dict(supplement_quantities)
