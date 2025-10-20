from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ProductQCInput(BaseModel):
    product_tracking_id: int
    inspected_by: int
    weight_grams: float
    pressure_drop: float
    visual_pass: bool
    inspection_result: str
    notes: Optional[str] = None
    reason_ids: Optional[List[int]] = None
