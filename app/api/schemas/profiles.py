from uuid import UUID
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict


class GenderEnum(str, Enum):
    MALE = "male"
    FEMALE = "female"


class AgeGroupEnum(str, Enum):
    CHILD = "child"         # 0-12
    ADULT = "adult"         # 13-19
    SENIOR = "senior"       # 20-59
    TEENAGER = "teenager"   # 60+


class ProfileCreate(BaseModel):
    name: Optional[str] = None

    model_config = ConfigDict(str_strip_whitespace=True)


class Profile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    gender: GenderEnum
    gender_probability: float
    sample_size: int
    age: int
    age_group: AgeGroupEnum
    country_id: str
    country_probability: float
    created_at: str


class ProfileResponse(BaseModel):
    status: str = "success"
    data: Profile | list[Profile]


class ProfileExist(ProfileResponse):
    message: str = "Profile already exists"
