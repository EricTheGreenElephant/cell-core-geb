from pydantic import BaseModel, ConfigDict
from typing import List


class SalesCatalogueProductOut(BaseModel):
    product_tracking_id: int
    product_quantity: int

    model_config = ConfigDict(from_attributes=True)


class SalesCatalogueSupplementOut(BaseModel):
    supplement_id: int
    supplement_quantity: int

    model_config = ConfigDict(from_attributes=True)


class SalesCatalogueOut(BaseModel):
    id: int
    article_number: int
    package_name: str
    package_desc: str
    price: float
    products: List[SalesCatalogueProductOut]
    supplements: List[SalesCatalogueSupplementOut]

    model_config = ConfigDict(from_attributes=True)