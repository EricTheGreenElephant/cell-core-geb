from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ProductQMReview(BaseModel):
    product_id: int
    current_stage_name: str
    last_updated_at: datetime
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
    product_id: int
    product_type_name: str
    inspection_result: Optional[str]
    inspected_by: str
    visual_pass: Optional[bool]
    surface_treated: Optional[bool]
    sterilized: Optional[bool]
    current_stage_name: str
    current_location: Optional[str]
    last_updated_at: datetime


class QuarantinedProductRow(BaseModel):
    product_id: int
    harvest_id: int
    product_type: str
    previous_stage_name: Optional[str]
    current_stage_name: str
    location_name: Optional[str]
    inspection_result: Optional[str]
    qc_result: Optional[str]
    weight_grams: Optional[float]
    pressure_drop: Optional[float]
    last_updated_at: datetime


class InvestigationEntry(BaseModel):
    product_id: int
    status: str = Field(default="Under Investigation")
    comment: str = Field(..., max_length=255)
    deviation_number: str = Field(..., max_length=100)
    created_by: int
    created_at: datetime = Field(default_factory=datetime.now)


class InvestigatedProductRow(BaseModel):
    product_id: int
    product_type: str
    previous_stage_name: str
    current_stage_name: str
    last_updated_at: datetime
    location_name: Optional[str]
    inspection_result: Optional[str]
    deviation_number: str
    comment: str
    created_by: str
    created_at: datetime