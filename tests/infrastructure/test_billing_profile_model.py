from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.billing.entities.billing_address import BillingAddress
from app.domain.billing.entities.billing_profile import BillingProfile
from app.domain.billing.entities.payment_method_snapshot import PaymentMethodSnapshot
from app.infrastructure.persistence.models.billing_profile import BillingProfileModel
from app.infrastructure.persistence.repositories.billing_profile_sqlalchemy import (
    BillingProfileSQLAlchemyRepository,
    billing_profile_from_stripe_customer_payload,
    payment_method_snapshot_from_stripe_payload,
)


@pytest.mark.asyncio
async def test_billing_profile_model_round_trip(db_session, create_user_in_db):
    user = await create_user_in_db(email="billing@test.com", password=None, stripe_customer_id="cus_billing")
    issued_at = datetime(2026, 6, 18, 12, 0, tzinfo=UTC)

    model = BillingProfileModel(
        user_id=user.id,
        stripe_customer_id="cus_billing",
        contact_first_name="Marie",
        contact_last_name="Curie",
        contact_email="billing@example.com",
        address_line1="1 Rue du Test",
        address_line2="Apt 2",
        address_city="Geneva",
        address_state="GE",
        address_postal_code="1200",
        address_country="CH",
        payment_method_id="pm_123",
        payment_method_brand="visa",
        payment_method_last4="4242",
        payment_method_exp_month=12,
        payment_method_exp_year=2027,
        payment_method_holder_name="Marie Curie",
        payment_method_country="CH",
        payment_method_funding="credit",
        payment_method_wallet="apple_pay",
        created_at=issued_at,
        updated_at=issued_at,
    )
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)

    fetched = await db_session.get(BillingProfileModel, model.id)
    assert fetched is not None
    assert fetched.user_id == user.id
    assert fetched.stripe_customer_id == "cus_billing"
    assert fetched.contact_email == "billing@example.com"
    assert fetched.address_country == "CH"
    assert fetched.payment_method_last4 == "4242"


@pytest.mark.asyncio
async def test_billing_profile_repository_round_trips_address_and_payment_snapshot(db_session, create_user_in_db):
    user = await create_user_in_db(email="repo@test.com", password=None, stripe_customer_id="cus_repo")
    repo = BillingProfileSQLAlchemyRepository(session=db_session)

    profile = BillingProfile(
        user_id=user.id,
        stripe_customer_id="cus_repo",
        contact_first_name="Ada",
        contact_last_name="Lovelace",
        contact_email="ada@example.com",
        billing_address=BillingAddress(line1="10 Downing St", city="London", postal_code="SW1A", country="GB"),
        payment_method_snapshot=PaymentMethodSnapshot(
            stripe_payment_method_id="pm_repo",
            brand="mastercard",
            last4="9876",
            exp_month=1,
            exp_year=2028,
            holder_name="Ada Lovelace",
            country="GB",
            funding="credit",
        ),
    )

    created = await repo.upsert(profile)
    assert created.contact_full_name == "Ada Lovelace"
    assert created.billing_address is not None
    assert created.billing_address.as_single_line() == "10 Downing St, SW1A, London, GB"
    assert created.payment_method_snapshot is not None
    assert created.payment_method_snapshot.masked_display == "mastercard •••• 9876"

    fetched = await repo.get_by_stripe_customer_id("cus_repo")
    assert fetched is not None
    assert fetched.contact_email == "ada@example.com"
    assert fetched.payment_method_snapshot is not None
    assert fetched.payment_method_snapshot.expiry_display == "01/2028"


def test_billing_profile_from_stripe_customer_payload_skips_incomplete_address() -> None:
    profile = billing_profile_from_stripe_customer_payload(
        user_id=uuid4(),
        customer={
            "id": "cus_123",
            "name": "Marie Curie",
            "email": "billing@example.com",
            "address": {"line1": "1 Rue du Test", "city": "Geneva", "postal_code": "1200"},
            "metadata": {"last_name": "Curie"},
        },
    )

    assert profile.stripe_customer_id == "cus_123"
    assert profile.contact_first_name == "Marie Curie"
    assert profile.contact_last_name == "Curie"
    assert profile.billing_address is None


def test_payment_method_snapshot_from_stripe_payload_masks_card() -> None:
    snapshot = payment_method_snapshot_from_stripe_payload(
        {
            "id": "pm_123",
            "card": {
                "brand": "visa",
                "last4": "4242",
                "exp_month": 12,
                "exp_year": 2027,
                "country": "CH",
                "funding": "credit",
                "wallet": {"type": "apple_pay"},
            },
            "billing_details": {"name": "Marie Curie"},
        }
    )

    assert snapshot.stripe_payment_method_id == "pm_123"
    assert snapshot.masked_display == "visa •••• 4242"
    assert snapshot.expiry_display == "12/2027"
