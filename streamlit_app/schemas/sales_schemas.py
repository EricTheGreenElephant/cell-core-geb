from pydantic import BaseModel
from typing import Dict


class SalesOrderInput(BaseModel):
    customer_id: int
    created_by: int
    product_quantities: Dict[str, int]