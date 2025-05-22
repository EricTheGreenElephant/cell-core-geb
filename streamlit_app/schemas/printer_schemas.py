from pydantic import BaseModel, ConfigDict

class PrinterOut(BaseModel):
    id: int
    name: str
    status: str

    model_config = ConfigDict(from_attributes=True)
