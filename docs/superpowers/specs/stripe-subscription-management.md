# Stripe Subscription Management

**Bounded Context:** billing
**Persona(s):** Thomas, Marie, Carlos, Isabelle, Sarah
**Status:** Approved — ticketing ready
**Date:** 2026-06-18
**Version:** v1.0
**Sources:** `SPEC_STRIPE_SUBSCRIPTION_SUMMARY.md`, `AUDIT_STRIPE_SUBSCRIPTION_SUMMARY.md`, `SPEC_STRIPE_BILLING_HISTORY.md`, `AUDIT_STRIPE_BILLING_HISTORY.md`

## Overview

Expose a complete billing area for Sovrum users so they can inspect and control their Stripe subscription, billing
address, payment method summary, and invoice history from their account profile. The backend must keep Stripe as the
source of truth for sensitive payment data and persist only the minimal local snapshot required for display and
workflow orchestration.

This scope builds on the already implemented subscription summary and billing history endpoints and extends the billing
context toward a self-service account management experience.

## User Story

> As a Candidate or BusinessAccount,
> I want to manage my subscription and billing details from my Sovrum account,
> So that I can see what I am paying, update billing information, change plans safely, and handle payments without
> support.

## Acceptance Criteria

### Scenario 1 — Nominal billing dashboard
- Given a connected user with a Stripe customer and at least one active billing record
- When the user opens the billing area in their profile
- Then the UI can display the current subscription summary
- And the billing address snapshot
- And the masked payment method summary
- And the invoice history list

### Scenario 2 — Plan change request
- Given a connected user on a paid plan
- When the user requests a plan change to another paid plan
- Then the change is scheduled for the end of the current billing period
- And the current subscription remains active until renewal

### Scenario 3 — Freemium upgrade
- Given a connected user on the Freemium plan
- When the user upgrades to a paid plan
- Then the change is applied immediately
- And the billing summary is refreshed from Stripe

### Scenario 4 — Billing details edge cases
- Given a connected user without saved invoices or without a saved payment method summary
- When the user opens the billing area
- Then the UI still renders successfully
- And empty states are shown for missing collections
- And no sensitive card data is exposed

## Out of Scope v1

- Refund workflows
- Tax export / invoice export automation
- Multiple active subscriptions per account
- Coupon and promotion management
- Manual storage of full card numbers or CVC
- Enterprise multi-user billing administration

## Hypotheses to validate

- [ ] Stripe Customer Portal will be used for card/payment-method management instead of a fully custom payment form.
- [ ] Local persistence will store only billing address and masked payment method snapshot data, never raw card data.
- [ ] The temporary `stripe_customer_id` exposure in the user domain will remain until the billing-context decoupling ticket
  is completed.
- [ ] The plan-change flow can be implemented as a pending change for paid plans and as an immediate upgrade from
  Freemium.

## Domain Impact

- Entities: `BillingProfile`, `BillingAddress`, `PaymentMethodSnapshot`, `SubscriptionChangeRequest`
- Invariants:
  - card PAN and CVC are never persisted locally;
  - billing data is user-scoped;
  - paid-plan changes are scheduled for renewal unless the current plan is Freemium;
  - Stripe remains the source of truth for sensitive payment details.

## API Contract

- `GET /api/v1/stripe/subscriptions/me` - implemented
- `GET /api/v1/stripe/billing-history` - implemented
- `GET /api/v1/stripe/billing-profile` - to implement
- `PUT /api/v1/stripe/billing-profile` - to implement
- `POST /api/v1/stripe/subscriptions/me/change-plan` - to implement
- `POST /api/v1/stripe/subscriptions/me/cancel` - to implement
- `POST /api/v1/stripe/subscriptions/me/reactivate` - to implement
- `POST /api/v1/stripe/customer-portal/session` - to implement

## Tickets proposed v1.0

Backend:
- [ ] Domain — Introduce billing profile and payment method snapshot entities
- [ ] Infrastructure — Persist billing profile, address, and masked payment method snapshot
- [ ] Application — Build billing account overview use case
- [ ] Application — Add billing profile update and Stripe Customer Portal session use cases
- [ ] Application — Add plan change, cancellation, and reactivation workflows
- [ ] Presentation — Expose billing account routes and DTOs
- [ ] QA — Cover the full billing area with domain, application, infrastructure, and presentation tests

Frontend:
- [ ] Entities + Interface — Define billing profile, payment method, and subscription management contracts
- [ ] Use Cases — Orchestrate the billing dashboard and management flows
- [ ] HTTP Adapter — Connect to billing summary, profile, history, plan-change, and portal endpoints
- [ ] UI — Build the billing section in the candidate profile page
- [ ] UI — Add plan-change, billing-address, and payment-method controls
- [ ] QA — Cover the billing area with unit, integration, and Playwright tests

## Validation notes

- Preserve the existing summary and billing history contracts.
- Keep all payment data masked or tokenized.
- Surface billing controls in the candidate profile area without duplicating authentication or session logic.
