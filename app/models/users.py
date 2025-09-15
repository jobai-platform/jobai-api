import uuid
from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.functions import func

from ..constants.general import DB_SCHEMA
from ..constants.users import TABLE_NAME, ID_COL
from ..core.database import Base
from ..utils import make_foreign_key


class Users(Base):
    __tablename__ = TABLE_NAME
    __table_args__ = {"schema": DB_SCHEMA}

    id = Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Mapped[str] = mapped_column(nullable=False, unique=True)
    hashed_password = Mapped[str] = mapped_column(nullable=True)
    full_name = Mapped[str] = mapped_column(nullable=True)
    role = Mapped[str] = mapped_column(nullable=False, default="user")
    is_active = Mapped[str] = mapped_column(nullable=False, default=True)
    is_superuser = Mapped[str] = mapped_column(nullable=False, default=False)
    stripe_customer_id = Mapped[str] = mapped_column(nullable=True, unique=True)

    created_at = Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        server_onupdate=func.now(),
    )

fk_user = make_foreign_key(ID_COL, TABLE_NAME)
