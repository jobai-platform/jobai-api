# Stripe Subscription Summary API

**Bounded Context:** billing
**Status:** Approved
**Date:** 2026-06-18
**Owner:** Forge
**Sources:** `SPEC_STRIPE_SUBSCRIPTION_SUMMARY.md`, `AUDIT_STRIPE_SUBSCRIPTION_SUMMARY.md`

## Goal

Expose the current Stripe subscription state of the authenticated user through a stable backend contract.

The contract must return only data that already exists in Stripe or in the persisted subscription record. No derived or
invented values are allowed.

## Scope

In scope:

- `GET /api/v1/stripe/subscriptions/me`;
- current plan and status;
- billing period fields from Stripe;
- cancellation fields from Stripe;
- monetary fields from Stripe;
- metadata required by the billing UI;
- backward-compatible nullable response fields.

Out of scope:

- subscription updates from this endpoint;
- multiple active subscriptions per user;
- invoice history;
- coupon and promotion management;
- frontend implementation.

## Contract

### HTTP

`GET /api/v1/stripe/subscriptions/me`

Authentication: connected user.

Success response: `200 OK`.

Missing subscription response: `404 Not Found` with `subscription_not_found`.

### Response fields

| Field | Type | Nullable | Notes |
|---|---|---:|---|
| `user_id` | `UUID` | No | Owner of the subscription |
| `plan` | `string` | No | Current plan value from the domain enum |
| `status` | `string` | No | Current subscription status |
| `stripe_customer_id` | `string` | Yes | Stripe customer identifier |
| `stripe_subscription_id` | `string` | Yes | Stripe subscription identifier |
| `billing_price_id` | `UUID` | Yes | Internal price reference |
| `current_period_start` | `datetime` | Yes | Start of the current billing period |
| `current_period_end` | `datetime` | Yes | End of the current billing period |
| `cancel_at_period_end` | `boolean` | Yes | Stripe cancellation flag |
| `canceled_at` | `datetime` | Yes | Stripe cancellation timestamp |
| `amount` | `integer` | Yes | Raw amount stored from Stripe |
| `currency` | `string` | Yes | Currency code stored from Stripe |

## Architecture Impact

| Layer | Change |
|---|---|
| Domain | Extend `Subscription` with billing-period and monetary fields |
| Application | Ensure Stripe webhook handling stores the new fields |
| Infrastructure | Add nullable persistence columns and map them in the repository |
| Presentation | Extend `SubscriptionRead` and return the complete summary contract |

## Acceptance Criteria

- The authenticated user can retrieve a reliable subscription summary.
- The response stays stable across subscriptions with partial Stripe data.
- Existing subscriptions without the new fields keep working.
- Webhook-driven updates populate the persisted fields.
- The API documentation matches the returned contract.

## Validation Notes

- Use nullable fields everywhere the Stripe payload may be absent.
- Preserve the existing `404` behavior when no subscription record exists.
- Keep serialization ISO-8601 compatible for all datetime fields.
