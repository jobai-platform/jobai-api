from dataclasses import dataclass, field

from httpx import ASGITransport, AsyncClient
import pytest
import pytest_asyncio

from app.application.auth.use_cases import hash_password_reset_token
from app.core.config import settings
from app.core.dependency import (
    get_email_gateway,
    get_forgot_password_use_case,
    get_reset_password_use_case,
)
from app.domain.users.password_reset_token import PasswordResetToken
from app.domain.users.value_objects import Email
from app.infrastructure.persistence.repositories.password_reset_token_sqlalchemy import (
    SQLAlchemyPasswordResetTokenRepository,
)
from app.infrastructure.security.password_service import PasswordServiceAdapter
from app.main import app


@pytest_asyncio.fixture
async def api_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@dataclass
class FakeForgotPasswordUseCase:
    calls: list[dict[str, str]] = field(default_factory=list)

    async def execute(self, *, email: str, reset_base_url: str) -> None:
        self.calls.append({"email": email, "reset_base_url": reset_base_url})


@dataclass
class FakeResetPasswordUseCase:
    error: ValueError | None = None
    calls: list[dict[str, str]] = field(default_factory=list)

    async def execute(self, *, signed_token: str, new_password: str) -> None:
        self.calls.append({"signed_token": signed_token, "new_password": new_password})
        if self.error is not None:
            raise self.error


@dataclass
class FakeEmailGateway:
    sent: list[dict[str, str]] = field(default_factory=list)

    async def send_password_reset(self, email: Email, token: str, reset_url: str) -> None:
        self.sent.append(
            {
                "email": email.value,
                "token": token,
                "reset_url": reset_url,
            }
        )


@pytest.mark.asyncio
async def test_password_forgot_returns_204_and_uses_server_frontend_origin(api_client, monkeypatch):
    use_case = FakeForgotPasswordUseCase()
    monkeypatch.setattr(settings, "FRONTEND_ORIGIN", "https://app.jobai.example/")
    app.dependency_overrides[get_forgot_password_use_case] = lambda: use_case

    response = await api_client.post(
        "/api/v1/auth/password/forgot",
        json={"email": "Candidate@Example.com"},
    )

    assert response.status_code == 204
    assert response.content == b""
    assert use_case.calls == [
        {
            "email": "Candidate@example.com",
            "reset_base_url": "https://app.jobai.example/auth/password/reset",
        }
    ]


@pytest.mark.asyncio
async def test_password_forgot_returns_422_for_invalid_email(api_client):
    use_case = FakeForgotPasswordUseCase()
    app.dependency_overrides[get_forgot_password_use_case] = lambda: use_case

    response = await api_client.post(
        "/api/v1/auth/password/forgot",
        json={"email": "not-an-email"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert use_case.calls == []


@pytest.mark.asyncio
async def test_password_reset_returns_204_for_valid_request(api_client):
    use_case = FakeResetPasswordUseCase()
    app.dependency_overrides[get_reset_password_use_case] = lambda: use_case

    response = await api_client.post(
        "/api/v1/auth/password/reset",
        json={"token": "signed-token", "new_password": "SecurePass1!"},
    )

    assert response.status_code == 204
    assert response.content == b""
    assert use_case.calls == [
        {
            "signed_token": "signed-token",
            "new_password": "SecurePass1!",
        }
    ]


@pytest.mark.asyncio
async def test_password_reset_returns_uniform_400_for_invalid_token(api_client):
    use_case = FakeResetPasswordUseCase(
        error=ValueError("Invalid or expired password reset token"),
    )
    app.dependency_overrides[get_reset_password_use_case] = lambda: use_case

    response = await api_client.post(
        "/api/v1/auth/password/reset",
        json={"token": "invalid-token", "new_password": "SecurePass1!"},
    )

    assert response.status_code == 400
    assert response.json() == {
        "code": "bad_request",
        "detail": "Invalid or expired password reset token",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "new_password",
    [
        "short1A!",
        "nouppercase1!aaa",
        "NoDigitHere!!!a",
        "NoSpecialChar1a",
    ],
)
async def test_password_reset_returns_422_for_weak_password(api_client, new_password):
    use_case = FakeResetPasswordUseCase()
    app.dependency_overrides[get_reset_password_use_case] = lambda: use_case

    response = await api_client.post(
        "/api/v1/auth/password/reset",
        json={"token": "signed-token", "new_password": new_password},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert use_case.calls == []


@pytest.mark.asyncio
async def test_password_forgot_wires_real_use_case_repository_and_email_gateway(
    client,
    db_session,
    create_user_in_db,
):
    await create_user_in_db("forgot-integration@example.com")
    email_gateway = FakeEmailGateway()
    app.dependency_overrides[get_email_gateway] = lambda: email_gateway

    response = await client.post(
        "/api/v1/auth/password/forgot",
        json={"email": "forgot-integration@example.com"},
    )

    assert response.status_code == 204
    assert len(email_gateway.sent) == 1
    sent = email_gateway.sent[0]
    assert sent["email"] == "forgot-integration@example.com"
    assert sent["reset_url"].startswith(f"{settings.FRONTEND_ORIGIN.rstrip('/')}/auth/password/reset?token=")

    token_repo = SQLAlchemyPasswordResetTokenRepository(db_session)
    record = await token_repo.find_by_token_hash(hash_password_reset_token(sent["token"]))
    assert record is not None


@pytest.mark.asyncio
async def test_password_reset_wires_real_use_case_and_consumes_token(
    client,
    db_session,
    create_user_in_db,
):
    candidate = await create_user_in_db("reset-integration@example.com", password="OldSecurePass1!")
    token = PasswordResetToken.generate(signing_key=settings.PASSWORD_RESET_SIGNING_KEY)
    token_hash = hash_password_reset_token(token.signed_value)
    token_repo = SQLAlchemyPasswordResetTokenRepository(db_session)
    await token_repo.save(
        candidate_id=candidate.id,
        token_hash=token_hash,
        created_at=token.created_at,
    )

    response = await client.post(
        "/api/v1/auth/password/reset",
        json={"token": token.signed_value, "new_password": "NewSecurePass1!"},
    )

    assert response.status_code == 204
    await db_session.refresh(candidate)
    assert candidate.hashed_password is not None
    assert PasswordServiceAdapter().verify("NewSecurePass1!", candidate.hashed_password)

    record = await token_repo.find_by_token_hash(token_hash)
    assert record is not None
    assert record.consumed_at is not None
