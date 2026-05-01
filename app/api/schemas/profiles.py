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


class BaseResponse(BaseModel):
    status: str = "success"


class ProfileResponseV1(BaseResponse):
    data: ProfileV1


class PaginatedResponseV1(BaseResponse):
    page: int
    limit: int
    total: int = 2026
    total_pages: int = 203
    links: dict
    data: list[ProfileV1]


class ProfileStatV1(BaseModel):
    total_profiles: int
    by_gender: dict[str, int]
    unique_countries: int


class ProfileExistV1(ProfileResponseV1):
    message: str = "Profile already exists"


class StatResponseV1(BaseResponse):
    data: ProfileStatV1
