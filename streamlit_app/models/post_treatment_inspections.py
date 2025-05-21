from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Literal, Optional


class PostTreatmentQCModel(BaseModel):
    id: Optional[int]
    product_id: int
    inspected_by: int
    inspected_at: Optional[datetime] = None
    visual_pass: bool
    surface_treated: bool
    sterilized: bool
    qc_result: Literal["QM Request", "Internal Use", "Waste"]
    notes: Optional[str] = None
    