from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class Profile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    gender: str
    gender_probability: float
    age: int
    age_group: str
    country_id: str
    country_name: str
    country_probability: float
    created_at: datetime


class ProfileResponse(BaseModel):
    status: str = "success"
    page: int
    limit: int
    total: int
    data: list[Profile]
