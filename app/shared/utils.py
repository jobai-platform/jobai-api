from datetime import datetime
from typing import Any, Mapping

from sqlalchemy import ForeignKey


def make_foreign_key(
    referenced_column: str,
    referenced_table: str,
    *,
    nullable: bool = False,
    unique: bool = False,
) -> ForeignKey:
    """
    Create a SQLAlchemy ForeignKey definition pointing to "<table>.<column>".

    Note: SQLAlchemy's ForeignKey does not enforce nullable/unique; those belong to Column().
    We keep the parameters for backwards compatibility, but they are not applied here.
    """
    return ForeignKey(f"{referenced_table}.{referenced_column}")


def set_orm_attributes(instance: Any, attributes: Mapping[str, Any]) -> None:
    """Set multiple attributes on an ORM instance."""
    for attr_name, attr_value in attributes.items():
        setattr(instance, attr_name, attr_value)


def timestamp_to_datetime(timestamp: float) -> "datetime":
    """Convert a UNIX timestamp (seconds) to a datetime (local timezone)."""
    return datetime.fromtimestamp(timestamp)
