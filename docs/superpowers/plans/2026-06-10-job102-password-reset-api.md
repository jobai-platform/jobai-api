# JOB-102 - Password Reset API Plan

**Status:** Implemented
**Date:** 2026-06-10
**Owner:** Forge
**Design:** `docs/superpowers/specs/2026-06-10-job102-password-reset-api-design.md`

## Objective

Add the forgot-password and reset-password HTTP endpoints on top of the completed JOB-99 to JOB-101 flow.

## TDD Plan

1. [x] Fetch `origin/develop` and verify JOB-101 is merged.
2. [x] Create the JOB-102 feature branch.
3. [x] RED - add isolated presentation tests for both endpoints.
4. [x] GREEN - add forgot/reset request DTOs.
5. [x] REFACTOR - share the existing D4 password validator with reset-password.
6. [x] GREEN - expose typed dependency aliases for both use cases.
7. [x] GREEN - add both FastAPI routes.
8. [x] GREEN - map reset token `ValueError` to a uniform `400`.
9. [x] Add design, plan, and API integration documentation.
10. [x] Run focused tests and presentation regression tests.
11. [x] Run Ruff, Black check, and mypy on touched application files.
12. [x] Commit, push, and create GitHub PR #52 targeting `develop`.

## Expected Files

```text
app/core/dependency.py
app/presentation/api/v1/auth_routes.py
app/presentation/api/v1/schemas/auth.py
tests/presentation/api/v1/test_auth_password_routes.py
docs/superpowers/specs/2026-06-10-job102-password-reset-api-design.md
docs/superpowers/plans/2026-06-10-job102-password-reset-api.md
docs/api/password-reset.md
```

## Complexity

| Area | Effort | Notes |
|---|---|---|
| Domain | XS | No change |
| Application | XS | Existing use cases |
| Infrastructure | XS | No change |
| Presentation | M | DTOs, routes, error mapping |
| Tests | M | Isolated HTTP contract tests |
| Documentation | S | API consumer guide |
| **Total** | **M** | Security-sensitive public API surface |
