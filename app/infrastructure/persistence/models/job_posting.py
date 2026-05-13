from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.constants.general import DB_SCHEMA
from app.infrastructure.config.database import Base


class JobPostingModel(Base):
    __tablename__ = "job_postings"
    __table_args__ = (
        UniqueConstraint(
            "external_id", "source",
            name="uq_job_posting_external_id_source",
        ),
        Index("ix_job_postings_source", "source"),
        Index("ix_job_postings_posted_at", "posted_at"),
        {"schema": DB_SCHEMA},
    )

    def __repr__(self) -> str:
        return (
            f"<JobPostingModel("
            f"id={self.id}, "
            f"title={self.title!r}, "
            f"company={self.company!r}, "
            f"source={self.source!r}"
            f")>"
        )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    external_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    company: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    location: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    url: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
    )

    apply_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )

    company_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )

    posted_at: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    is_remote: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    job_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    insights: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    salary_min: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    salary_max: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    salary_currency: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    skills_raw: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
