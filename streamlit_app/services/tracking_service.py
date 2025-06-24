from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session
from models.production_models import ProductTracking
from utils.db_transaction import transactional


def generate_tracking_id(db: Session, date=None) -> str:
    if not date:
        date = datetime.today()
    
    prefix = date.strftime("PRD-%Y%d%m")

    count = db.query(ProductTracking).filter(
        ProductTracking.tracking_id.like(f"{prefix}-%")
    ).count()

    return f"{prefix}-{count + 1:05d}"

def log_product_status_change(db: Session, product_id: int, from_stage_id: int, to_stage_id: int, reason: str, user_id: int):
    db.execute(
        text("""
            INSERT INTO product_status_history
                (product_id, from_stage_id, to_stage_id, reason, changed_by, changed_at)
            VALUES
                (:product_id, :from_stage_id, :to_stage_id, :reason, :user_id, GETDATE())
        """),
        {
            "product_id": product_id,
            "from_stage_id": from_stage_id,
            "to_stage_id": to_stage_id,
            "reason": reason, 
            "user_id": user_id
        }
    )