# JOB-100 — Forgot Password Use Case Plan

**Status:** Implemented
**Date:** 2026-06-05
**Owner:** Forge
**Related ticket:** JOB-100

## Objective

Add the forgot-password application use case and email delivery port while preserving hexagonal boundaries and the
anti-enumeration behavior required by the frontend flow.

## Tasks

1. [x] Create JOB-100 branch from `develop`.
2. [x] Audit existing Auth use cases, ports, fake repositories, and ADR-0002.
3. [x] Add application tests first in `tests/application/auth/test_forgot_password_use_case.py`.
4. [x] Add `IEmailGateway` to `app/application/auth/ports.py`.
5. [x] Add `PasswordResetToken` and `ForgotPasswordUseCase` to `app/application/auth/use_cases.py`.
6. [x] Keep Resend adapter and presentation endpoint out of scope.
7. [x] Validate focused application tests and full `tests/application/` suite.
8. [ ] Commit, push, and open PR.

## Decisions

| Decision | Reason |
|---|---|
| Add `IEmailGateway` in application auth ports | ADR-0002 requires Resend to be swappable behind a port |
| Keep use case application-only | Ticket scope explicitly targets application layer |
| Return `None` for both existing and unknown users | Supports anti-enumeration and presentation `204` mapping |
| Generate token in use case | Ticket requires token generation and email delivery |
| Do not persist token yet | Reset validation/persistence is not part of JOB-100 |

## Test Plan

```bash
poetry run pytest tests/application/auth/test_forgot_password_use_case.py -q
poetry run pytest tests/application/ -q
```

## Completion Criteria

- [x] Existing-user test sends exactly one fake email.
- [x] Unknown-user test sends no email and raises no error.
- [x] `IEmailGateway` has `send_password_reset(email, token, reset_url)`.
- [x] Application tests pass.
