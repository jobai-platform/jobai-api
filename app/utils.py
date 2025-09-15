from datetime import timezone, UTC, datetime

from pydantic import BaseModel
from sqlalchemy import ForeignKey

from app.constants.general import DB_SCHEMA
from app.core.database import Base


def make_foreign_key(id_col: str, ref_table: str, db_schema: str = DB_SCHEMA) -> ForeignKey:
    return ForeignKey(f"{db_schema}.{ref_table}.{id_col}")


def set_orm_attributes(db_obj: Base, data: BaseModel, exclude_none: bool = True) -> None:
    for key, val in data.model_dump(exclude_none=exclude_none).items():
        if hasattr(db_obj, key):
            setattr(db_obj, key, val)


def timestamp_to_datetime(timestamp: float | None, tz: timezone = UTC) -> datetime | None:
    if timestamp is None:
        return

    return datetime.fromtimestamp(timestamp, tz=tz)
