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
| `created_at` | `datetime` | timezone-aware, defaults to UTC now |
| `consumed_at` | `datetime | None` | timezone-aware when present |

Behavior:

1. `expires_at` is always `created_at + 30 minutes`.
2. `is_expired(now=created_at + 30min)` returns `True`.
3. `is_expired(now=created_at + 31min)` returns `True`.
4. `consume()` sets `consumed_at` when the token is not consumed and not expired.
5. A second `consume()` raises `ValueError`.
6. Consuming an expired token raises `ValueError`.

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
- Domain module has zero framework imports.
- Domain tests cover TTL, consumption, expiration, and invalid construction.

## Validation

```bash
poetry run pytest tests/domain/users/test_password_reset_token.py -q
poetry run pytest tests/domain/ -q
```

Validated on 2026-06-05:

- focused password reset token tests: `9 passed`.
- focused domain/application compatibility tests: `11 passed`.
- domain test suite: `115 passed`.
- ruff on touched Python files: passed.
