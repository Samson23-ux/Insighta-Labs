import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    UUID,
    Index,
    Float,
    Integer,
    VARCHAR,
    DateTime,
    PrimaryKeyConstraint,
)


from app.database.base import Base


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID)
    name: Mapped[str] = mapped_column(VARCHAR, unique=True)
    gender: Mapped[str] = mapped_column(VARCHAR)
    gender_probability: Mapped[float] = mapped_column(Float)
    age: Mapped[int] = mapped_column(Integer)
    age_group: Mapped[str] = mapped_column(VARCHAR)
    country_id: Mapped[str] = mapped_column(VARCHAR(2))
    country_name: Mapped[str] = mapped_column(VARCHAR)
    country_probability: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now(timezone.utc)
    )

    __table_args__ = (
        PrimaryKeyConstraint("id", name="profiles_id_pk"),
        Index("idx_profiles_age", age),
        Index("idx_profiles_country_id", country_id),
        Index("idx_profiles_created_at", created_at),
        Index("idx_profiles_gender_probability", gender_probability),
        Index("idx_profiles_composite_1", country_id, age, gender),
        Index("idx_profiles_composite_2", country_id, age, age_group),
    )
