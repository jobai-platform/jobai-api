# Stripe Subscription Summary API

## Endpoint

`GET /api/v1/stripe/subscriptions/me`

Returns the current Stripe subscription summary for the authenticated user.

## Authentication

Bearer token for the connected user.

## Success Response

`200 OK`

```json
{
  "user_id": "8c1d4f8f-8d8a-4a9b-9b9a-5b3d5a9c3f2a",
  "plan": "pro",
  "status": "active",
  "stripe_customer_id": "cus_123",
  "stripe_subscription_id": "sub_123",
  "billing_price_id": "7d2e6d1f-2d3a-4acb-9a4f-1d0f8b7d5c2e",
  "current_period_start": "2026-06-01T00:00:00Z",
  "current_period_end": "2026-07-01T00:00:00Z",
  "cancel_at_period_end": false,
  "canceled_at": null,
  "amount": 2900,
  "currency": "eur"
}
```

The API returns the raw persisted subscription data. Fields that are not yet available from Stripe or from the
subscription record remain `null`.

## Error Response

`404 Not Found`

```json
{
  "code": "subscription_not_found",
  "detail": "No active subscription found for user 8c1d4f8f-8d8a-4a9b-9b9a-5b3d5a9c3f2a"
}
```

## Returned Fields

| Field | Description |
|---|---|
| `user_id` | Owner of the subscription record |
| `plan` | Current billing plan |
| `status` | Current subscription status |
| `stripe_customer_id` | Stripe customer identifier |
| `stripe_subscription_id` | Stripe subscription identifier |
| `billing_price_id` | Internal billing price identifier |
| `current_period_start` | Start timestamp of the current billing period |
| `current_period_end` | End timestamp of the current billing period |
| `cancel_at_period_end` | Boolean cancellation flag |
| `canceled_at` | Stripe cancellation timestamp |
| `amount` | Persisted subscription amount |
| `currency` | Persisted subscription currency |

## Notes For Consumers

- Treat all date fields as ISO-8601 timestamps.
- Do not assume the optional fields are present for trial, incomplete, or partially synchronized subscriptions.
- Use `amount` and `currency` together for billing display.
- Do not derive plan or status locally; use the backend payload as the source of truth.
