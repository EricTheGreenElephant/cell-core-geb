from datetime import datetime
from sqlalchemy.orm import Session
from models.production_models import ProductTracking


def generate_tracking_id(db: Session, date=None) -> str:
    if not date:
        date = datetime.today()
    
    prefix = date.strftime("PRD-%Y%d%m")

    count = db.query(ProductTracking).filter(
        ProductTracking.tracking_id.like(f"{prefix}-%")
    ).count()

    return f"{prefix}-{count + 1:05d}"