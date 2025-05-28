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


class FilamentAcclimatizationOut(BaseModel):
    id: int
    filament_id: int
    status: str
    moved_at: datetime
    moved_by: int
    ready_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
