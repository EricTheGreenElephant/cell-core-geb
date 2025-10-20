from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional


class ProductQMReview(BaseModel):
    product_tracking_id: int
    current_stage_name: str
    last_updated_at: datetime
    lot_number: str
    sku: str
    sku_name: str
    inspection_result: str
    inspected_by: str
    weight_grams: float
    pressure_drop: float
    visual_pass: bool
    current_location: Optional[str]
    qc_notes: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class PostTreatmentApprovalCandidate(BaseModel):
    product_tracking_id: int
    sku: str
    sku_name: str
    inspection_result: Optional[str]
    inspected_by: str
    visual_pass: Optional[bool]
    surface_treated: Optional[bool]
    sterilized: Optional[bool]
    current_stage_name: str
    current_location: Optional[str]
    last_updated_at: datetime


class QuarantinedProductRow(BaseModel):
    product_tracking_id: int
    tracking_id: str
    sku: str
    sku_name: str
    previous_stage_name: Optional[str]
    current_stage_name: str
    location_name: Optional[str]
    inspection_result: Optional[str]
    quarantine_date: datetime
    quarantine_reason: Optional[str]
    quarantined_by: str
    qc_result: Optional[str]
    weight_grams: Optional[float]
    pressure_drop: Optional[float]
    last_updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class InvestigationEntry(BaseModel):
    product_tracking_id: int
    status: str = Field(default="Under Investigation")
    comment: str = Field(..., max_length=255)
    deviation_number: str = Field(..., max_length=100)
    created_by: int
    created_at: datetime = Field(default_factory=datetime.now)


class InvestigatedProductRow(BaseModel):
    product_tracking_id: int
    sku: str
    sku_name: str
    previous_stage_name: str
    current_stage_name: str
    last_updated_at: datetime
    location_name: Optional[str]
    inspection_result: Optional[str]
    deviation_number: str
    comment: str
    created_by: str
    created_at: datetime


class ProductQuarantineSearchResult(BaseModel):
    product_tracking_id: int
    tracking_id: str
    sku: str
    sku_name: str
    lot_number: Optional[str]
    current_stage_name: str
    current_status: Optional[str]
    location_name: Optional[str]
    last_updated_at: datetime

    model_config = ConfigDict(from_attributes=True)