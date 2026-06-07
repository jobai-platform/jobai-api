import json

import httpx
import pytest

from app.domain.users.value_objects import Email
from app.infrastructure.email.resend_gateway import (
    ResendEmailError,
    ResendEmailSender,
    resolve_resend_api_key,
)


def test_resolve_resend_api_key_prefers_sandbox_outside_production(monkeypatch) -> None:
    monkeypatch.setenv("RESEND_API_KEY_SANDBOX", "sandbox-key")
    monkeypatch.setenv("RESEND_API_KEY_PROD", "production-key")
    monkeypatch.setenv("RESEND_API_KEY", "fallback-key")

    assert resolve_resend_api_key("preview") == "sandbox-key"


def test_resolve_resend_api_key_prefers_production_key_in_production(monkeypatch) -> None:
    monkeypatch.setenv("RESEND_API_KEY_SANDBOX", "sandbox-key")
    monkeypatch.setenv("RESEND_API_KEY_PROD", "production-key")
    monkeypatch.setenv("RESEND_API_KEY", "fallback-key")

    assert resolve_resend_api_key("production") == "production-key"


def test_resolve_resend_api_key_uses_backward_compatible_fallback(monkeypatch) -> None:
    monkeypatch.delenv("RESEND_API_KEY_SANDBOX", raising=False)
    monkeypatch.delenv("RESEND_API_KEY_PROD", raising=False)
    monkeypatch.setenv("RESEND_API_KEY", "fallback-key")

    assert resolve_resend_api_key("dev") == "fallback-key"


def test_resolve_resend_api_key_fails_when_no_key_is_configured(monkeypatch) -> None:
    monkeypatch.delenv("RESEND_API_KEY_SANDBOX", raising=False)
    monkeypatch.delenv("RESEND_API_KEY_PROD", raising=False)
    monkeypatch.delenv("RESEND_API_KEY", raising=False)

    with pytest.raises(ValueError, match="Resend API key is not configured"):
        resolve_resend_api_key("dev")


@pytest.mark.asyncio
async def test_resend_email_sender_posts_password_reset_email() -> None:
    captured_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request
        return httpx.Response(200, json={"id": "email-id"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    sender = ResendEmailSender(
        api_key="sandbox-key",
        from_email="JobAI <onboarding@resend.dev>",
        client=client,
    )

    await sender.send_password_reset(
        Email.from_raw("candidate@example.com"),
        "token.signature",
        "https://app.jobai.test/reset-password?token=token.signature",
    )

    assert captured_request is not None
    assert captured_request.url == "https://api.resend.com/emails"
    assert captured_request.headers["Authorization"] == "Bearer sandbox-key"
    payload = json.loads(captured_request.content)
    assert payload["from"] == "JobAI <onboarding@resend.dev>"
    assert payload["to"] == ["candidate@example.com"]
    assert payload["subject"] == "Reset your JobAI password"
    assert "https://app.jobai.test/reset-password?token=token.signature" in payload["html"]
    assert "https://app.jobai.test/reset-password?token=token.signature" in payload["text"]
    await client.aclose()


@pytest.mark.asyncio
async def test_resend_email_sender_raises_safe_error_for_provider_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer secret-api-key"
        return httpx.Response(
            422,
            json={
                "message": (
                    "invalid sender for secret-api-key and "
                    "https://app.jobai.test/reset-password?token=token.signature"
                )
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    sender = ResendEmailSender(api_key="secret-api-key", client=client)

    with pytest.raises(ResendEmailError) as raised:
        await sender.send_password_reset(
            Email.from_raw("candidate@example.com"),
            "token.signature",
            "https://app.jobai.test/reset-password?token=token.signature",
        )

    assert "422" in str(raised.value)
    assert "invalid sender" in str(raised.value)
    assert "secret-api-key" not in str(raised.value)
    assert "token.signature" not in str(raised.value)
    await client.aclose()


@pytest.mark.asyncio
async def test_resend_email_sender_raises_safe_error_for_network_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("network unavailable", request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    sender = ResendEmailSender(api_key="secret-api-key", client=client)

    with pytest.raises(ResendEmailError, match="Resend request failed"):
        await sender.send_password_reset(
            Email.from_raw("candidate@example.com"),
            "token.signature",
            "https://app.jobai.test/reset-password?token=token.signature",
        )

    await client.aclose()
