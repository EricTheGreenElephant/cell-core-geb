from pydantic import BaseModel
from typing import Optional


class TreatmentBatchProductModel(BaseModel):
    id: Optional[int]
    batch_id: int
    product_id: int
    surface_treat: bool = True
    sterilize: bool = True