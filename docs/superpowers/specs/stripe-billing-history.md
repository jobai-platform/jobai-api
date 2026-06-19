# Stripe Billing History API

**Bounded Context:** billing
**Status:** Approved — align-backend requis
**Date:** 2026-06-18
**Owner:** Forge
**Sources:** `SPEC_STRIPE_BILLING_HISTORY.md`, `AUDIT_STRIPE_BILLING_HISTORY.md`

## Goal

Expose the authenticated user's Stripe billing history through a stable backend contract. The API must return raw
Stripe billing data that is already persisted locally, without inventing or deriving new billing concepts in the
presentation layer.

## Current Baseline

- `Invoice` domain entity already exists.
- `InvoiceModel` persistence model already exists.
- `InvoiceSQLAlchemyRepository` already exists.
- `BillingHistoryResult` DTO already exists.
- Missing pieces are the application use case, the API schema, the FastAPI route, and the dependency wiring.
- Stripe invoice webhook handling is still incomplete and must be aligned if invoice records are to be populated
  automatically.

## Scope

In scope:

- `GET /api/v1/stripe/billing-history`;
- authenticated access only;
- per-user isolation through the connected user and its Stripe customer ID;
- paginated invoice history;
- stable response envelope with metadata;
- API documentation for consumers;
- webhook-driven persistence of invoice events if required by the backend flow.

Out of scope:

- modifying or canceling invoices from this endpoint;
- refunds workflows;
- tax reporting;
- currency conversion;
- frontend implementation.

## User Story

> As a Candidate or BusinessAccount,
> I want to view my Stripe billing history,
> So that I can track payments, download invoices, and understand past charges.

## HTTP Contract

### Endpoint

`GET /api/v1/stripe/billing-history`

Authentication: connected user.

### Success response

`200 OK`

Response envelope:

```json
{
  "items": [],
  "total": 0,
  "limit": 50,
  "offset": 0,
  "has_more": false
}
```

Each item represents one persisted Stripe invoice and exposes:

- `date`
- `amount`
- `currency`
- `status`
- `stripe_invoice_id`
- `stripe_payment_id`
- `description`
- `hosted_invoice_url`

The backend must return invoices sorted by most recent first.

### Empty history

If the connected user has no billing history, the API still returns `200 OK` with:

```json
{
  "items": [],
  "total": 0,
  "limit": 50,
  "offset": 0,
  "has_more": false
}
```

### Not found

If the authenticated user record cannot be resolved, the use case may raise a `404` domain error. The route should
preserve the existing error contract used across the backend.

## Acceptance Criteria

### Scenario 1 - Nominal path
- Given a connected user with invoice history
- When the user calls `GET /api/v1/stripe/billing-history`
- Then the API returns `200 OK`
- And the response contains a paginated list of invoices
- And the response contains pagination metadata

### Scenario 2 - Empty history
- Given a connected user with no invoice history
- When the user calls `GET /api/v1/stripe/billing-history`
- Then the API returns `200 OK`
- And `items` is an empty list
- And `total` is `0`
- And `has_more` is `false`

### Scenario 3 - Pagination
- Given a connected user with more invoices than the requested limit
- When the user calls `GET /api/v1/stripe/billing-history?limit=1&offset=0`
- Then the API returns the first page only
- And the envelope reflects `total`, `limit`, `offset`, and `has_more`

### Scenario 4 - Isolation
- Given two different connected users
- When user A calls the endpoint
- Then only user A's invoices are returned
- And user B's invoices are never exposed

## Domain Impact

- `Invoice` is the core entity reused by the billing history flow.
- `BillingHistoryResult` is the application DTO for pagination metadata.
- No new billing aggregate is required for v1.

## Architecture Impact

| Layer | Change |
|---|---|
| Domain | Reuse existing `Invoice` entity |
| Application | Add `GetBillingHistoryUseCase` and align webhook invoice persistence if needed |
| Infrastructure | Reuse `InvoiceModel` and `InvoiceSQLAlchemyRepository` |
| Presentation | Add `InvoiceRead` and a paginated response schema, then expose the route |

## Open Questions

- Should invoice webhook ingestion be strict and fail on partial Stripe payloads, or should it persist what is available?
- Should the endpoint use `limit/offset` only, or also expose `page/size` aliases for frontend convenience?
- Should cancellation and refund events be represented in the same invoice history stream or stay out of v1?

## Tickets Proposed v1.0

Backend:

- [ ] [Feature][billing][High] Create `GetBillingHistoryUseCase` on top of the invoice repository
- [ ] [Feature][billing][High] Add the paginated billing history route and response schema
- [ ] [Feature][billing][High] Wire the billing history use case in dependency injection
- [ ] [Feature][billing][Medium] Align Stripe webhook invoice persistence if invoice events must populate history automatically
- [ ] [Feature][billing][Medium] Add consumer-facing API documentation for billing history

## Validation Notes

- Keep datetime serialization ISO-8601 compatible.
- Preserve user isolation through the authenticated identity and Stripe customer ID.
- Keep the invoice list ordered by most recent invoice first.
