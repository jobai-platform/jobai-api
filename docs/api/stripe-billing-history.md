# Stripe Billing History API

## Endpoint

`GET /api/v1/stripe/billing-history`

Returns the current connected user's Stripe invoice history.

## Authentication

Bearer token for the connected user.

## Success Response

`200 OK`

```json
{
  "items": [
    {
      "date": "2026-06-18T12:00:00Z",
      "amount": 2900,
      "currency": "eur",
      "status": "paid",
      "stripe_invoice_id": "in_123",
      "stripe_payment_id": "pi_123",
      "description": "Pro plan",
      "hosted_invoice_url": "https://stripe.test/invoice"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0,
  "has_more": false
}
```

Invoices are returned in reverse chronological order. The API only exposes invoices linked to the authenticated user.

## Empty History

`200 OK`

```json
{
  "items": [],
  "total": 0,
  "limit": 50,
  "offset": 0,
  "has_more": false
}
```

## Returned Fields

| Field | Description |
|---|---|
| `items` | Paginated list of invoices |
| `total` | Total number of invoices for the connected user |
| `limit` | Page size requested by the client |
| `offset` | Number of invoices skipped |
| `has_more` | Whether another page exists |
| `date` | Invoice issue date |
| `amount` | Raw amount in the smallest currency unit |
| `currency` | Currency code from Stripe |
| `status` | Invoice payment status |
| `stripe_invoice_id` | Stripe invoice identifier |
| `stripe_payment_id` | Stripe payment identifier |
| `description` | Human-readable invoice description |
| `hosted_invoice_url` | Stripe-hosted PDF or invoice page URL when available |

## Notes For Consumers

- Treat `amount` as cents or the smallest unit for the returned currency.
- Treat `date` as an ISO-8601 timestamp in UTC.
- Use `total`, `limit`, `offset`, and `has_more` for pagination controls.
- Do not expect invoice rows from other users, even if those rows share a Stripe customer prefix.
