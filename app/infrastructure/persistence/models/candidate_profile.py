import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql.functions import func

from app.constants.general import DB_SCHEMA
from app.infrastructure.config.database import Base


class CandidateProfileModel(Base):
    __tablename__ = "candidate_profiles"
    __table_args__ = {"schema": DB_SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(f"{DB_SCHEMA}.users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    current_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    years_of_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    skills: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    desired_salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    desired_salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    preferred_locations: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    remote_preference: Mapped[str] = mapped_column(String(16), nullable=False, default="any")
    bio: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    cv_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
