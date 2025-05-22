from pydantic import BaseModel, ConfigDict

class UserOut(BaseModel):
    id: int
    display_name: str

    model_config = ConfigDict(from_attributes=True)
