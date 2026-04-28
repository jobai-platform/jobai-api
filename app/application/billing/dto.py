from dataclasses import dataclass


@dataclass(frozen=True)
class CheckoutSessionResult:
    checkout_url: str
