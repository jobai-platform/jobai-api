import uuid
from datetime import datetime

from sqlalchemy import UniqueConstraint, String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql.functions import func

from app.constants.general import DB_SCHEMA
from app.constants.users import TABLE_NAME, ID_COL
from app.infrastructure.config.database import Base
from app.shared.utils import make_foreign_key


class UserModel(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_user_email"),
        {"schema": DB_SCHEMA},
    )

    def __repr__(self) -> str:
        return f"<UserModel(id={self.id}, email={self.email}, role={self.role})>"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )

    username: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
        unique=True,
    )

    first_name: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    last_name: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    hashed_password: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="user",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        unique=True,
    )

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

    # OAuth social fields
    linkedin_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        unique=True,
        index=True,
    )

    avatar_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    # Soft delete fields
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    scheduled_purge_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    # fk_user = make_foreign_key(ID_COL, TABLE_NAME)

    # Auth: token blacklist
    blacklist_tokens: set = set()
    # NOTE: fk_user has deleted - make_foreign_key() return ForeignKey orpheline, so we manage the relationship manually in the repository layer when needed.

