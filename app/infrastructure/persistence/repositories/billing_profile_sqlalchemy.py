import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.billing.ports import BillingProfileRepository
from app.domain.billing.entities.billing_address import BillingAddress
from app.domain.billing.entities.billing_profile import BillingProfile
from app.domain.billing.entities.payment_method_snapshot import PaymentMethodSnapshot
from app.infrastructure.persistence.models.billing_profile import BillingProfileModel

logger = logging.getLogger(__name__)


def _billing_address_from_model(model: BillingProfileModel) -> BillingAddress | None:
    address_values = (
        model.address_line1,
        model.address_city,
        model.address_postal_code,
        model.address_country,
    )
    if not any(address_values):
        return None
    if not all(address_values):
        return None
    return BillingAddress(
        line1=model.address_line1 or "",
        line2=model.address_line2,
        city=model.address_city or "",
        state=model.address_state,
        postal_code=model.address_postal_code or "",
        country=model.address_country or "",
    )


def _payment_method_from_model(model: BillingProfileModel) -> PaymentMethodSnapshot | None:
    snapshot_values = (
        model.payment_method_brand,
        model.payment_method_last4,
        model.payment_method_exp_month,
        model.payment_method_exp_year,
    )
    if not any(snapshot_values):
        return None
    if not all(snapshot_values):
        return None
    return PaymentMethodSnapshot(
        stripe_payment_method_id=model.payment_method_id,
        brand=model.payment_method_brand or "",
        last4=model.payment_method_last4 or "",
        exp_month=model.payment_method_exp_month or 0,
        exp_year=model.payment_method_exp_year or 0,
        holder_name=model.payment_method_holder_name,
        country=model.payment_method_country,
        funding=model.payment_method_funding,
        wallet=model.payment_method_wallet,
    )


def _to_domain(model: BillingProfileModel) -> BillingProfile:
    return BillingProfile(
        user_id=UUID(str(model.user_id)),
        stripe_customer_id=model.stripe_customer_id,
        contact_first_name=model.contact_first_name,
        contact_last_name=model.contact_last_name,
        contact_email=model.contact_email,
        billing_address=_billing_address_from_model(model),
        payment_method_snapshot=_payment_method_from_model(model),
    )


def _apply_domain_to_model(model: BillingProfileModel, profile: BillingProfile) -> None:
    model.user_id = str(profile.user_id)
    model.stripe_customer_id = profile.stripe_customer_id
    model.contact_first_name = profile.contact_first_name
    model.contact_last_name = profile.contact_last_name
    model.contact_email = profile.contact_email

    address = profile.billing_address
    if address is None:
        model.address_line1 = None
        model.address_line2 = None
        model.address_city = None
        model.address_state = None
        model.address_postal_code = None
        model.address_country = None
    else:
        model.address_line1 = address.line1
        model.address_line2 = address.line2
        model.address_city = address.city
        model.address_state = address.state
        model.address_postal_code = address.postal_code
        model.address_country = address.country

    snapshot = profile.payment_method_snapshot
    if snapshot is None:
        model.payment_method_id = None
        model.payment_method_brand = None
        model.payment_method_last4 = None
        model.payment_method_exp_month = None
        model.payment_method_exp_year = None
        model.payment_method_holder_name = None
        model.payment_method_country = None
        model.payment_method_funding = None
        model.payment_method_wallet = None
    else:
        model.payment_method_id = snapshot.stripe_payment_method_id
        model.payment_method_brand = snapshot.brand
        model.payment_method_last4 = snapshot.last4
        model.payment_method_exp_month = snapshot.exp_month
        model.payment_method_exp_year = snapshot.exp_year
        model.payment_method_holder_name = snapshot.holder_name
        model.payment_method_country = snapshot.country
        model.payment_method_funding = snapshot.funding
        model.payment_method_wallet = snapshot.wallet


def billing_profile_from_stripe_customer_payload(
    *,
    user_id: UUID,
    customer: dict,
) -> BillingProfile:
    address = customer.get("address") or {}
    name = (customer.get("name") or "").strip()
    invoice_settings = customer.get("invoice_settings") or {}
    first_name = invoice_settings.get("name") or name
    has_complete_address = all(
        [
            address.get("line1"),
            address.get("city"),
            address.get("postal_code"),
            address.get("country"),
        ],
    )

    return BillingProfile(
        user_id=user_id,
        stripe_customer_id=customer.get("id"),
        contact_first_name=first_name,
        contact_last_name=customer.get("metadata", {}).get("last_name"),
        contact_email=customer.get("email"),
        billing_address=BillingAddress(
            line1=address.get("line1") or "",
            line2=address.get("line2"),
            city=address.get("city") or "",
            state=address.get("state"),
            postal_code=address.get("postal_code") or "",
            country=address.get("country") or "",
        )
        if has_complete_address
        else None,
    )


def payment_method_snapshot_from_stripe_payload(payment_method: dict) -> PaymentMethodSnapshot:
    card = payment_method.get("card") or {}
    billing_details = payment_method.get("billing_details") or {}
    return PaymentMethodSnapshot(
        stripe_payment_method_id=payment_method.get("id"),
        brand=card.get("brand") or "",
        last4=card.get("last4") or "",
        exp_month=card.get("exp_month") or 0,
        exp_year=card.get("exp_year") or 0,
        holder_name=billing_details.get("name"),
        country=card.get("country"),
        funding=card.get("funding"),
        wallet=_extract_wallet_type(card.get("wallet")),
    )


class BillingProfileSQLAlchemyRepository(BillingProfileRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_user_id(self, user_id: UUID) -> BillingProfile | None:
        stmt = select(BillingProfileModel).where(BillingProfileModel.user_id == str(user_id))
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_domain(model) if model else None

    async def get_by_stripe_customer_id(self, stripe_customer_id: str) -> BillingProfile | None:
        stmt = select(BillingProfileModel).where(
            BillingProfileModel.stripe_customer_id == stripe_customer_id,
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_domain(model) if model else None

    async def upsert(self, profile: BillingProfile) -> BillingProfile:
        stmt = select(BillingProfileModel).where(
            BillingProfileModel.user_id == str(profile.user_id),
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            model = BillingProfileModel(user_id=str(profile.user_id))
            self.session.add(model)

        _apply_domain_to_model(model, profile)
        await self.session.flush([model])
        await self.session.refresh(model)
        return _to_domain(model)


def _extract_wallet_type(wallet: object) -> str | None:
    if isinstance(wallet, dict):
        value = wallet.get("type")
        return str(value) if value is not None else None
    if wallet is None:
        return None
    return str(wallet)
