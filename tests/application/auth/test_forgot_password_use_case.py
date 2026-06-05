from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

import pytest

from app.application.auth.ports import IEmailGateway
from app.application.auth.use_cases import ForgotPasswordUseCase
from app.domain.users.entities import Candidate
from app.domain.users.value_objects import Email, HashedPassword
from tests.fakes.users.in_memory_user_repo import InMemoryUserRepository


@dataclass(frozen=True, slots=True)
class SentPasswordResetEmail:
    email: Email
    token: str
    reset_url: str


class FakeEmailGateway(IEmailGateway):
    def __init__(self) -> None:
        self.sent_password_reset_emails: list[SentPasswordResetEmail] = []

    async def send_password_reset(self, email: Email, token: str, reset_url: str) -> None:
        self.sent_password_reset_emails.append(SentPasswordResetEmail(email=email, token=token, reset_url=reset_url))


def _make_use_case(
    user_repo: InMemoryUserRepository | None = None,
    email_gateway: FakeEmailGateway | None = None,
) -> tuple[ForgotPasswordUseCase, InMemoryUserRepository, FakeEmailGateway]:
    user_repo = user_repo or InMemoryUserRepository()
    email_gateway = email_gateway or FakeEmailGateway()
    return ForgotPasswordUseCase(user_repo=user_repo, email_gateway=email_gateway), user_repo, email_gateway


@pytest.mark.asyncio
async def test_forgot_password_sends_reset_email_when_user_exists() -> None:
    use_case, user_repo, email_gateway = _make_use_case()
    await user_repo.create(
        Candidate(
            id=uuid4(),
            email=Email.from_raw("candidate@example.com"),
            hashed_password=HashedPassword("hashed-password"),
        )
    )

    result = await use_case.execute(
        email="Candidate@Example.com",
        reset_base_url="https://app.jobai.test/reset-password",
    )

    assert result is None
    assert len(email_gateway.sent_password_reset_emails) == 1
    sent_email = email_gateway.sent_password_reset_emails[0]
    assert sent_email.email == Email.from_raw("candidate@example.com")
    assert sent_email.token
    assert sent_email.token in sent_email.reset_url
    assert sent_email.reset_url.startswith("https://app.jobai.test/reset-password?token=")


@pytest.mark.asyncio
async def test_forgot_password_returns_success_without_email_when_user_does_not_exist() -> None:
    use_case, _, email_gateway = _make_use_case()

    result = await use_case.execute(
        email="unknown@example.com",
        reset_base_url="https://app.jobai.test/reset-password",
    )

    assert result is None
    assert email_gateway.sent_password_reset_emails == []
