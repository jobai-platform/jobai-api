# Stripe Subscription Management Plan

**Status:** Planned
**Date:** 2026-06-18
**Owner:** Forge
**Design:** `docs/superpowers/specs/stripe-subscription-management.md`

## Objective

Deliver a complete self-service billing area for Sovrum users on top of the existing Stripe subscription summary and
billing history APIs.

## Scope baseline

Already implemented:

- `GET /api/v1/stripe/subscriptions/me`
- `GET /api/v1/stripe/billing-history`

Missing for full management:

- billing profile read/update
- payment method summary and portal handoff
- plan change scheduling
- cancellation / reactivation flows
- frontend account billing section
- end-to-end tests across the billing area

## TDD plan

1. RED - add domain tests for billing profile, billing address, and payment method snapshot invariants.
2. GREEN - introduce the billing profile entities and value objects.
3. RED - add infrastructure tests for billing profile persistence and masked payment method snapshots.
4. GREEN - add persistence models, repository mappings, and migration(s).
5. RED - add application tests for billing account overview, profile update, plan change, cancel, reactivate, and portal session use cases.
6. GREEN - implement the application layer for billing account management.
7. RED - add presentation tests for billing account endpoints and error cases.
8. GREEN - expose the FastAPI routes and DTOs.
9. RED - add frontend contract/use-case tests for billing dashboard and management flows.
10. GREEN - implement the frontend adapters, use cases, and profile billing UI.
11. RED - add Playwright coverage for the complete billing area.
12. RUN - validate the touched backend and frontend areas with focused test commands and lint/type checks.

## Expected files

```text
backend-api/app/domain/billing/
backend-api/app/application/billing/
backend-api/app/infrastructure/persistence/
backend-api/app/presentation/api/v1/
backend-api/tests/domain/billing/
backend-api/tests/application/billing/
backend-api/tests/infrastructure/
backend-api/tests/presentation/
frontend-app/src/domain/
frontend-app/src/application/
frontend-app/src/infrastructure/
frontend-app/src/presentation/
frontend-app/src/app/(candidate)/profile/
frontend-app/src/app/(candidate)/settings/
frontend-app/src/app/(candidate)/billing/
frontend-app/src/shared/api/
frontend-app/src/*/*.test.ts
frontend-app/tests/e2e/
docs/superpowers/specs/stripe-subscription-management.md
docs/superpowers/plans/2026-06-18-stripe-subscription-management.md
docs/api/stripe-subscription-management.md
```

## Complexity

| Area | Effort | Notes |
|---|---|---|
| Domain | M | Billing profile and payment-method snapshots |
| Application | L | Overview + plan-change orchestration |
| Infrastructure | M | Persistence + migration + Stripe mapping |
| Presentation | M | REST contracts and error mapping |
| Frontend | L | Profile billing area + flow orchestration |
| Tests | L | Layered coverage + Playwright |
| Total | L | Broad billing management surface |

