from pydantic import BaseModel, ConfigDict
from datetime import datetime 
from typing import Optional, List


class ShipmentCreate(BaseModel):
    customer_id: int 
    order_id: Optional[int] = None 
    notes: str = ""


class ShipmentUnitItemOut(BaseModel):
    id: int 
    product_id: int
    tracking_id: Optional[str] = None 
    model_config = ConfigDict(from_attributes=True)


class ShipmentSKUItemOut(BaseModel):
    id: int 
    product_sku_id: int 
    quantity: int 
    sku: Optional[str] = None 
    model_config = ConfigDict(from_attributes=True)


class ShipmentOut(BaseModel):
    id: int 
    customer_id: int 
    order_id: Optional[int] 
    status: str
    created_date: datetime 
    ship_date: Optional[datetime]
    delivery_date: Optional[datetime]
    tracking_number: Optional[str]
    carrier: Optional[str]
    notes: Optional[str]
    unit_items: List[ShipmentUnitItemOut] = []
    sku_items: List[ShipmentSKUItemOut] = []
    model_config = ConfigDict(from_attributes=True)