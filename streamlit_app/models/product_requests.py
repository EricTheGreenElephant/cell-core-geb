from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ProductRequestModel(BaseModel):
    id: Optional[int]
    product_id: int
    quantity: int
    requested_by: int
    requested_at: Optional[datetime] = None
    status: str
    # lot_number: str
    notes: Optional[str] = None
    