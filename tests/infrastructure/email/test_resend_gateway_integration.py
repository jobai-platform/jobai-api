import os

import pytest

from app.domain.users.value_objects import Email
from app.infrastructure.email.resend_gateway import ResendEmailSender


@pytest.mark.asyncio
@pytest.mark.integration
async def test_resend_email_sender_sends_real_sandbox_email() -> None:
    api_key = os.getenv("RESEND_API_KEY_SANDBOX")
    recipient = os.getenv("RESEND_SANDBOX_RECIPIENT")
    if not api_key or not recipient:
        pytest.skip("RESEND_API_KEY_SANDBOX and RESEND_SANDBOX_RECIPIENT are required")

    sender = ResendEmailSender(
        api_key=api_key,
        from_email="JobAI <onboarding@resend.dev>",
    )
    try:
        await sender.send_password_reset(
            Email.from_raw(recipient),
            "sandbox-token.signature",
            "https://app.jobai.test/reset-password?token=sandbox-token.signature",
        )
    finally:
        await sender.aclose()
