# JOB-101 - ResetPasswordUseCase + ResendEmailSender

**Status:** Implemented
**Date:** 2026-06-07
**Owner:** Forge
**Related tickets:** JOB-99, JOB-100, JOB-101
**Related ADR:** `docs/adr/adr-0002-email-provider.md`

## Goal

Complete the backend password-reset flow by:

- persisting password-reset token state;
- validating the signed token, its 30-minute TTL, and single-use invariant;
- replacing the Candidate password with a newly hashed password;
- delivering forgot-password emails through a Resend infrastructure adapter.

## Scope

In scope:

- `ResetPasswordUseCase` in the Auth application layer;
- a `PasswordResetTokenRepository` application port;
- persistence model, SQLAlchemy adapter, and Alembic migration for token state;
- updating `ForgotPasswordUseCase` so generated tokens are persisted before email delivery;
- `ResendEmailSender` implementing `IEmailGateway`;
- environment-aware Resend credential selection;
- application, infrastructure, and migration tests;
- a real Resend sandbox integration test guarded by environment variables.

Out of scope:

- FastAPI forgot/reset-password routes and DTOs;
- frontend screens and form validation;
- password-strength policy changes;
- email templates managed in the Resend dashboard;
- background queues, retries, and delivery webhooks.

## Existing Constraint

`PasswordResetToken.signed_value` currently contains `value.signature`, while the signature also covers `created_at`.
The timestamp is intentionally not trusted from client input. The persistence record therefore stores `created_at`, and
the use case reconstructs the domain token from:

- the untrusted `value.signature` received from the client;
- the trusted `created_at` and `consumed_at` loaded by token hash from PostgreSQL.

This avoids exposing database identifiers or trusting a client-provided timestamp.

## Domain And Layer Mapping

| Layer | Change |
|---|---|
| Domain | Add safe reconstruction/parsing of a signed `PasswordResetToken` |
| Application | Add token repository port, persist tokens in `ForgotPasswordUseCase`, add `ResetPasswordUseCase` |
| Infrastructure | Add SQLAlchemy token repository, ORM model, migration, and Resend email adapter |
| Presentation | No change in JOB-101 |

## Persistence Model

Table: `password_reset_tokens`

| Column | Type | Rule |
|---|---|---|
| `token_hash` | `VARCHAR(64)` | Primary key; SHA-256 of the complete signed token |
| `candidate_id` | `UUID` | Foreign key to Candidate/User, indexed |
| `created_at` | timezone-aware timestamp | Source of truth for TTL and signature validation |
| `consumed_at` | nullable timezone-aware timestamp | Non-null after successful claim |

The raw token and signature are not stored. A database leak must not expose immediately usable reset links.

Expired rows may be cleaned up in a later maintenance ticket. Cleanup is not required for correctness because every read
still enforces the domain TTL.

## Application Ports

```text
PasswordResetTokenRepository
  save(candidate_id, token_hash, created_at) -> None
  find_by_token_hash(token_hash) -> PasswordResetTokenRecord | None
  consume_if_available(token_hash, consumed_at) -> bool
```

`consume_if_available` must use a conditional update where `consumed_at IS NULL`. Returning `False` represents an
already-consumed or missing token and closes concurrent replay attempts.

## Forgot Password Change

`ForgotPasswordUseCase` gains `PasswordResetTokenRepository`.

For an existing Candidate:

1. Generate the signed domain token.
2. Hash the complete signed value with SHA-256.
3. Persist `candidate_id`, token hash, and `created_at`.
4. Build the reset URL.
5. Send the email through `IEmailGateway`.

Unknown emails still return success without persisting or sending anything.

## Reset Password Contract

Input:

```text
signed_token: str
new_password: str
now: datetime | None
```

Output:

```text
None
```

Behavior:

1. Reject an empty or malformed signed token with `ValueError`.
2. Hash the complete signed token and load its persistence record.
3. Reject a missing record with `ValueError`.
4. Reconstruct `PasswordResetToken` from the signed value and trusted persisted timestamps.
5. Validate signature, expiration, and prior consumption through `PasswordResetToken.consume`.
6. Hash `new_password` through the `PasswordHasher` port.
7. Claim the token with `consume_if_available` in the request transaction.
8. Reject a failed claim with `ValueError` to prevent concurrent reuse.
9. Load the Candidate and replace `hashed_password` with `HashedPassword`.
10. Persist the Candidate through `UserRepository.update`.

The token claim and password update share the request-scoped database transaction. The repository flushes the claim,
then the Candidate update commits both changes together. An exception before commit rolls the transaction back.

## Error Policy

The ticket explicitly requires `ValueError` for invalid, expired, or consumed tokens. JOB-101 therefore keeps that
contract even though newer application use cases generally prefer `AppError` subclasses.

All invalid token cases use the same public message:

```text
Invalid or expired password reset token
```

This avoids exposing whether the token existed, was expired, had an invalid signature, or had already been consumed.

## Resend Adapter

`ResendEmailSender` lives in `app/infrastructure/email/resend_gateway.py` and uses the existing async `httpx`
dependency against `POST https://api.resend.com/emails`.

Configuration:

| Variable | Purpose |
|---|---|
| `RESEND_API_KEY_SANDBOX` | Credential selected outside production |
| `RESEND_API_KEY_PROD` | Credential selected when `APP_ENV=production` |
| `RESEND_API_KEY` | Backward-compatible fallback when the environment-specific key is absent |
| `RESEND_FROM_EMAIL` | Verified production sender; defaults to `JobAI <onboarding@resend.dev>` outside production |
| `RESEND_TIMEOUT` | HTTP timeout in seconds; default `10.0` |

Selection rule:

- production: `RESEND_API_KEY_PROD`, then `RESEND_API_KEY`;
- dev, develop, preview: `RESEND_API_KEY_SANDBOX`, then `RESEND_API_KEY`;
- no selected key: fail fast with `ValueError` during adapter construction.

The adapter sends both HTML and plain-text bodies. Non-2xx responses raise an infrastructure exception with status and
provider error details, but never include the API key.

## Resend Sandbox Test

The real network test is marked `integration` and runs only when both variables are present:

```text
RESEND_API_KEY_SANDBOX
RESEND_SANDBOX_RECIPIENT
```

The sender is `JobAI <onboarding@resend.dev>`. Resend restricts this testing domain to the email address associated with
the Resend account, so `RESEND_SANDBOX_RECIPIENT` must use that address.

The regular test suite remains deterministic and network-free. Unit tests inject `httpx.MockTransport`.

## Acceptance Criteria

Given a valid, unconsumed token younger than 30 minutes,
When `ResetPasswordUseCase.execute` runs,
Then the new password is hashed and persisted,
And the token is marked consumed.

Given an expired token,
When the reset is attempted,
Then `ValueError` is raised,
And the Candidate password is unchanged.

Given a token already consumed once,
When a second reset is attempted,
Then `ValueError` is raised,
And the Candidate password is unchanged.

Given a tampered or unknown token,
When the reset is attempted,
Then `ValueError` is raised without revealing the failure reason.

Given two concurrent attempts with the same valid token,
When both try to claim it,
Then only one conditional consume succeeds.

Given a non-production environment,
When `ResendEmailSender` is constructed,
Then it prefers `RESEND_API_KEY_SANDBOX`.

Given `APP_ENV=production`,
When `ResendEmailSender` is constructed,
Then it prefers `RESEND_API_KEY_PROD`.

## Validation

```bash
poetry run pytest tests/domain/users/test_password_reset_token.py -q
poetry run pytest tests/application/auth/test_reset_password_use_case.py -q
poetry run pytest tests/infrastructure/email/test_resend_gateway.py -q
poetry run pytest tests/infrastructure/persistence/test_password_reset_token_repository.py -q
poetry run pytest -m integration tests/infrastructure/email/test_resend_gateway_integration.py -q
poetry run pytest tests/ -q
```

Validated on 2026-06-07:

- focused JOB-101 tests: `38 passed`;
- domain and application suites: `245 passed`;
- full non-integration suite: `334 passed`, `112 deselected`;
- password-reset repository integration tests: `4 passed`;
- real Resend sandbox test: skipped because sandbox credentials were not configured;
- targeted Ruff checks: passed;
- Alembic migration upgraded PostgreSQL from `c4a9e8b3f012` to `e2f5b7719c31`.

The repository-wide integration suite has six unrelated pre-existing failures in authentication fixtures, shared rate
limiting state, and admin user role serialization. JOB-101 integration tests pass independently.
