from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ProfileV1(BaseModel):
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


class ProfileCreateV1(BaseModel):
    name: str = None


class ProfileResponseV1(BaseModel):
    status: str = "success"
    data: ProfileV1


class PaginatedResponseV1(BaseModel):
    status: str = "success"
    page: int
    limit: int
    total: int = 2026
    total_pages: int = 203
    links: dict
    data: list[ProfileV1]


class ProfileExistV1(ProfileResponseV1):
    message: str = "Profile already exists"
