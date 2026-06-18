# Stripe Subscription Summary API Plan

**Status:** Planned
**Date:** 2026-06-18
**Owner:** Forge
**Design:** `docs/superpowers/specs/stripe-subscription-summary.md`
**Audit:** `AUDIT_STRIPE_SUBSCRIPTION_SUMMARY.md`

## Objective

Extend the Stripe subscription summary path so the backend exposes the current plan, status, billing period, cancellation
state, and monetary metadata for the authenticated user.

## TDD Plan

1. Write domain tests for the new `Subscription` fields and keep existing behavior unchanged.
2. Extend the domain entity with the Stripe period and monetary fields.
3. Write infrastructure tests for the subscription model and repository mapping of the new nullable columns.
4. Add the database migration for the new subscription columns.
5. Implement the persistence changes and repository mapping.
6. Write application tests for webhook-driven subscription updates and partial Stripe payloads.
7. Extend the webhook handling so Stripe subscription events persist the new fields.
8. Write presentation tests for `GET /api/v1/stripe/subscriptions/me` with complete, partial, and missing data.
9. Extend the API schema and route to return the full subscription summary contract.
10. Update the consumer-facing API documentation.
11. Run the focused test suites, then the repository lint/type checks on touched files.

## Expected Files

```text
app/domain/billing/entities/subscription.py
app/infrastructure/persistence/models/subscription.py
app/infrastructure/persistence/repositories/subscription_sqlalchemy.py
app/application/billing/use_cases.py
app/presentation/api/v1/schemas/billing.py
app/presentation/api/v1/stripe_routes.py
tests/domain/billing/test_subscription.py
tests/infrastructure/test_subscription_model.py
tests/application/billing/test_use_cases.py
tests/presentation/test_stripe_routes.py
docs/superpowers/specs/stripe-subscription-summary.md
docs/superpowers/plans/2026-06-18-stripe-subscription-summary.md
docs/api/stripe-subscription-summary.md
```

## Complexity

| Area | Effort | Notes |
|---|---|---|
| Domain | S | Add nullable subscription fields |
| Application | M | Webhook payload extraction and persistence |
| Infrastructure | M | Model, repository, and migration updates |
| Presentation | S | DTO and route serialization |
| Tests | M | Layered coverage for summary and webhook paths |
| Documentation | S | Plan, spec, and API contract |
| Total | M | Backward-compatible billing contract expansion |
