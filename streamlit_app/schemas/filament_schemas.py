from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class FilamentCreate(BaseModel):
    serial_number: str
    weight_grams: float
    location_id: int
    qc_result: str
    received_by: int


class FilamentOut(BaseModel):
    id: int
    serial_number: str
    weight_grams: float
    qc_result: Optional[str]
    received_at: Optional[datetime]
    received_by: Optional[int]
    location_id: Optional[int]

    model_config = ConfigDict(from_attributes=True)


class FilamentMountOut(BaseModel):
    id: int
    filament_id: int
    printer_id: int
    mounted_by: int
    remaining_weight: float
    mounted_at: datetime
    unmounted_at: Optional[datetime] = None
    unmounted_by: Optional[int] = None
    status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class FilamentAcclimatizationOut(BaseModel):
    id: int
    filament_id: int
    status: str
    moved_at: datetime
    moved_by: int
    ready_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
