from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class ProductRequestCreate(BaseModel):
    requested_by: int
    product_id: int
    quantity: int
    notes: Optional[str] = ""


class ProductRequestOut(BaseModel):
    id: int
    product_type: str
    requested_by: str
    lot_number: str
    status: str
    requested_at: datetime
    average_weight: int
    buffer_weight: int

    model_config = ConfigDict(from_attributes=True)


class SupplementCreate(BaseModel):
    name: str


class SupplementOut(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)

    
class HarvestedProductOut(BaseModel):
    harvest_id: int
    request_id: int
    product_type: str
    filament_serial: str
    printer_name: str
    lid_serial: str
    printed_by: str
    print_date: datetime
    

class ProductTrackingRead(BaseModel):
    id: int
    tracking_id: str
    current_status_id: Optional[int]
    current_status_name: Optional[str] = None
    harvest_id: int
    previous_stage_id: int
    current_stage_id: int
    last_updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductStatusHistoryEntry(BaseModel):
    id: int
    product_id: int
    from_stage_id: Optional[int]
    to_stage_id: int
    reason: Optional[str]
    changed_by: int
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True)