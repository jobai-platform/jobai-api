# JOB-101 - Reset Password And Resend Plan

**Status:** Implemented
**Date:** 2026-06-07
**Owner:** Forge
**Related ticket:** JOB-101
**Design:** `docs/superpowers/specs/2026-06-07-job101-reset-password-resend-design.md`

## Objective

Implement the reset-password application flow and Resend infrastructure adapter without weakening the 30-minute TTL,
single-use protection, secret isolation, or hexagonal layer boundaries.

## TDD Execution Plan

1. [x] Retrieve JOB-101 and create its Linear branch from `origin/develop`.
2. [x] Audit JOB-99/JOB-100 implementation, Auth ports, repositories, DI, configuration, and ADR-0002.
3. [x] Write the JOB-101 design, implementation plan, and Resend integration guide.
4. [x] RED - extend domain token tests for parsing/reconstruction of `value.signature`.
5. [x] GREEN - add the minimal domain reconstruction method.
6. [x] RED - add application tests for token persistence in `ForgotPasswordUseCase`.
7. [x] RED - add `ResetPasswordUseCase` tests:
   - valid token changes the password and consumes the token;
   - expired token raises `ValueError`;
   - tampered token raises `ValueError`;
   - unknown token raises `ValueError`;
   - second use raises `ValueError`;
   - failed concurrent claim raises `ValueError`;
   - invalid flow does not change the password.
8. [x] GREEN - add `PasswordResetTokenRepository` and `PasswordResetTokenRecord` to application ports.
9. [x] GREEN - update `ForgotPasswordUseCase` and implement `ResetPasswordUseCase`.
10. [x] REFACTOR - move shared token hashing and public invalid-token error handling into focused private helpers.
11. [x] RED - add SQLAlchemy repository integration tests, including conditional single-use consumption.
12. [x] GREEN - add ORM model, Alembic migration, and SQLAlchemy repository.
13. [x] RED - add Resend adapter unit tests with `httpx.MockTransport`.
14. [x] GREEN - implement `ResendEmailSender` and environment-aware credential resolution.
15. [x] RED/GREEN - add the opt-in real Resend sandbox integration test.
16. [x] Wire repositories, password hasher, Resend adapter, and use cases in `app/core/dependency.py`.
17. [x] Update `.env.example` and any deployment configuration required by the new variables.
18. [x] Run focused tests, layer suites, migration smoke test, and full non-integration suite.
19. [x] Run the real sandbox test when credentials are available; otherwise document the verified skip.
20. [ ] Commit, push, open a GitHub PR, and update JOB-101 with validation evidence.

## Files Expected To Change

```text
app/domain/users/password_reset_token.py
app/application/auth/ports.py
app/application/auth/use_cases.py
app/infrastructure/email/__init__.py
app/infrastructure/email/resend_gateway.py
app/infrastructure/persistence/models/password_reset_token.py
app/infrastructure/persistence/repositories/password_reset_token_sqlalchemy.py
app/core/config.py
app/core/dependency.py
migrations/versions/<revision>_add_password_reset_tokens.py
.env.example
tests/domain/users/test_password_reset_token.py
tests/application/auth/test_forgot_password_use_case.py
tests/application/auth/test_reset_password_use_case.py
tests/fakes/auth/in_memory_password_reset_token_repo.py
tests/infrastructure/email/test_resend_gateway.py
tests/infrastructure/email/test_resend_gateway_integration.py
tests/infrastructure/persistence/test_password_reset_token_repository.py
```

## Decisions

| Decision | Reason |
|---|---|
| Persist a SHA-256 hash, not the raw signed token | A database leak must not expose active reset links |
| Keep `created_at` server-side | Signature and TTL validation must not trust client timestamps |
| Use a conditional consume update | Prevents concurrent replay of a single token |
| Claim and password update in one transaction | Prevent partial persistence while retaining concurrent replay protection |
| Reuse `PasswordHasher` and `UserRepository` ports | Avoid duplicate security and persistence abstractions |
| Use async `httpx` directly | Already installed and keeps the adapter small |
| Guard the real Resend test with env variables | Default tests remain offline and deterministic |
| Keep presentation out of scope | JOB-101 targets application and infrastructure only |

## Complexity

| Area | Effort | Notes |
|---|---|---|
| Domain | S | Signed-token parsing and reconstruction |
| Application | M | Persistence port, forgot flow update, reset orchestration |
| Infrastructure | M | Model, migration, repository, conditional consume |
| Resend | M | Config resolution, adapter, network/error tests |
| Presentation | XS | No change |
| Tests | L | Domain, application, DB integration, HTTP adapter, live sandbox |
| **Total** | **L** | Security-sensitive cross-layer change |

## Validation Matrix

```bash
poetry run pytest tests/domain/users/test_password_reset_token.py -q
poetry run pytest tests/application/auth/test_forgot_password_use_case.py -q
poetry run pytest tests/application/auth/test_reset_password_use_case.py -q
poetry run pytest tests/infrastructure/email/test_resend_gateway.py -q
poetry run pytest tests/infrastructure/persistence/test_password_reset_token_repository.py -q
poetry run pytest tests/infrastructure/test_migrations_smoke.py -q
poetry run pytest tests/domain/ tests/application/ -q
poetry run pytest tests/ -q
poetry run ruff check <touched-files>
poetry run mypy <touched-app-files>
```

Live sandbox:

```bash
RESEND_API_KEY_SANDBOX=... \
RESEND_SANDBOX_RECIPIENT=account-owner@example.com \
poetry run pytest -m integration tests/infrastructure/email/test_resend_gateway_integration.py -q
```

## Completion Criteria

- [x] Every reset token is persisted by hash before email delivery.
- [x] A valid token updates the Candidate password exactly once.
- [x] Invalid, expired, tampered, unknown, and consumed tokens raise `ValueError`.
- [x] Concurrent reuse is blocked by infrastructure persistence.
- [x] No raw reset token is stored in PostgreSQL.
- [x] Resend sandbox/prod key selection satisfies EC23.
- [x] Adapter unit tests do not use the network.
- [x] Real sandbox test is executable and either passes or is explicitly skipped for missing credentials.
- [x] Full non-integration suite passes.
- [ ] Feature branch is pushed and reviewed through a GitHub PR.
