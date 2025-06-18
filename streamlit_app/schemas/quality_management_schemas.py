from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ProductQMReview(BaseModel):
    tracking_id: int
    current_stage_name: str
    last_updated_at: datetime
    harvest_id: int
    lot_number: str
    product_type_name: str
    inspection_result: str
    inspected_by: str
    weight_grams: float
    pressure_drop: float
    visual_pass: bool
    current_location: Optional[str]
    qc_notes: Optional[str]

    class Config:
        orm_mode = True

class PostTreatmentApprovalCandidate(BaseModel):
    tracking_id: int
    harvest_id: int
    product_type_name: str
    inspection_result: Optional[str]
    inspected_by: str
    visual_pass: Optional[bool]
    surface_treated: Optional[bool]
    sterilized: Optional[bool]
    current_stage_name: str
    current_location: Optional[str]
    last_updated_at: datetime