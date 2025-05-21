from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional, Literal


class FilamentBase(BaseModel):
    id: int
    serial_number: str
    weight_grams: float
    qc_result: str
    received_at: datetime
    received_by: Optional[str] = None
    location_name: Optional[str] = None


class FilamentInUse(FilamentBase):
    remaining_weight: Optional[float]
    printer_name: Optional[str]
    mounted_at: Optional[datetime]


class FilamentArchived(FilamentBase):
    remaining_weight: Optional[float]
    printer_name: Optional[str]
    mounted_at: Optional[datetime]
    unmounted_at: Optional[datetime]
    unmounted_by: Optional[str]


class FilamentMountCreate(BaseModel):
    filament_id: int
    printer_id: int
    mounted_by: int
    acclimatization_id: int


class FilamentCreate(BaseModel):
    serial_number: str
    weight_grams: float
    location_id: int
    qc_result: str
    received_by: int

    @field_validator("qc_result")
    @classmethod
    def validate_qc(cls, v):
        allowed = {"PASS", "FAIL"}
        if v not in allowed:
            raise ValueError("qc_result must be PASS or FAIL")
        return v
