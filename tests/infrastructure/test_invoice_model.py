from datetime import UTC, datetime, timedelta

import pytest

from app.domain.billing.entities.invoice import Invoice
from app.domain.billing.enums import Plan
from app.infrastructure.persistence.models.invoice import InvoiceModel
from app.infrastructure.persistence.repositories.invoice_sqlalchemy import InvoiceSQLAlchemyRepository


@pytest.mark.asyncio
async def test_invoice_model_crud(db_session, create_user_in_db):
    user = await create_user_in_db(email="invoice@test.com", password=None, stripe_customer_id="cus_invoice")
    issued_at = datetime(2026, 6, 18, 12, 0, tzinfo=UTC)
    due_at = issued_at + timedelta(days=14)

    model = InvoiceModel(
        user_id=user.id,
        stripe_customer_id="cus_invoice",
        stripe_invoice_id="in_invoice",
        stripe_payment_id="pi_invoice",
        amount=2900,
        currency="eur",
        status="paid",
        date=issued_at,
        due_date=due_at,
        paid_at=issued_at + timedelta(days=1),
        description="Pro plan",
        hosted_invoice_url="https://stripe.test/invoice",
    )
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)

    fetched = await db_session.get(InvoiceModel, model.id)
    assert fetched is not None
    assert fetched.user_id == user.id
    assert fetched.stripe_customer_id == "cus_invoice"
    assert fetched.stripe_invoice_id == "in_invoice"
    assert fetched.amount == 2900
    assert fetched.currency == "eur"
    assert fetched.status == "paid"
    assert fetched.date == issued_at
    assert fetched.due_date == due_at


@pytest.mark.asyncio
async def test_invoice_repository_filters_and_paginates_by_stripe_customer_id(db_session, create_user_in_db):
    user = await create_user_in_db(email="repo@test.com", password=None, stripe_customer_id="cus_repo")
    other_user = await create_user_in_db(email="other@test.com", password=None, stripe_customer_id="cus_other")
    repo = InvoiceSQLAlchemyRepository(session=db_session)
    issued_at = datetime(2026, 6, 18, 12, 0, tzinfo=UTC)

    first = Invoice(
        user_id=user.id,
        stripe_customer_id="cus_repo",
        stripe_invoice_id="in_2",
        stripe_payment_id="pi_2",
        amount=2900,
        currency="eur",
        status="paid",
        date=issued_at,
        description="June",
    )
    second = Invoice(
        user_id=user.id,
        stripe_customer_id="cus_repo",
        stripe_invoice_id="in_1",
        stripe_payment_id="pi_1",
        amount=1900,
        currency="eur",
        status="paid",
        date=issued_at.replace(hour=10),
        description="May",
    )
    other = Invoice(
        user_id=other_user.id,
        stripe_customer_id="cus_other",
        stripe_invoice_id="in_other",
        stripe_payment_id="pi_other",
        amount=4900,
        currency="chf",
        status="paid",
        date=issued_at,
        description="Other",
    )

    await repo.add(first)
    await repo.add(second)
    await repo.add(other)

    items = await repo.get_by_stripe_customer_id("cus_repo", limit=1, offset=0)

    assert len(items) == 1
    assert items[0].stripe_invoice_id == "in_2"
    assert await repo.count_by_stripe_customer_id("cus_repo") == 2
    assert await repo.get_by_stripe_invoice_id("in_other") is not None
    assert await repo.count_by_user_id(user.id) == 2
