import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, UniqueConstraint, Boolean
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.functions import func

from old.app.constants.general import DB_SCHEMA
from old.app.constants.users import TABLE_NAME, ID_COL
from old.app.core.database import Base
from old.app.utils.utils import make_foreign_key


class Users(Base):
    __tablename__ = TABLE_NAME
    __table_args__ = (
        UniqueConstraint("email", name="uq_user_email"),
        {"schema": DB_SCHEMA}
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(80), nullable=True, unique=True)

    first_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(80), nullable=True)

    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    stripe_customer_id: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)

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

fk_user = make_foreign_key(ID_COL, TABLE_NAME)
blacklist_tokens = set()
