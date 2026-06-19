import pytest

from app.domain.billing.entities.billing_address import BillingAddress


def test_billing_address_normalizes_and_formats_single_line() -> None:
    address = BillingAddress(
        line1="  12 Rue de Lyon  ",
        line2=" Apt 5 ",
        city="  Geneve ",
        postal_code=" 1201 ",
        country=" ch ",
        state=" ge ",
    )

    assert address.line1 == "12 Rue de Lyon"
    assert address.line2 == "Apt 5"
    assert address.city == "Geneve"
    assert address.postal_code == "1201"
    assert address.country == "CH"
    assert address.state == "ge"
    assert address.as_single_line() == "12 Rue de Lyon, Apt 5, 1201, Geneve, CH"


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"line1": "", "city": "Geneva", "postal_code": "1200", "country": "CH"}, "line1 cannot be empty"),
        ({"line1": "Main", "city": " ", "postal_code": "1200", "country": "CH"}, "city cannot be empty"),
        ({"line1": "Main", "city": "Geneva", "postal_code": "", "country": "CH"}, "postal_code cannot be empty"),
        ({"line1": "Main", "city": "Geneva", "postal_code": "1200", "country": " "}, "country cannot be empty"),
    ],
)
def test_billing_address_rejects_empty_required_fields(kwargs: dict[str, str], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        BillingAddress(**kwargs)


def test_billing_address_rejects_invalid_country_code() -> None:
    with pytest.raises(ValueError, match="country must be a valid ISO country code"):
        BillingAddress(line1="Main", city="Geneva", postal_code="1200", country="CHEM")
