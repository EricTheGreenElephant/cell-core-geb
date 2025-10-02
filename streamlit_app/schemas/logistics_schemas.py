from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime


class TreatmentProductData(BaseModel):
    product_id: int
    surface_treat: bool
    sterilize: bool


class TreatmentBatchCreate(BaseModel):
    sent_by: int
    tracking_data: List[TreatmentProductData]
    notes: Optional[str] = None


class TreatmentBatchOut(BaseModel):
    id: int
    sent_by: int
    sent_at: datetime
    status: str
    notes: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class TreatmentBatchProductCandidate(BaseModel):
    product_id: int
    current_stage_name: str
    current_status: str
    last_updated_at: datetime
    harvest_id: int
    sku: str
    sku_name: str
    inspection_result: str
    location_name: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class PostHarvestStorageCandidate(BaseModel):
    product_id: int
    current_stage_name: str
    location_id: Optional[int]
    harvest_id: int
    last_updated_at: datetime
    inspection_result: str
    filament_serial: str
    sku: str
    sku_name: str
    printed_by: Optional[str]
    print_date: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class PostTreatmentStorageCandidate(BaseModel):
    product_id: int
    harvest_id: int
    sku: str
    sku_name: str
    inspection_result: Optional[str]


class AdHocQuarantineStorageCandidate(BaseModel):
    product_id: int
    quarantine_id: int
    current_stage_name: str
    last_updated_at: datetime
    sku: str
    sku_name: str
    quarantined_by: int
    quarantine_date: datetime
    inspection_result: str

    model_config = ConfigDict(from_attributes=True)