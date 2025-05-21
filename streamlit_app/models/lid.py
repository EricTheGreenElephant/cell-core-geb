from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, Literal


class LidModel(BaseModel):
    id: Optional[int]
    serial_number: str
    location_id: int
    received_by: int
    qc_result: Literal["PASS", "FAIL"]
    received_at: Optional[datetime] = None

    