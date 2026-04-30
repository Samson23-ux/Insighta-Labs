import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    UUID,
    Boolean,
    VARCHAR,
    DateTime,
    PrimaryKeyConstraint,
)


from app.database.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID)
    github_id: Mapped[str] = mapped_column(VARCHAR, unique=True)
    username: Mapped[str] = mapped_column(VARCHAR)
    email: Mapped[str] = mapped_column(VARCHAR, unique=True)
    avatar_url: Mapped[str] = mapped_column(VARCHAR)
    role: Mapped[str] = mapped_column(VARCHAR)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now(timezone.utc)
    )

    __table_args__ = (
        PrimaryKeyConstraint("id", name="users_id_pk"),
    )
