from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.domain.billing.entities.invoice import Invoice


def test_invoice_stores_core_billing_fields() -> None:
    issued_at = datetime(2026, 6, 18, 12, 0, tzinfo=UTC)
    due_at = issued_at + timedelta(days=14)
    paid_at = issued_at + timedelta(days=2)

    invoice = Invoice(
        user_id=uuid4(),
        stripe_customer_id="cus_123",
        stripe_invoice_id="in_123",
        stripe_payment_id="pi_123",
        amount=2900,
        currency="eur",
        status="paid",
        date=issued_at,
        due_date=due_at,
        paid_at=paid_at,
        description="Pro plan",
        hosted_invoice_url="https://stripe.test/invoice",
    )

    assert invoice.stripe_customer_id == "cus_123"
    assert invoice.stripe_invoice_id == "in_123"
    assert invoice.stripe_payment_id == "pi_123"
    assert invoice.amount == 2900
    assert invoice.currency == "eur"
    assert invoice.status == "paid"
    assert invoice.date == issued_at
    assert invoice.due_date == due_at
    assert invoice.paid_at == paid_at
    assert invoice.description == "Pro plan"
    assert invoice.hosted_invoice_url == "https://stripe.test/invoice"
    assert invoice.is_paid() is True
    assert invoice.days_since_issue(reference=issued_at + timedelta(days=3)) == 3
    assert invoice.get_display_amount() == 29.0


def test_invoice_accepts_partial_stripe_payload() -> None:
    invoice = Invoice(
        user_id=uuid4(),
        stripe_customer_id="cus_123",
        stripe_invoice_id=None,
        stripe_payment_id=None,
        amount=0,
        currency="chf",
        status="draft",
        date=datetime(2026, 6, 18, 12, 0, tzinfo=UTC),
    )

    assert invoice.stripe_invoice_id is None
    assert invoice.stripe_payment_id is None
    assert invoice.due_date is None
    assert invoice.paid_at is None
    assert invoice.description is None
    assert invoice.hosted_invoice_url is None
    assert invoice.is_paid() is False


def test_invoice_rejects_invalid_amount() -> None:
    with pytest.raises(ValueError, match="amount must be a positive integer"):
        Invoice(
            user_id=uuid4(),
            stripe_customer_id="cus_123",
            stripe_invoice_id="in_123",
            stripe_payment_id=None,
            amount=-1,
            currency="eur",
            status="draft",
            date=datetime(2026, 6, 18, 12, 0, tzinfo=UTC),
        )


def test_invoice_rejects_invalid_currency() -> None:
    with pytest.raises(ValueError, match="currency must be an ISO 4217 code"):
        Invoice(
            user_id=uuid4(),
            stripe_customer_id="cus_123",
            stripe_invoice_id="in_123",
            stripe_payment_id=None,
            amount=2900,
            currency="euro",
            status="draft",
            date=datetime(2026, 6, 18, 12, 0, tzinfo=UTC),
        )
