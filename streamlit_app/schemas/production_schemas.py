from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class ProductRequestCreate(BaseModel):
    requested_by: int
    sku_id: int
    quantity: int
    notes: Optional[str] = ""


class ProductRequestOut(BaseModel):
    id: int
    sku: str
    sku_name: str
    product_type: str
    requested_by: str
    lot_number: str
    status: str
    requested_at: datetime

    height_mm: Optional[float] = None
    diameter_mm: Optional[float] = None
    average_weight_g: Optional[float] = None
    weight_buffer_g: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)

    
class HarvestedProductOut(BaseModel):
    harvest_id: int
    request_id: int
    sku: str
    sku_name: str
    product_type: str
    filament_serial: str
    printer_name: str
    lid_serial: str
    seal_serial: str
    printed_by: str
    print_date: datetime
    

class ProductTrackingRead(BaseModel):
    id: int
    product_id: int
    product_code: Optional[str] = None
    sku_id: Optional[int] = None 
    sku: Optional[str] = None
    current_status_id: Optional[int]
    current_status_name: Optional[str] = None
    harvest_id: int
    previous_stage_id: Optional[int] = None
    current_stage_id: int
    last_updated_at: datetime
    location_name: Optional[str] = None
    product_type: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ProductStatusHistoryEntry(BaseModel):
    id: int
    product_tracking_id: int
    from_stage_id: Optional[int]
    to_stage_id: int
    reason: Optional[str]
    changed_by: int
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True)