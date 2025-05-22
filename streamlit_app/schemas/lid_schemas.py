from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class LidCreate(BaseModel):
    serial_number: str
    location_id: int
    qc_result: str
    received_by: int


class LidOut(BaseModel):
    id: int
    serial_number: str
    location_id: int
    qc_result: str
    received_by: int
    received_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True) 