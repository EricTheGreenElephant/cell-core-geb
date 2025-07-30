from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class SealCreate(BaseModel):
    serial_number: str
    quantity: int
    location_id: int
    qc_result: str
    received_by: int


class SealOut(BaseModel):
    id: int
    serial_number: str
    quantity: int
    location_id: int
    qc_result: str
    received_by: int
    received_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True) 