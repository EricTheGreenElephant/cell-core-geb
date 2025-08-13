from sqlalchemy import text
from sqlalchemy.orm import Session


def get_label_data_by_product_id(db: Session, product_id: int):
    query = text(
        """
            SELECT
                pt.id,
                ptype.name AS product_type,
                ptype.average_weight AS volume,
                pr.lot_number,
                CONVERT(VARCHAR, DATEADD(year, 1, ph.print_date), 23) AS expiration_date,
                CONCAT('GEB-', UPPER(LEFT(ptype.name, 6)), '-', pt.id) AS reference_number
            FROM product_tracking pt
            JOIN product_harvest ph ON pt.harvest_id = ph.id
            JOIN product_requests pr ON ph.request_id = pr.id
            JOIN product_types ptype ON pr.product_id = ptype.id
            WHERE pt.id = :product_id
        """
    )

    result = db.execute(query, {"product_id": product_id}).mappings().first()

    if not result:
        return None
    
    return dict(result)