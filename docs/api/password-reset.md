# Password Reset API

## Request A Reset Email

```http
POST /api/v1/auth/password/forgot
Content-Type: application/json
```

```json
{"email": "candidate@example.com"}
```

Successful and unknown-account requests both return:

```http
204 No Content
```

This identical response prevents account enumeration.

```bash
curl -i -X POST "$API_URL/api/v1/auth/password/forgot" \
  -H "Content-Type: application/json" \
  -d '{"email":"candidate@example.com"}'
```

The email link targets `{FRONTEND_ORIGIN}/auth/password/reset?token=...`. The API controls this origin; clients cannot
provide a callback URL.

## Reset The Password

```http
POST /api/v1/auth/password/reset
Content-Type: application/json
```

```json
{
  "token": "<token-from-reset-link>",
  "new_password": "SecurePass1!"
}
```

Success:

```http
204 No Content
```

```bash
curl -i -X POST "$API_URL/api/v1/auth/password/reset" \
  -H "Content-Type: application/json" \
  -d '{"token":"<signed-token>","new_password":"SecurePass1!"}'
```

Invalid or expired token:

```http
400 Bad Request
```

```json
{
  "code": "bad_request",
  "detail": "Invalid or expired password reset token"
}
```

Weak passwords and malformed requests return `422` with `code: "validation_error"`.

## Password Policy

- minimum 12 characters;
- at least one uppercase letter;
- at least one digit;
- at least one special character.

## Configuration

| Variable | Purpose |
|---|---|
| `FRONTEND_ORIGIN` | Trusted frontend origin used to build reset links |
| `PASSWORD_RESET_SIGNING_KEY` | Signs and validates reset tokens |
| `RESEND_API_KEY_SANDBOX` | Resend credential outside production |
| `RESEND_API_KEY_PROD` | Resend production credential |
| `RESEND_FROM_EMAIL` | Sender identity |

