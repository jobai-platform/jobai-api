from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.application.auth.use_cases import ResetPasswordUseCase, hash_password_reset_token
from app.application.users.ports import PasswordHasher
from app.domain.users.entities import Candidate
from app.domain.users.password_reset_token import PasswordResetToken
from app.domain.users.value_objects import Email, HashedPassword
from tests.fakes.auth.in_memory_password_reset_token_repo import (
    InMemoryPasswordResetTokenRepository,
)
from tests.fakes.users.in_memory_user_repo import InMemoryUserRepository

SIGNING_KEY = "test-password-reset-signing-key"
CREATED_AT = datetime(2026, 6, 7, 10, 0, tzinfo=UTC)


class FakePasswordHasher(PasswordHasher):
    def __init__(self) -> None:
        self.hashed_passwords: list[str] = []

    def hash_password(self, raw_password: str) -> str:
        self.hashed_passwords.append(raw_password)
        return f"hashed::{raw_password}"

    def verify(self, raw_password: str, hashed_password: str) -> bool:
        return hashed_password == f"hashed::{raw_password}"


async def _make_use_case() -> tuple[
    ResetPasswordUseCase,
    InMemoryUserRepository,
    InMemoryPasswordResetTokenRepository,
    FakePasswordHasher,
    Candidate,
    PasswordResetToken,
]:
    user_repo = InMemoryUserRepository()
    token_repo = InMemoryPasswordResetTokenRepository()
    password_hasher = FakePasswordHasher()
    candidate = await user_repo.create(
        Candidate(
            id=uuid4(),
            email=Email.from_raw("candidate@example.com"),
            hashed_password=HashedPassword("old-hash"),
        )
    )
    token = PasswordResetToken.generate(signing_key=SIGNING_KEY, now=CREATED_AT)
    await token_repo.save(
        candidate_id=candidate.id,
        token_hash=hash_password_reset_token(token.signed_value),
        created_at=token.created_at,
    )
    return (
        ResetPasswordUseCase(
            user_repo=user_repo,
            token_repo=token_repo,
            password_hasher=password_hasher,
            signing_key=SIGNING_KEY,
        ),
        user_repo,
        token_repo,
        password_hasher,
        candidate,
        token,
    )


@pytest.mark.asyncio
async def test_reset_password_hashes_and_persists_new_password_and_consumes_token() -> None:
    use_case, user_repo, token_repo, password_hasher, candidate, token = await _make_use_case()

    result = await use_case.execute(
        signed_token=token.signed_value,
        new_password="NewSecurePass1!",
        now=CREATED_AT + timedelta(minutes=5),
    )

    assert result is None
    updated = await user_repo.get_by_id(candidate.id)
    assert updated is not None
    assert updated.hashed_password == HashedPassword("hashed::NewSecurePass1!")
    assert password_hasher.hashed_passwords == ["NewSecurePass1!"]
    record = await token_repo.find_by_token_hash(hash_password_reset_token(token.signed_value))
    assert record is not None
    assert record.consumed_at == CREATED_AT + timedelta(minutes=5)


@pytest.mark.asyncio
async def test_reset_password_rejects_expired_token_without_changing_password() -> None:
    use_case, user_repo, _, password_hasher, candidate, token = await _make_use_case()

    with pytest.raises(ValueError, match="Invalid or expired password reset token"):
        await use_case.execute(
            signed_token=token.signed_value,
            new_password="NewSecurePass1!",
            now=CREATED_AT + timedelta(minutes=31),
        )

    unchanged = await user_repo.get_by_id(candidate.id)
    assert unchanged is not None
    assert unchanged.hashed_password == HashedPassword("old-hash")
    assert password_hasher.hashed_passwords == []


@pytest.mark.asyncio
async def test_reset_password_rejects_second_use() -> None:
    use_case, _, _, _, _, token = await _make_use_case()
    await use_case.execute(
        signed_token=token.signed_value,
        new_password="FirstSecurePass1!",
        now=CREATED_AT + timedelta(minutes=5),
    )

    with pytest.raises(ValueError, match="Invalid or expired password reset token"):
        await use_case.execute(
            signed_token=token.signed_value,
            new_password="SecondSecurePass1!",
            now=CREATED_AT + timedelta(minutes=6),
        )


@pytest.mark.asyncio
async def test_reset_password_rejects_tampered_token() -> None:
    use_case, _, _, password_hasher, _, token = await _make_use_case()
    tampered = f"tampered-{token.value}.{token.signature}"

    with pytest.raises(ValueError, match="Invalid or expired password reset token"):
        await use_case.execute(
            signed_token=tampered,
            new_password="NewSecurePass1!",
            now=CREATED_AT + timedelta(minutes=5),
        )

    assert password_hasher.hashed_passwords == []


@pytest.mark.asyncio
async def test_reset_password_rejects_invalid_signature_for_persisted_token_hash() -> None:
    use_case, _, token_repo, password_hasher, candidate, token = await _make_use_case()
    invalid_signature_token = f"{token.value}.{'0' * 64}"
    await token_repo.save(
        candidate_id=candidate.id,
        token_hash=hash_password_reset_token(invalid_signature_token),
        created_at=token.created_at,
    )

    with pytest.raises(ValueError, match="Invalid or expired password reset token"):
        await use_case.execute(
            signed_token=invalid_signature_token,
            new_password="NewSecurePass1!",
            now=CREATED_AT + timedelta(minutes=5),
        )

    assert password_hasher.hashed_passwords == []


@pytest.mark.asyncio
async def test_reset_password_rejects_unknown_token() -> None:
    use_case, _, _, password_hasher, _, _ = await _make_use_case()
    unknown = PasswordResetToken.generate(signing_key=SIGNING_KEY, now=CREATED_AT)

    with pytest.raises(ValueError, match="Invalid or expired password reset token"):
        await use_case.execute(
            signed_token=unknown.signed_value,
            new_password="NewSecurePass1!",
            now=CREATED_AT + timedelta(minutes=5),
        )

    assert password_hasher.hashed_passwords == []


@pytest.mark.asyncio
async def test_reset_password_rejects_failed_concurrent_claim_without_changing_password() -> None:
    use_case, user_repo, token_repo, password_hasher, candidate, token = await _make_use_case()
    token_repo.allow_consume = False

    with pytest.raises(ValueError, match="Invalid or expired password reset token"):
        await use_case.execute(
            signed_token=token.signed_value,
            new_password="NewSecurePass1!",
            now=CREATED_AT + timedelta(minutes=5),
        )

    unchanged = await user_repo.get_by_id(candidate.id)
    assert unchanged is not None
    assert unchanged.hashed_password == HashedPassword("old-hash")
    assert password_hasher.hashed_passwords == []
