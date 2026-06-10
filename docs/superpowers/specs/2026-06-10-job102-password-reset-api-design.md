# JOB-102 - Password Reset API Design

**Status:** Implemented
**Date:** 2026-06-10
**Owner:** Forge
**Related tickets:** JOB-99, JOB-100, JOB-101, JOB-102

## Goal

Expose the existing forgot-password and reset-password application use cases through FastAPI without moving business
logic into the presentation layer.

## Scope

In scope:

- `POST /api/v1/auth/password/forgot`;
- `POST /api/v1/auth/password/reset`;
- Pydantic request validation;
- server-owned reset URL construction;
- uniform invalid-token error mapping;
- presentation tests and API documentation.

Out of scope:

- domain, application, persistence, Resend, or migration changes;
- frontend screens;
- email delivery retries or webhooks;
- changes to the password policy.

## HTTP Contracts

### Forgot Password

Request:

```json
{"email": "candidate@example.com"}
```

Response: `204 No Content`.

The response is identical for existing and unknown Candidate accounts. The client cannot provide the reset URL. The
backend derives it from `FRONTEND_ORIGIN`:

```text
{FRONTEND_ORIGIN}/auth/password/reset
```

The application use case appends the signed token as a query parameter.

### Reset Password

Request:

```json
{
  "token": "<signed-token>",
  "new_password": "SecurePass1!"
}
```

Success response: `204 No Content`.

Invalid, expired, unknown, tampered, or consumed tokens return:

```json
{
  "code": "bad_request",
  "detail": "Invalid or expired password reset token"
}
```

with status `400 Bad Request`.

The new password uses the existing D4 policy: at least 12 characters, one uppercase letter, one digit, and one special
character. Request validation failures return `422 validation_error`.

## Architecture

| Layer | Change |
|---|---|
| Domain | None |
| Application | Reuse `ForgotPasswordUseCase` and `ResetPasswordUseCase` |
| Infrastructure | None |
| Presentation | DTOs, dependency aliases, routes, error mapping |
| Migration | None |

The routes only validate transport data, derive the trusted frontend URL, invoke a use case, and map the legacy
`ValueError` reset contract to HTTP.

## Security

- Forgot-password responses do not expose account existence.
- Reset URLs are derived from server configuration, preventing client-controlled reset links.
- Forgot-password requests are limited to five requests per minute per limiter key.
- All token rejection causes share one public error.
- Password-reset tokens remain single-use and expire after 30 minutes through JOB-99/JOB-101 behavior.

## Acceptance Criteria

Given any syntactically valid email,
When forgot-password is requested,
Then the API returns `204`,
And the application use case receives the server-configured reset URL.

Given an invalid email,
When forgot-password is requested,
Then the API returns `422`,
And the use case is not called.

Given a valid token and strong password,
When reset-password is requested,
Then the API returns `204`.

Given any rejected token,
When reset-password is requested,
Then the API returns the uniform `400` response.

Given a weak password,
When reset-password is requested,
Then the API returns `422`,
And the use case is not called.

