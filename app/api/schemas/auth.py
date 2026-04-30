import enum
from uuid import UUID
from pydantic import BaseModel, Field


class TokenStatusV1(str, enum.Enum):
    VALID: str = "valid"
    REVOKED: str = "revoked"
    USED: str = "used"


class TokenDataV1(BaseModel):
    id: UUID


class AccessTokenCreateV1(BaseModel):
    refresh_token: str = Field(
        ..., description="A valid refresh token that is currently being used"
    )


class TokenResponseV1(BaseModel):
    status: str = "success"
    access_token: str
    refresh_token: str


class LogoutResponseV1(BaseModel):
    status: str = "success"
    message: str
