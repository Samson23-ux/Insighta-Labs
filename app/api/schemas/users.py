from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class UserV1(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    github_id: str
    username: str
    email: str
    avatar_url: str
    role: str
    is_active: bool
    last_login_at: datetime
    created_at: datetime


class UserResponseV1(BaseModel):
    status: str = "success"
    data: UserV1
