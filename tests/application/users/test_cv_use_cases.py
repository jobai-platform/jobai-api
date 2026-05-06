import pytest
from uuid import uuid4

from app.application.users.cv_use_cases import DeleteCVUseCase, UploadCVCommand, UploadCVUseCase
from app.domain.common.exceptions import BadRequestError, NotFoundError
from app.domain.users.candidate_profile import CandidateProfile
from tests.fakes.storage.fake_storage_gateway import FakeStorageGateway
from tests.fakes.users.in_memory_candidate_profile_repo import InMemoryCandidateProfileRepository

_PDF = b"%PDF-1.4 fake content"
_PDF_MIME = "application/pdf"


def _make_use_cases():
    repo = InMemoryCandidateProfileRepository()
    storage = FakeStorageGateway()
    upload_uc = UploadCVUseCase(profile_repo=repo, storage=storage)
    delete_uc = DeleteCVUseCase(profile_repo=repo, storage=storage)
    return upload_uc, delete_uc, repo, storage


# ---------------------------------------------------------------------------
# UploadCVUseCase
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upload_cv_happy_path():
    upload_uc, _, repo, storage = _make_use_cases()
    user_id = uuid4()
    await repo.save(CandidateProfile(user_id=user_id))

    result = await upload_uc.execute(UploadCVCommand(
        user_id=user_id,
        filename="cv.pdf",
        content_type=_PDF_MIME,
        data=_PDF,
    ))

    assert result.key == f"cvs/{user_id}/cv.pdf"
    assert result.url.endswith(f"cvs/{user_id}/cv.pdf")
    assert result.size == len(_PDF)
    assert result.content_type == _PDF_MIME
    assert len(storage.uploads) == 1

    profile = await repo.get_by_user_id(user_id)
    assert profile.cv_url is not None


@pytest.mark.asyncio
async def test_upload_cv_raises_when_profile_not_found():
    upload_uc, _, _, _ = _make_use_cases()

    with pytest.raises(NotFoundError, match="profile_not_found"):
        await upload_uc.execute(UploadCVCommand(
            user_id=uuid4(),
            filename="cv.pdf",
            content_type=_PDF_MIME,
            data=_PDF,
        ))


@pytest.mark.asyncio
async def test_upload_cv_raises_on_empty_file():
    upload_uc, _, repo, _ = _make_use_cases()
    user_id = uuid4()
    await repo.save(CandidateProfile(user_id=user_id))

    with pytest.raises(BadRequestError, match="invalid_file"):
        await upload_uc.execute(UploadCVCommand(
            user_id=user_id, filename="empty.pdf", content_type=_PDF_MIME, data=b"",
        ))


@pytest.mark.asyncio
async def test_upload_cv_raises_on_file_too_large():
    upload_uc, _, repo, _ = _make_use_cases()
    user_id = uuid4()
    await repo.save(CandidateProfile(user_id=user_id))

    with pytest.raises(BadRequestError, match="file_too_large"):
        await upload_uc.execute(UploadCVCommand(
            user_id=user_id,
            filename="huge.pdf",
            content_type=_PDF_MIME,
            data=b"x" * (5 * 1024 * 1024 + 1),
        ))


@pytest.mark.asyncio
async def test_upload_cv_raises_on_invalid_mime_type():
    upload_uc, _, repo, _ = _make_use_cases()
    user_id = uuid4()
    await repo.save(CandidateProfile(user_id=user_id))

    with pytest.raises(BadRequestError, match="invalid_file_type"):
        await upload_uc.execute(UploadCVCommand(
            user_id=user_id,
            filename="photo.png",
            content_type="image/png",
            data=b"fakepng",
        ))


@pytest.mark.asyncio
async def test_upload_cv_accepts_docx():
    upload_uc, _, repo, storage = _make_use_cases()
    user_id = uuid4()
    await repo.save(CandidateProfile(user_id=user_id))

    result = await upload_uc.execute(UploadCVCommand(
        user_id=user_id,
        filename="cv.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        data=b"fake docx content",
    ))

    assert result.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


# ---------------------------------------------------------------------------
# DeleteCVUseCase
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_cv_happy_path():
    upload_uc, delete_uc, repo, storage = _make_use_cases()
    user_id = uuid4()
    await repo.save(CandidateProfile(user_id=user_id))
    await upload_uc.execute(UploadCVCommand(
        user_id=user_id, filename="cv.pdf", content_type=_PDF_MIME, data=_PDF,
    ))

    await delete_uc.execute(user_id)

    assert len(storage.deletes) == 1
    profile = await repo.get_by_user_id(user_id)
    assert profile.cv_url is None


@pytest.mark.asyncio
async def test_delete_cv_raises_when_no_cv():
    _, delete_uc, repo, _ = _make_use_cases()
    user_id = uuid4()
    await repo.save(CandidateProfile(user_id=user_id))

    with pytest.raises(BadRequestError, match="no_cv"):
        await delete_uc.execute(user_id)


@pytest.mark.asyncio
async def test_delete_cv_raises_when_profile_not_found():
    _, delete_uc, _, _ = _make_use_cases()

    with pytest.raises(NotFoundError, match="profile_not_found"):
        await delete_uc.execute(uuid4())
