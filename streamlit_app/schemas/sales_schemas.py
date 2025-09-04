from pydantic import BaseModel, ConfigDict
from typing import Dict, Optional


class SalesOrderInput(BaseModel):
    customer_id: int
    created_by: int
    updated_by: int
    sku_quantities: Dict[int, int]
    notes: str = ""
    parent_order_id: int | None = None


class OrderItemOut(BaseModel):
    id: int
    product_sku_id: int 
    quantity: int 

    model_config = ConfigDict(from_attributes=True)

    