import enum
from uuid import UUID
from pydantic import BaseModel


class TokenStatusV1(str, enum.Enum):
    VALID: str = "valid"
    REVOKED: str = "revoked"
    USED: str = "used"


class TokenDataV1(BaseModel):
    id: UUID


class TokenResponseV1(BaseModel):
    status: str = "success"
    access_token: str
    refresh_token: str
