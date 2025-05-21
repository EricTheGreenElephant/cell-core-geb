from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TreatmentBatchModel(BaseModel):
    id: Optional[int]
    sent_by: int
    sent_at: Optional[datetime] = None
    status: str
    notes: Optional[str] = None