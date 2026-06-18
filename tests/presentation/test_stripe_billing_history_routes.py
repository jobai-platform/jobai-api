from datetime import UTC, datetime, timedelta

import pytest

from app.domain.billing.entities.invoice import Invoice
from app.infrastructure.persistence.models.invoice import InvoiceModel


@pytest.mark.asyncio
async def test_get_billing_history_returns_items_and_pagination(client, create_user_in_db, db_session):
    user = await create_user_in_db(email="history@test.com", password=None, stripe_customer_id="cus_history")
    now = datetime(2026, 6, 18, 12, 0, tzinfo=UTC)

    db_session.add(
        InvoiceModel(
            user_id=user.id,
            stripe_customer_id="cus_history",
            stripe_invoice_id="in_2",
            stripe_payment_id="pi_2",
            amount=2900,
            currency="eur",
            status="paid",
            date=now,
            due_date=now + timedelta(days=14),
            paid_at=now + timedelta(days=1),
            description="June invoice",
            hosted_invoice_url="https://stripe.test/in_2",
        )
    )
    db_session.add(
        InvoiceModel(
            user_id=user.id,
            stripe_customer_id="cus_history",
            stripe_invoice_id="in_1",
            stripe_payment_id="pi_1",
            amount=1900,
            currency="eur",
            status="paid",
            date=now - timedelta(days=30),
            due_date=now - timedelta(days=16),
            paid_at=now - timedelta(days=28),
            description="May invoice",
            hosted_invoice_url="https://stripe.test/in_1",
        )
    )
    await db_session.commit()

    from app import main as app_module
    from app.presentation.security.deps import get_current_user_id

    app_module.app.dependency_overrides[get_current_user_id] = lambda: user.id

    response = await client.get("/api/v1/stripe/billing-history?limit=1&offset=0")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["limit"] == 1
    assert body["offset"] == 0
    assert body["has_more"] is True
    assert len(body["items"]) == 1
    assert body["items"][0]["stripe_invoice_id"] == "in_2"
    assert body["items"][0]["amount"] == 2900
    assert body["items"][0]["currency"] == "eur"


@pytest.mark.asyncio
async def test_get_billing_history_returns_empty_list_when_no_history(client, create_user_in_db):
    user = await create_user_in_db(email="empty@test.com", password=None, stripe_customer_id="cus_empty")

    from app import main as app_module
    from app.presentation.security.deps import get_current_user_id

    app_module.app.dependency_overrides[get_current_user_id] = lambda: user.id

    response = await client.get("/api/v1/stripe/billing-history")

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0
