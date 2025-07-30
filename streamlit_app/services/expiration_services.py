from sqlalchemy import text
from sqlalchemy.orm import Session


def get_expiring_products(db: Session):
    # Products within 7 days of expiry, but not over a year old
    expiring_soon = db.execute(text(
        """
            SELECT pt.id, ph.print_date, ptype.name AS product_type
            FROM product_tracking pt
            JOIN product_harvest ph ON pt.harvest_id = ph.id
            JOIN product_requests pr ON ph.request_id = pr.id
            JOIN product_types ptype ON pr.product_id = ptype.id
            JOIN lifecycle_stages ls ON pt.current_stage_id = ls.id
            WHERE
                ls.stage_code != 'Expired'
                AND ph.print_date < DATEADD(DAY, -358 , GETDATE())
                AND ph.print_date >= DATEADD(YEAR, -1, GETDATE())
        """
    )).fetchall()

    # Products that are over 1 year old, not already expired
    expired = db.execute(text(
        """
            SELECT pt.id, ph.print_date, ptype.name AS product_type
            FROM product_tracking pt
            JOIN product_harvest ph ON pt.harvest_id = ph.id
            JOIN product_requests pr ON ph.request_id = pr.id
            JOIN product_types ptype ON pr.product_id = ptype.id
            JOIN lifecycle_stages ls ON pt.current_stage_id = ls.id
            WHERE 
                ls.stage_code != 'Expired'
                AND ph.print_date < DATEADD(YEAR, -1, GETDATE())
        """
    )).fetchall()

    return (
        [dict(r._mapping) for r in expiring_soon],
        [dict(r._mapping) for r in expired]
    )

def expire_eligible_products(db: Session, user_id: int) -> int:
    # Get stage ID for 'Expired'
    expired_stage_id = db.scalar(text(
        """
            SELECT id FROM lifecycle_stages WHERE stage_code = 'Expired'
        """
    ))
    # Get eligible product IDs
    product_ids = db.execute(text(
        """
            SELECT pt.id
            FROM product_tracking pt
            JOIN product_harvest ph ON pt.harvest_id = ph.id
            JOIN lifecycle_stages ls ON pt.current_stage_id = ls.id
            WHERE 
                ls.stage_code != 'Expired'
                AND ph.print_date < DATEADD(YEAR, -1, GETDATE())
        """
    )).scalars().all()

    if not product_ids:
        return 0
    
    # Update products' current_stage_id
    db.execute(text(
        """
            UDPATE product_tracking
            SET current_stage_id = :stage
            WHERE id IN :ids
        """
    ), {"stagee": expired_stage_id, "ids": tuple(product_ids)})

    # Insert into product_stages_history
    db.execute(text(
        """
            INSERT INTO product_status_history (product_id, from_stage_id, to_stage_id, reason, changed_by)
            SELECT pt.id, pt.current_stage_id, :to_stage, 'Auto-expired after 1 year', :user
            FROM product_tracking pt
            JOIN lifecycle_stages ls ON pt.current_stage_id = ls.id
            WHERE pt.id IN :ids
        """
    ), {"to_stage": expired_stage_id, "user": user_id, "ids": tuple(product_ids)})

    db.commit()
    return len(product_ids)