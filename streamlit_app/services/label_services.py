from sqlalchemy import text
from sqlalchemy.orm import Session


def get_label_data_by_product_id(db: Session, product_id: int):
    query = text(
        """
            SELECT
                pt.id,
                pt.product_id,
                ps.sku AS reference_number,
                ptype.name AS product_type,
                pps.average_weight_g AS volume,
                pr.lot_number,
                CONVERT(VARCHAR, DATEADD(year, 1, ph.print_date), 23) AS expiration_date
            FROM product_tracking pt
            JOIN product_types ptype ON pt.product_type_id = ptype.id
            JOIN product_skus ps ON pt.sku_id = ps.id
            JOIN product_print_specs pps ON ps.id = pps.sku_id
            JOIN product_harvest ph ON pt.harvest_id = ph.id
            JOIN product_requests pr ON ph.request_id = pr.id
            WHERE pt.product_id = :product_id
        """
    )

    result = db.execute(query, {"product_id": product_id}).mappings().first()

    if not result:
        return None
    
    return dict(result)