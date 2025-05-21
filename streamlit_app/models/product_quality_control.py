from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime


class ProductQualityControlModel(BaseModel):
    id: Optional[int]
    harvest_id: int
    inspected_by: int
    inspected_at: Optional[datetime] = None
    weight_grams: float
    pressure_drop: float
    visual_pass: bool
    inspection_result: Literal["Passed", "B-Ware", "Waste", "Quarantine"]
    notes: Optional[str] = None