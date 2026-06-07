# Resend Password Reset Integration

**Date:** 2026-06-07
**Owner:** Forge
**Related ticket:** JOB-101

## Purpose

JOB-101 uses Resend only for transactional password-reset emails through the application port `IEmailGateway`.
Application and domain code must never import Resend or read provider credentials.

## Environment Variables

```dotenv
# Selected outside production.
RESEND_API_KEY_SANDBOX=

# Selected only when APP_ENV=production.
RESEND_API_KEY_PROD=

# Optional backward-compatible fallback.
RESEND_API_KEY=

# Production must use a sender on a verified Resend domain.
RESEND_FROM_EMAIL=JobAI <onboarding@resend.dev>

# HTTP timeout in seconds.
RESEND_TIMEOUT=10.0

# Used only by the opt-in real integration test.
RESEND_SANDBOX_RECIPIENT=
```

## Credential Selection

| `APP_ENV` | First choice | Fallback |
|---|---|---|
| `production` | `RESEND_API_KEY_PROD` | `RESEND_API_KEY` |
| `dev`, `develop`, `preview` | `RESEND_API_KEY_SANDBOX` | `RESEND_API_KEY` |

The adapter fails during construction when no applicable key is configured. It must not silently send production email
with a sandbox credential or log any key.

## Sandbox Constraints

The default Resend testing sender is:

```text
JobAI <onboarding@resend.dev>
```

Resend permits the `resend.dev` testing domain to send only to the email address associated with the Resend account.
Set `RESEND_SANDBOX_RECIPIENT` to that address before running the live test.

## Test Commands

Offline adapter tests:

```bash
poetry run pytest tests/infrastructure/email/test_resend_gateway.py -q
```

Real sandbox call:

```bash
RESEND_API_KEY_SANDBOX=... \
RESEND_SANDBOX_RECIPIENT=account-owner@example.com \
poetry run pytest -m integration tests/infrastructure/email/test_resend_gateway_integration.py -q
```

The integration test skips when either required variable is absent. CI must not require an external Resend call unless
the pipeline explicitly supplies sandbox credentials.

## Request Contract

The adapter sends an authenticated `POST` request to:

```text
https://api.resend.com/emails
```

Required payload fields:

```json
{
  "from": "JobAI <onboarding@resend.dev>",
  "to": ["candidate@example.com"],
  "subject": "Reset your JobAI password",
  "html": "<p>...</p>",
  "text": "..."
}
```

Authentication:

```text
Authorization: Bearer <selected-api-key>
```

## Operational Behavior

- `2xx`: email accepted by Resend.
- `4xx`: configuration or request failure; raise an infrastructure error.
- `429`: rate limited; raise an infrastructure error. Retry policy is out of scope for JOB-101.
- `5xx`: provider failure; raise an infrastructure error.
- timeout/network failure: raise an infrastructure error while preserving the original exception as the cause.

Logs and exceptions may include the HTTP status and provider message. They must never contain the Authorization header,
API key, complete reset URL, or raw reset token.

## Production Checklist

1. Verify the JobAI sending domain in Resend.
2. Set `RESEND_FROM_EMAIL` to an address on that verified domain.
3. Store `RESEND_API_KEY_PROD` in the production secret manager.
4. Confirm `APP_ENV=production`.
5. Keep `RESEND_API_KEY_SANDBOX` out of production.
6. Send a controlled password-reset email and verify delivery before enabling the public route.
