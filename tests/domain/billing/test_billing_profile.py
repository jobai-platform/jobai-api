from datetime import UTC, datetime
from uuid import uuid4

from app.domain.billing.entities.billing_address import BillingAddress
from app.domain.billing.entities.billing_profile import BillingProfile
from app.domain.billing.entities.payment_method_snapshot import PaymentMethodSnapshot


def test_billing_profile_tracks_contact_address_and_payment_snapshot() -> None:
    profile = BillingProfile(
        user_id=uuid4(),
        stripe_customer_id=" cus_123 ",
        contact_first_name="  Marie ",
        contact_last_name=" Curie ",
        contact_email=" MARIE@EXAMPLE.COM ",
        billing_address=BillingAddress(
            line1="1 Rue du Test",
            city="Geneva",
            postal_code="1200",
            country="CH",
        ),
        payment_method_snapshot=PaymentMethodSnapshot(
            stripe_payment_method_id="pm_123",
            brand="visa",
            last4="4242",
            exp_month=12,
            exp_year=2027,
        ),
        created_at=datetime(2026, 6, 18, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 6, 18, 12, 0, tzinfo=UTC),
    )

    assert profile.stripe_customer_id == "cus_123"
    assert profile.contact_first_name == "Marie"
    assert profile.contact_last_name == "Curie"
    assert profile.contact_email == "marie@example.com"
    assert profile.contact_full_name == "Marie Curie"
    assert profile.billing_address is not None
    assert profile.billing_address.city == "Geneva"
    assert profile.payment_method_snapshot is not None
    assert profile.payment_method_snapshot.masked_display == "visa •••• 4242"


def test_billing_profile_updates_contact_and_snapshots() -> None:
    profile = BillingProfile(user_id=uuid4())

    profile.update_contact_info(first_name="Ada", last_name="Lovelace", email="ADA@EXAMPLE.COM")
    profile.update_billing_address(
        BillingAddress(line1="10 Downing St", city="London", postal_code="SW1A", country="GB")
    )
    profile.update_payment_method(
        PaymentMethodSnapshot(
            stripe_payment_method_id="pm_456",
            brand="mastercard",
            last4="9876",
            exp_month=1,
            exp_year=2028,
        )
    )

    assert profile.contact_full_name == "Ada Lovelace"
    assert profile.contact_email == "ada@example.com"
    assert profile.billing_address is not None
    assert profile.billing_address.as_single_line() == "10 Downing St, SW1A, London, GB"
    assert profile.payment_method_snapshot is not None
    assert profile.payment_method_snapshot.masked_display == "mastercard •••• 9876"
    assert profile.updated_at.tzinfo is not None
