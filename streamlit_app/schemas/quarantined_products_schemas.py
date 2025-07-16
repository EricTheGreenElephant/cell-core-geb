from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class QuarantinedProductBase(BaseModel):
    product_id: int
    from_stage_id: int
    source: str
    location_id: Optional[int] = None
    quarantine_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class QuarantinedProductCreate(QuarantinedProductBase):
    quarantined_by: int

    model_config = ConfigDict(from_attributes=True)


class QuarantinedProductUpdate(BaseModel):
    quarantine_status: str
    result: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class QuarantinedProductRead(QuarantinedProductBase):
    id: int
    quarantine_status: str
    quarantine_date: datetime
    quarantined_by: int
    result: Optional[str]
    resolved_at: Optional[datetime]
    resolved_by: Optional[int]

    model_config = ConfigDict(from_attributes=True)
