from enum import Enum

class SubscriptionPlan(str, Enum):
    FREEMIUM = "freemium"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    PENDING = "pending"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
