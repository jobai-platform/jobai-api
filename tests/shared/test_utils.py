from sqlalchemy import ForeignKey

from app.shared.utils import make_foreign_key, set_orm_attributes, timestamp_to_datetime


def test_make_foreign_key_returns_foreign_key() -> None:
    fk = make_foreign_key("id", "users")
    assert isinstance(fk, ForeignKey)
    # The referenced target should be visible in the internal repr/string form
    assert "users.id" in str(fk)


def test_set_orm_attributes_sets_multiple_fields() -> None:
    class Dummy:
        def __init__(self) -> None:
            self.a = 0
            self.b = ""

    obj = Dummy()
    set_orm_attributes(obj, {"a": 123, "b": "hello"})
    assert obj.a == 123
    assert obj.b == "hello"


def test_timestamp_to_datetime_returns_datetime() -> None:
    dt = timestamp_to_datetime(0.0)
    # Should return a datetime instance (epoch)
    assert dt.year == 1970
