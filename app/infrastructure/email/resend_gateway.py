from html import escape
import os

import httpx

from app.application.auth.ports import IEmailGateway
from app.domain.users.value_objects import Email

RESEND_EMAILS_URL = "https://api.resend.com/emails"
DEFAULT_FROM_EMAIL = "JobAI <onboarding@resend.dev>"


class ResendEmailError(RuntimeError):
    pass


def resolve_resend_api_key(app_env: str) -> str:
    environment_key = (
        os.getenv("RESEND_API_KEY_PROD")
        if app_env.strip().lower() == "production"
        else os.getenv("RESEND_API_KEY_SANDBOX")
    )
    api_key = environment_key or os.getenv("RESEND_API_KEY")
    if not api_key:
        raise ValueError("Resend API key is not configured")
    return api_key


class ResendEmailSender(IEmailGateway):
    def __init__(
        self,
        *,
        api_key: str | None = None,
        app_env: str | None = None,
        from_email: str | None = None,
        timeout: float | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key or resolve_resend_api_key(app_env or os.getenv("APP_ENV", "dev"))
        self._from_email = from_email or os.getenv("RESEND_FROM_EMAIL", DEFAULT_FROM_EMAIL)
        resolved_timeout = timeout or float(os.getenv("RESEND_TIMEOUT", "10.0"))
        self._client = client or httpx.AsyncClient(timeout=resolved_timeout)
        self._owns_client = client is None

    async def send_password_reset(self, email: Email, token: str, reset_url: str) -> None:
        safe_reset_url = escape(reset_url, quote=True)
        payload = {
            "from": self._from_email,
            "to": [email.value],
            "subject": "Reset your JobAI password",
            "html": (
                "<p>You requested a password reset for your JobAI account.</p>"
                f'<p><a href="{safe_reset_url}">Reset your password</a></p>'
                "<p>This link expires in 30 minutes and can be used only once.</p>"
            ),
            "text": (
                "You requested a password reset for your JobAI account.\n\n"
                f"Reset your password: {reset_url}\n\n"
                "This link expires in 30 minutes and can be used only once."
            ),
        }
        try:
            response = await self._client.post(
                RESEND_EMAILS_URL,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=payload,
            )
        except httpx.HTTPError as exc:
            raise ResendEmailError("Resend request failed") from exc

        if response.is_success:
            return

        provider_message = _provider_error_message(response)
        provider_message = _redact_provider_message(
            provider_message,
            secrets=(self._api_key, token, reset_url),
        )
        raise ResendEmailError(
            f"Resend rejected email with status {response.status_code}: {provider_message}"
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()


def _provider_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return "provider error"
    message = payload.get("message") if isinstance(payload, dict) else None
    return str(message) if message else "provider error"


def _redact_provider_message(message: str, *, secrets: tuple[str, ...]) -> str:
    redacted = message
    for secret in secrets:
        if secret:
            redacted = redacted.replace(secret, "[redacted]")
    return redacted
