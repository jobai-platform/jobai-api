import pytest

from app.domain.billing.entities.payment_method_snapshot import PaymentMethodSnapshot


def test_payment_method_snapshot_masks_card_data() -> None:
    snapshot = PaymentMethodSnapshot(
        stripe_payment_method_id="pm_123",
        brand="visa",
        last4="4242",
        exp_month=12,
        exp_year=2027,
        holder_name="  Marie Curie ",
        country=" ch ",
        funding=" credit ",
        wallet=" apple_pay ",
    )

    assert snapshot.stripe_payment_method_id == "pm_123"
    assert snapshot.brand == "visa"
    assert snapshot.last4 == "4242"
    assert snapshot.holder_name == "Marie Curie"
    assert snapshot.country == "CH"
    assert snapshot.funding == "credit"
    assert snapshot.wallet == "apple_pay"
    assert snapshot.masked_display == "visa •••• 4242"
    assert snapshot.expiry_display == "12/2027"


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        (
            {
                "stripe_payment_method_id": None,
                "brand": "",
                "last4": "4242",
                "exp_month": 12,
                "exp_year": 2027,
            },
            "brand cannot be empty",
        ),
        (
            {
                "stripe_payment_method_id": None,
                "brand": "visa",
                "last4": "42",
                "exp_month": 12,
                "exp_year": 2027,
            },
            "last4 must contain exactly 4 digits",
        ),
        (
            {
                "stripe_payment_method_id": None,
                "brand": "visa",
                "last4": "4242",
                "exp_month": 0,
                "exp_year": 2027,
            },
            "exp_month must be between 1 and 12",
        ),
    ],
)
def test_payment_method_snapshot_rejects_invalid_values(kwargs: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        PaymentMethodSnapshot(**kwargs)
