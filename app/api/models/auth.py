import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    UUID,
    Text,
    Enum,
    Index,
    DateTime,
    ForeignKey,
    PrimaryKeyConstraint,
)

from app.database.base import Base
from app.api.schemas.auth import TokenStatusV1


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID)
    token: Mapped[str] = mapped_column(Text)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("users.id", name="tokens_user_id_fk", ondelete="CASCADE"),
    )
    status: Mapped[TokenStatusV1] = mapped_column(
        Enum(TokenStatusV1), default=TokenStatusV1.VALID
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now(timezone.utc)
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        PrimaryKeyConstraint("id", name="refresh_tokens_pk"),
        Index("idx_auth_user_id", user_id),
    )
