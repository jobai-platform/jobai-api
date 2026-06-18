# Stripe Billing History API Plan

**Status:** Planned
**Date:** 2026-06-18
**Owner:** Forge
**Design:** `docs/superpowers/specs/stripe-billing-history.md`
**Audit:** `AUDIT_STRIPE_BILLING_HISTORY.md`

## Objective

Complete the Stripe billing history API on top of the existing invoice entity, invoice model, repository, and billing
history DTO.

## Current Baseline

Already present in the repo:

- `app/domain/billing/entities/invoice.py`
- `app/infrastructure/persistence/models/invoice.py`
- `app/infrastructure/persistence/repositories/invoice_sqlalchemy.py`
- `app/application/billing/dto.py` with `BillingHistoryResult`
- `tests/domain/billing/test_invoice.py`
- `tests/infrastructure/test_invoice_model.py`
- `tests/application/billing/test_billing_history_use_case.py`
- `tests/presentation/test_stripe_billing_history_routes.py`

Still missing or incomplete:

- `GetBillingHistoryUseCase`
- billing history FastAPI route
- response schema for paginated invoice history
- dependency wiring in `app/core/dependency.py`
- consumer-facing API documentation
- invoice webhook ingestion if invoice records need to be created from Stripe events

## TDD Plan

1. RED - confirm the application use case tests fail because `GetBillingHistoryUseCase` is absent.
2. RED - confirm the presentation route tests fail because `/api/v1/stripe/billing-history` is absent.
3. GREEN - implement `GetBillingHistoryUseCase` using the existing invoice repository and user repository.
4. GREEN - add the paginated response schema for invoice history.
5. GREEN - add the `GET /api/v1/stripe/billing-history` route.
6. GREEN - wire the new use case into `app/core/dependency.py`.
7. REFACTOR - keep the route thin and the use case responsible for pagination semantics.
8. GREEN - align invoice webhook persistence if the history endpoint depends on automatic Stripe ingestion.
9. GREEN - add or update API docs under `docs/api/`.
10. RUN - execute the focused backend tests for domain, application, infrastructure, and presentation.
11. RUN - execute Ruff, Black, and mypy on touched backend files.

## Expected Files

```text
app/application/billing/use_cases.py
app/core/dependency.py
app/presentation/api/v1/schemas/billing.py
app/presentation/api/v1/stripe_routes.py
app/application/billing/dto.py
tests/application/billing/test_billing_history_use_case.py
tests/presentation/test_stripe_billing_history_routes.py
docs/api/stripe-billing-history.md
docs/superpowers/specs/stripe-billing-history.md
docs/superpowers/plans/2026-06-18-stripe-billing-history.md
```

## Complexity

| Area | Effort | Notes |
|---|---|---|
| Application | M | Use case orchestration and pagination semantics |
| Presentation | M | New schema and route contract |
| Infrastructure | XS | Reuse existing invoice persistence |
| Tests | M | Route, pagination, and isolation coverage |
| Documentation | S | Spec, plan, and API contract |
| Total | M | Mostly wiring on top of existing invoice primitives |

