# JOB-99 — PasswordResetToken Domain Plan

**Status:** Implemented
**Date:** 2026-06-05
**Owner:** Forge
**Related ticket:** JOB-99

## Objective

Create the domain-level password reset token object for the Sprint 2 Forgot/Reset Password flow while preserving strict
hexagonal boundaries and TDD-first delivery.

## Tasks

1. [x] Retrieve the Linear branch name before implementation.
2. [x] Create `feature/job-99-domain-passwordresettoken-value-object-ttl-30min-usage` from `origin/develop`.
3. [x] Review existing auth/domain token patterns and JOB-100 docs.
4. [x] Add domain tests first in `tests/domain/users/test_password_reset_token.py`.
5. [x] Implement `app/domain/users/password_reset_token.py`.
6. [x] Replace the application-local token class with the domain token.
7. [x] Validate focused domain tests.
8. [x] Validate full domain suite.
9. [x] Commit, push, and open PR.

## Decisions

| Decision | Reason |
|---|---|
| Keep TTL as `PASSWORD_RESET_TOKEN_TTL` | Makes the 30-minute invariant explicit in the domain |
| Treat `now` as injectable | Keeps tests deterministic without framework or time mocks |
| Raise `ValueError` for consumed/expired tokens | Matches the ticket's domain invariant requirement |
| Reuse the domain type from JOB-100 code | Avoids duplicate password reset token definitions |

## Test Plan

```bash
poetry run pytest tests/domain/users/test_password_reset_token.py -q
poetry run pytest tests/application/auth/test_forgot_password_use_case.py -q
poetry run pytest tests/domain/ -q
```

## Completion Criteria

- [x] EC7: a second `consume()` raises `ValueError`.
- [x] EC8: `t+31min` returns expired.
- [x] Token generation returns a non-empty URL-safe value.
- [x] Domain implementation imports stdlib only.
- [x] Full domain tests pass.
