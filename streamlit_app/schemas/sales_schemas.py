from pydantic import BaseModel, ConfigDict
from typing import Dict


class SalesOrderInput(BaseModel):
    customer_id: int
    created_by: int
    updated_by: int
    product_quantities: Dict[int, int]
    supplement_quantities: Dict[int, int]
    notes: str = ""
    parent_order_id: int | None = None


class OrderSupplementInput(BaseModel):
    supplement_id: int
    quantity: int


class OrderSupplementOut(BaseModel):
    id: int
    supplement_id: int
    quantity: int

    model_config = ConfigDict(from_attributes=True)