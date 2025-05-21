from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ProductTrackingModel(BaseModel):
    id: Optional[int]
    harvest_id: int
    current_status: str
    location_id: Optional[int] = None
    last_updated_at: Optional[datetime] = None
    