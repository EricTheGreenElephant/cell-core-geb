from pydantic import BaseModel
from typing import Optional


class ProductQCInput(BaseModel):
    harvest_id: int
    inspected_by: int
    weight_grams: float
    pressure_drop: float
    visual_pass: bool
    inspection_result: str
    notes: Optional[str] = None