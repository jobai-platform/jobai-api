from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from app.domain.billing.entities.billing_price import BillingPrice
from app.domain.billing.entities.invoice import Invoice
from app.domain.billing.entities.subscription import Subscription
from app.domain.billing.enums import Plan


class SubscriptionRepository(ABC):
    """
    Abstract base class that represents a subscription repository.
    """
    @abstractmethod
    async def get_by_user_id(self, user_id: UUID) -> Subscription | None:
        """
        Get Subscription by user ID.
        :param user_id: User ID.
        :return: Subscription object.
        """
        raise NotImplementedError()


    @abstractmethod
    async def get_by_stripe_subscription_id(self, stripe_subscription_id: str) -> Subscription | None:
        """
        Get Subscription by Stripe Subscription ID.
        :param stripe_subscription_id: Stripe Subscription ID.
        :return: Subscription object.
        """
        raise NotImplementedError()


    @abstractmethod
    async def create(self, subscription: Subscription) -> Subscription:
        """
        Create a new Subscription.
        :param subscription: Subscription object.
        :return: Subscription object.
        """
        raise NotImplementedError()


    @abstractmethod
    async def update(self, subscription: Subscription) -> Subscription | None:
        """
        Update subscription for a given user (user_id is read from subscription.user_id).
        :param subscription: Subscription object.
        :return: Subscription object.
        """
        raise NotImplementedError()


class BillingPriceRepository(ABC):
    """
    Abstract base class that represents a billing price repository.
    Billing prices are synchronized from stripe and stored locally.
    """
    @abstractmethod
    async def upsert(self, price: BillingPrice) -> BillingPrice:
        """
        Create or update a BillingPrice.
        :param price: BillingPrice domain entity.
        :return: BillingPrice domain entity.
        """
        raise NotImplementedError()

    @abstractmethod
    async def get_active_by_plan(self, plan: Plan) -> BillingPrice | None:
        """
        Get active BillingPrice by plan.
        :param plan: Plan enum value.
        :return: BillingPrice domain entity or None if not found.
        """
        raise NotImplementedError()


class BillingGateway(ABC):
    """
    Port for external billing provides, currently Stripe.
    """
    @abstractmethod
    async def create_checkout_session(
        self,
        *,
        email: str,
        user_id: UUID,
        plan: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        """
        Create a Stripe checkout session for a given user.
        :param email: User email.
        :param user_id: User ID.
        :param plan: Plan name.
        :param success_url: URL to redirect after successful payment.
        :param cancel_url: URL to redirect after canceled payment.
        :return: Checkout session URL.
        """
        raise NotImplementedError()

    @abstractmethod
    async def create_customer(
        self,
        *,
        email: str,
        user_id: UUID,
    ) -> str:
        """
        Create a Stripe customer for a given user.
        :param email: User email.
        :param user_id: User ID.
        :return: Stripe customer ID.
        """
        raise NotImplementedError()

    @abstractmethod
    async def create_subscription(
        self,
        *,
        customer_id: str,
        stripe_price_id: str,
        user_id: UUID,
        plan: Plan,
    ) -> str:
        """
        Create a Stripe subscription for a given customer and price.
        :param customer_id: Stripe customer ID.
        :param stripe_price_id: Stripe price ID.
        :param user_id: User ID.
        :param plan: Plan name.
        :return: Stripe subscription ID.
        """
        raise NotImplementedError()

    @abstractmethod
    async def list_prices(self) -> list[dict]:
        """
        List all prices from Stripe with normalized metada.
        Expected result item:
        {
            "stripe_price_id": "str",
            "stripe_product_id": "str",
            "plan": "str",
            "currency": "str",
            "amount": "float",
            "interval": "str",
            "active": "bool",
        }
        :return: List of normalized Stripe prices.
        """
        raise NotImplementedError()


    @abstractmethod
    async def verify_and_construct_event(self, payload: bytes, signature: str) -> dict:
        """
        Verify the webhook signature and construct the event object.
        :param payload: Webhook payload.
        :param signature: Webhook signature.
        :return: Event object.
        """
        raise NotImplementedError()


class InvoiceRepository(ABC):
    @abstractmethod
    async def get_by_user_id(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Invoice]:
        raise NotImplementedError()

    @abstractmethod
    async def get_by_stripe_customer_id(
        self,
        stripe_customer_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Invoice]:
        raise NotImplementedError()

    @abstractmethod
    async def get_by_stripe_invoice_id(self, stripe_invoice_id: str) -> Invoice | None:
        raise NotImplementedError()

    @abstractmethod
    async def add(self, invoice: Invoice) -> Invoice:
        raise NotImplementedError()

    @abstractmethod
    async def update(self, invoice: Invoice) -> Invoice | None:
        raise NotImplementedError()

    @abstractmethod
    async def count_by_user_id(self, user_id: UUID) -> int:
        raise NotImplementedError()

    @abstractmethod
    async def count_by_stripe_customer_id(self, stripe_customer_id: str) -> int:
        raise NotImplementedError()
