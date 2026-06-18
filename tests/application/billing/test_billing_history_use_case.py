from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.application.billing.dto import BillingHistoryResult
from app.application.billing.use_cases import GetBillingHistoryUseCase
from app.domain.billing.entities.invoice import Invoice
from app.domain.billing.entities.subscription import Subscription
from app.domain.billing.enums import Plan, SubscriptionStatus
from app.domain.common.exceptions import NotFoundError


@dataclass
class _User:
    id: UUID
    stripe_customer_id: str | None


class FakeUserRepo:
    def __init__(self, user: _User | None):
        self.user = user

    async def get_by_id(self, user_id):
        return self.user


class FakeInvoiceRepo:
    def __init__(self, invoices: list[Invoice] | None = None):
        self.invoices = invoices or []
        self.calls: list[tuple[str, object]] = []

    async def get_by_stripe_customer_id(self, stripe_customer_id: str, limit: int = 50, offset: int = 0):
        self.calls.append(("get_by_stripe_customer_id", stripe_customer_id, limit, offset))
        invoices = [invoice for invoice in self.invoices if invoice.stripe_customer_id == stripe_customer_id]
        return invoices[offset : offset + limit]

    async def count_by_stripe_customer_id(self, stripe_customer_id: str) -> int:
        self.calls.append(("count_by_stripe_customer_id", stripe_customer_id))
        return sum(1 for invoice in self.invoices if invoice.stripe_customer_id == stripe_customer_id)

    async def add(self, invoice: Invoice) -> Invoice:
        self.invoices.append(invoice)
        return invoice

    async def get_by_user_id(self, user_id, limit: int = 50, offset: int = 0):
        return [invoice for invoice in self.invoices if invoice.user_id == user_id][offset : offset + limit]

    async def get_by_stripe_invoice_id(self, stripe_invoice_id: str):
        return next((invoice for invoice in self.invoices if invoice.stripe_invoice_id == stripe_invoice_id), None)

    async def count_by_user_id(self, user_id):
        return sum(1 for invoice in self.invoices if invoice.user_id == user_id)


@pytest.mark.asyncio
async def test_get_billing_history_returns_paginated_results_for_connected_user():
    user_id = uuid4()
    customer_id = "cus_123"
    issued_at = datetime(2026, 6, 18, 12, 0, tzinfo=UTC)

    invoices = [
        Invoice(
            user_id=user_id,
            stripe_customer_id=customer_id,
            stripe_invoice_id="in_2",
            stripe_payment_id="pi_2",
            amount=2900,
            currency="eur",
            status="paid",
            date=issued_at,
            description="June invoice",
        ),
        Invoice(
            user_id=user_id,
            stripe_customer_id=customer_id,
            stripe_invoice_id="in_1",
            stripe_payment_id="pi_1",
            amount=1900,
            currency="eur",
            status="paid",
            date=issued_at.replace(hour=10),
            description="May invoice",
        ),
    ]

    uc = GetBillingHistoryUseCase(
        user_repository=FakeUserRepo(_User(id=user_id, stripe_customer_id=customer_id)),
        invoice_repository=FakeInvoiceRepo(invoices=invoices),
    )

    result = await uc.execute(user_id=user_id, limit=1, offset=0)

    assert isinstance(result, BillingHistoryResult)
    assert result.limit == 1
    assert result.offset == 0
    assert result.total == 2
    assert result.has_more is True
    assert len(result.items) == 1
    assert result.items[0].stripe_invoice_id == "in_2"


@pytest.mark.asyncio
async def test_get_billing_history_returns_empty_list_when_user_has_no_customer_id():
    user_id = uuid4()
    uc = GetBillingHistoryUseCase(
        user_repository=FakeUserRepo(_User(id=user_id, stripe_customer_id=None)),
        invoice_repository=FakeInvoiceRepo(),
    )

    result = await uc.execute(user_id=user_id)

    assert result.items == []
    assert result.total == 0
    assert result.has_more is False


@pytest.mark.asyncio
async def test_get_billing_history_raises_when_user_missing():
    uc = GetBillingHistoryUseCase(
        user_repository=FakeUserRepo(None),
        invoice_repository=FakeInvoiceRepo(),
    )

    with pytest.raises(NotFoundError, match="User not found"):
        await uc.execute(user_id=uuid4())
