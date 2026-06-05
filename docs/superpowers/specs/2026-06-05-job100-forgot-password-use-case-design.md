# JOB-100 — ForgotPasswordUseCase + IEmailGateway

**Status:** Implemented
**Date:** 2026-06-05
**Owner:** Forge
**Related ticket:** JOB-100
**Related ADR:** `docs/adr/adr-0002-email-provider.md`

## Goal

Add the application-layer forgot-password use case for the Auth bounded context.

The use case must be safe against account enumeration and expose email delivery through an application port so the
infrastructure adapter can use Resend later without coupling application code to Resend.

## Scope

In scope:

- add `IEmailGateway` to `app/application/auth/ports.py`;
- add `ForgotPasswordUseCase` to `app/application/auth/use_cases.py`;
- generate a `PasswordResetToken` value for existing users;
- send the password reset email through `IEmailGateway`;
- return success for both existing and unknown users;
- add application tests with a fake email gateway.

Out of scope for this ticket:

- Resend infrastructure adapter;
- presentation endpoint;
- token persistence and reset-password validation;
- frontend implementation, owned by Atlas.

## Domain And Layer Mapping

| Layer | Change |
|---|---|
| Domain | No entity change; `PasswordResetToken` is an application value for this use case |
| Application | Add email gateway port and forgot-password use case |
| Infrastructure | No adapter in this ticket; future Resend adapter implements the port |
| Presentation | No route in this ticket; future endpoint should map success to `204` |

## Use Case Contract

Input:

```text
email: str
reset_base_url: str
```

Output:

```text
None
```

Behavior:

1. Normalize and validate the email with `Email.from_raw`.
2. Lookup `UserRepository.get_by_email(email)`.
3. If no user exists, return without sending email.
4. If a user exists, generate a high-entropy `PasswordResetToken`.
5. Build the final reset URL by appending `token=<token>` to `reset_base_url`.
6. Call `IEmailGateway.send_password_reset(email, token, reset_url)`.
7. Return `None`.

## Anti-Enumeration Policy

The use case must not reveal whether the account exists.

- existing user: sends email and returns success;
- unknown user: does not send email and returns success;
- presentation layer should return `204 No Content` for both cases.

Invalid email format can still fail at validation time because it does not reveal account existence.

## Acceptance Criteria

Given an existing Candidate account,
When `ForgotPasswordUseCase.execute(email, reset_base_url)` runs,
Then one password reset email is sent through `IEmailGateway`,
And the generated reset URL contains the generated token.

Given an unknown email,
When `ForgotPasswordUseCase.execute(email, reset_base_url)` runs,
Then no email is sent,
And no error is raised.

Given the application layer,
When the use case is implemented,
Then it depends only on application ports and domain value objects,
And it does not import infrastructure or Resend.

## Frontend Contract For Atlas

The eventual presentation endpoint should return `204 No Content` for both existing and unknown users.

The frontend should display the same confirmation message for both cases, for example:

```text
If an account exists for this email, you will receive a reset link shortly.
```

## Validation

```bash
poetry run pytest tests/application/auth/test_forgot_password_use_case.py -q
poetry run pytest tests/application/ -q
```

Validated on 2026-06-05:

- focused forgot-password tests: `2 passed`;
- application test suite: `111 passed`;
- ruff on touched application/test files: passed.
