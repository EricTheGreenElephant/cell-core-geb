from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime


class TreatmentProductData(BaseModel):
    tracking_id: int
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