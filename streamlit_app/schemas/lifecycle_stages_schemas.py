from pydantic import BaseModel, ConfigDict


class LifecycleStagesRead(BaseModel):
    id: int
    stage_code: str
    stage_name: str
    stage_order: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)