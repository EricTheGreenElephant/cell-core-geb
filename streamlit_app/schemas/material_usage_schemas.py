from pydantic import BaseModel, ConfigDict
from datetime import datetime


class MaterialUsageCreate(BaseModel):
    product_id: int
    harvest_id: int 
    material_type: str
    lot_number: str
    used_quantity: float
    used_by: int
    reason: str | None = None
    
    model_config = ConfigDict(from_attributes=True)


class MaterialUsageRead(BaseModel):
    id: int 
    product_id: int
    harvest_id: int
    material_type: str
    lot_number: str
    used_quantity: float
    used_at: datetime
    used_by: int
    reason: str
    
    model_config = ConfigDict(from_attributes=True)
