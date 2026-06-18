import logging
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.billing.ports import InvoiceRepository
from app.domain.billing.entities.invoice import Invoice
from app.infrastructure.persistence.models.invoice import InvoiceModel

logger = logging.getLogger(__name__)


def _to_domain(model: InvoiceModel) -> Invoice:
    return Invoice(
        id=UUID(str(model.id)),
        user_id=UUID(str(model.user_id)),
        stripe_customer_id=model.stripe_customer_id,
        stripe_invoice_id=model.stripe_invoice_id,
        stripe_payment_id=model.stripe_payment_id,
        amount=model.amount or 0,
        currency=model.currency or "usd",
        status=model.status or "",
        date=model.date,
        due_date=model.due_date,
        paid_at=model.paid_at,
        description=model.description,
        hosted_invoice_url=model.hosted_invoice_url,
    )


def _apply_domain_to_model(model: InvoiceModel, invoice: Invoice) -> None:
    model.user_id = str(invoice.user_id)
    model.stripe_customer_id = invoice.stripe_customer_id
    model.stripe_invoice_id = invoice.stripe_invoice_id
    model.stripe_payment_id = invoice.stripe_payment_id
    model.amount = invoice.amount
    model.currency = invoice.currency
    model.status = invoice.status
    model.date = invoice.date
    model.due_date = invoice.due_date
    model.paid_at = invoice.paid_at
    model.description = invoice.description
    model.hosted_invoice_url = invoice.hosted_invoice_url


class InvoiceSQLAlchemyRepository(InvoiceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_user_id(self, user_id: UUID, limit: int = 50, offset: int = 0) -> Sequence[Invoice]:
        stmt = (
            select(InvoiceModel)
            .where(InvoiceModel.user_id == str(user_id))
            .order_by(InvoiceModel.date.desc().nullslast(), InvoiceModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [_to_domain(model) for model in result.scalars().all()]

    async def get_by_stripe_customer_id(
        self,
        stripe_customer_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Invoice]:
        stmt = (
            select(InvoiceModel)
            .where(InvoiceModel.stripe_customer_id == stripe_customer_id)
            .order_by(InvoiceModel.date.desc().nullslast(), InvoiceModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [_to_domain(model) for model in result.scalars().all()]

    async def get_by_stripe_invoice_id(self, stripe_invoice_id: str) -> Invoice | None:
        stmt = select(InvoiceModel).where(InvoiceModel.stripe_invoice_id == stripe_invoice_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_domain(model) if model else None

    async def add(self, invoice: Invoice) -> Invoice:
        model = InvoiceModel(
            user_id=str(invoice.user_id),
            stripe_customer_id=invoice.stripe_customer_id,
            stripe_invoice_id=invoice.stripe_invoice_id,
            stripe_payment_id=invoice.stripe_payment_id,
            amount=invoice.amount,
            currency=invoice.currency,
            status=invoice.status,
            date=invoice.date,
            due_date=invoice.due_date,
            paid_at=invoice.paid_at,
            description=invoice.description,
            hosted_invoice_url=invoice.hosted_invoice_url,
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return _to_domain(model)

    async def update(self, invoice: Invoice) -> Invoice | None:
        stmt = select(InvoiceModel).where(InvoiceModel.id == str(invoice.id))
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        _apply_domain_to_model(model, invoice)
        await self.session.flush([model])
        await self.session.refresh(model)
        return _to_domain(model)

    async def count_by_user_id(self, user_id: UUID) -> int:
        stmt = select(func.count()).select_from(InvoiceModel).where(InvoiceModel.user_id == str(user_id))
        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def count_by_stripe_customer_id(self, stripe_customer_id: str) -> int:
        stmt = (
            select(func.count())
            .select_from(InvoiceModel)
            .where(InvoiceModel.stripe_customer_id == stripe_customer_id)
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)
