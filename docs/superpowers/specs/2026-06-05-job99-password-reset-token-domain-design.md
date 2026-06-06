# JOB-99 — PasswordResetToken Domain Value Object

**Status:** Implemented
**Date:** 2026-06-05
**Owner:** Forge
**Related ticket:** JOB-99

## Goal

Add the domain object that represents a password reset token for the Forgot/Reset Password flow.

The object must enforce a strict 30-minute TTL and single-use consumption without importing any framework or
infrastructure dependency.

## Scope

In scope:

- add `app/domain/users/password_reset_token.py`;
- generate high-entropy reset token values;
- sign token values and creation timestamps with HMAC-SHA256;
- expose `expires_at`, `is_expired()`, `is_consumed`, and `consume()`;
- reject empty token values and naive datetimes;
- use the domain object from the existing forgot-password application use case.

Out of scope:

- token persistence;
- reset-password command/use case;
- email provider adapter;
- presentation endpoint.

## Domain Contract

`PasswordResetToken` fields:

| Field | Type | Rule |
|---|---|---|
| `value` | `str` | non-empty, generated with high entropy |
| `signature` | `str` | non-empty HMAC-SHA256 signature of `value` and `created_at` |
| `created_at` | `datetime` | timezone-aware, defaults to UTC now |
| `consumed_at` | `datetime | None` | timezone-aware when present |

Behavior:

1. `expires_at` is always `created_at + 30 minutes`.
2. `is_expired(now=created_at + 30min)` returns `True`.
3. `is_expired(now=created_at + 31min)` returns `True`.
4. `has_valid_signature()` uses constant-time comparison and rejects a changed value, timestamp, or key.
5. `consume()` sets `consumed_at` when the signature is valid and the token is not consumed or expired.
6. A second `consume()` raises `ValueError`.
7. Consuming an expired token raises `ValueError`.
8. Consuming a token with an invalid signature raises `ValueError`.

## Layer Mapping

| Layer | Change |
|---|---|
| Domain | Add `PasswordResetToken` in `app/domain/users/` |
| Application | Reuse the domain token in `ForgotPasswordUseCase` |
| Infrastructure | No change |
| Presentation | No change |

## Acceptance Criteria

- EC7: second usage raises `ValueError`.
- EC8: `t+31min` makes `is_expired()` return `True`.
- A modified token value, creation timestamp, or signing key invalidates the signature.
- Domain module has zero framework imports.
- Domain tests cover TTL, consumption, expiration, and invalid construction.

## Validation

```bash
poetry run pytest tests/domain/users/test_password_reset_token.py -q
poetry run pytest tests/domain/ -q
```

Validated on 2026-06-06 after QA correction:

- focused domain/application compatibility tests: `18 passed`.
- domain and application test suites: `233 passed`.
- ruff on touched Python files: passed.
