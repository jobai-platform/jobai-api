from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from app.domain.billing.entities import Subscription


class SubscriptionRepository(ABC):
    """
    Abstract base class that represents a subscription repository.
    """

    @abstractmethod
    async def get_by_user_id(self, user_id: UUID) -> Optional[Subscription]:
        """
        Get Subscription by user ID.
        :param user_id: User ID.
        :return: Subscription object.
        """
        raise NotImplementedError()


    @abstractmethod
    async def get_by_stripe_subscription_id(self, stripe_subscription_id: str) -> Optional[Subscription]:
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
    async def update(self, user_id: UUID, subscription: Subscription) -> Optional[Subscription]:
        """
        Update subscription for a given user.
        :param user_id: User ID.
        :param subscription: Subscription object.
        :return: Subscription object.
        """
        raise NotImplementedError()



class BillingGateway(ABC):
    """
    Port for external billing provides (Stripe).
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
    async def verify_and_construct_event(self, payload: bytes, signature: str) -> dict:
        """
        Verify the webhook signature and construct the event object.
        :param payload: Webhook payload.
        :param signature: Webhook signature.
        :return: Event object.
        """
        raise NotImplementedError()
