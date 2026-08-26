# Stripe Subscription Management

This document summarizes the billing area exposed by Sovrum for connected users.

## Implemented endpoints

`GET /api/v1/stripe/subscriptions/me`

- Returns the current subscription summary.
- Includes the current plan, status, Stripe identifiers, and nullable Stripe billing metadata.

`GET /api/v1/stripe/billing-history`

- Returns the connected user's invoice history.
- Uses a paginated envelope with `items`, `total`, `limit`, `offset`, and `has_more`.

`GET /api/v1/stripe/billing-profile`

- Returns the connected user's billing contact data.
- Includes the masked payment method snapshot when present.
- Returns empty-state fields when the user has no stored billing profile yet.

## Planned endpoints

`GET /api/v1/stripe/billing-profile`

- Returns billing contact data, billing address, and masked payment method summary.

`PUT /api/v1/stripe/billing-profile`

- Updates billing address and billing contact details.

`POST /api/v1/stripe/subscriptions/me/change-plan`

- Requests a plan change.
- Paid plans are scheduled for renewal.
- Freemium upgrades can be applied immediately.

`POST /api/v1/stripe/subscriptions/me/cancel`

- Schedules cancellation at the end of the current period or cancels immediately depending on the plan policy.

`POST /api/v1/stripe/subscriptions/me/reactivate`

- Restores a subscription scheduled for cancellation when the plan and Stripe state allow it.

`POST /api/v1/stripe/customer-portal/session`

- Opens Stripe Customer Portal for payment-method management.

## Notes for consumers

- Do not store or transmit raw card data.
- Treat Stripe as the source of truth for payment-method details.
- Expect some billing fields to remain nullable until the first webhook sync or customer-portal interaction.
