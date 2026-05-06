import io
import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from app.application.storage.ports import UploadedFile
from app.application.users.cv_use_cases import DeleteCVUseCase, UploadCVUseCase
from app.core.dependency import get_delete_cv_use_case, get_upload_cv_use_case
from app.domain.common.exceptions import BadRequestError, NotFoundError
from app.main import app

_PDF = b"%PDF-1.4 fake"
_PDF_MIME = "application/pdf"


def _uploaded_file(user_id, filename="cv.pdf") -> UploadedFile:
    key = f"cvs/{user_id}/{filename}"
    return UploadedFile(
        key=key,
        url=f"http://localhost:9000/jobai-cvs/{key}",
        size=len(_PDF),
        content_type=_PDF_MIME,
    )


# ---------------------------------------------------------------------------
# POST /candidates/me/cv
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upload_cv_returns_201(client, create_user_in_db, jwt_service):
    user = await create_user_in_db(email="cv_upload@test.com", password="secret")
    token = jwt_service.create_access_token(subject=str(user.id), extra={"role": "user", "email": user.email})

    fake_uc = AsyncMock(spec=UploadCVUseCase)
    fake_uc.execute.return_value = _uploaded_file(user.id)
    app.dependency_overrides[get_upload_cv_use_case] = lambda: fake_uc

    response = await client.post(
        "/api/v1/candidates/me/cv",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("cv.pdf", io.BytesIO(_PDF), _PDF_MIME)},
    )

    app.dependency_overrides.pop(get_upload_cv_use_case, None)

    assert response.status_code == 201
    data = response.json()
    assert "url" in data
    assert data["content_type"] == _PDF_MIME


@pytest.mark.asyncio
async def test_upload_cv_returns_401_without_token(client):
    response = await client.post(
        "/api/v1/candidates/me/cv",
        files={"file": ("cv.pdf", io.BytesIO(_PDF), _PDF_MIME)},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_cv_returns_400_on_invalid_file(client, create_user_in_db, jwt_service):
    user = await create_user_in_db(email="cv_bad_file@test.com", password="secret")
    token = jwt_service.create_access_token(subject=str(user.id), extra={"role": "user", "email": user.email})

    fake_uc = AsyncMock(spec=UploadCVUseCase)
    fake_uc.execute.side_effect = BadRequestError(code="invalid_file_type", details="Only PDF/Word allowed")
    app.dependency_overrides[get_upload_cv_use_case] = lambda: fake_uc

    response = await client.post(
        "/api/v1/candidates/me/cv",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("photo.png", io.BytesIO(b"fakepng"), "image/png")},
    )

    app.dependency_overrides.pop(get_upload_cv_use_case, None)

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_cv_returns_404_when_profile_not_found(client, create_user_in_db, jwt_service):
    user = await create_user_in_db(email="cv_no_profile@test.com", password="secret")
    token = jwt_service.create_access_token(subject=str(user.id), extra={"role": "user", "email": user.email})

    fake_uc = AsyncMock(spec=UploadCVUseCase)
    fake_uc.execute.side_effect = NotFoundError(code="profile_not_found", details="Profile not found")
    app.dependency_overrides[get_upload_cv_use_case] = lambda: fake_uc

    response = await client.post(
        "/api/v1/candidates/me/cv",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("cv.pdf", io.BytesIO(_PDF), _PDF_MIME)},
    )

    app.dependency_overrides.pop(get_upload_cv_use_case, None)

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /candidates/me/cv
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_cv_returns_204(client, create_user_in_db, jwt_service):
    user = await create_user_in_db(email="cv_delete@test.com", password="secret")
    token = jwt_service.create_access_token(subject=str(user.id), extra={"role": "user", "email": user.email})

    fake_uc = AsyncMock(spec=DeleteCVUseCase)
    fake_uc.execute.return_value = None
    app.dependency_overrides[get_delete_cv_use_case] = lambda: fake_uc

    response = await client.delete(
        "/api/v1/candidates/me/cv",
        headers={"Authorization": f"Bearer {token}"},
    )

    app.dependency_overrides.pop(get_delete_cv_use_case, None)

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_cv_returns_401_without_token(client):
    response = await client.delete("/api/v1/candidates/me/cv")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_cv_returns_400_when_no_cv(client, create_user_in_db, jwt_service):
    user = await create_user_in_db(email="cv_delete_none@test.com", password="secret")
    token = jwt_service.create_access_token(subject=str(user.id), extra={"role": "user", "email": user.email})

    fake_uc = AsyncMock(spec=DeleteCVUseCase)
    fake_uc.execute.side_effect = BadRequestError(code="no_cv", details="No CV to delete")
    app.dependency_overrides[get_delete_cv_use_case] = lambda: fake_uc

    response = await client.delete(
        "/api/v1/candidates/me/cv",
        headers={"Authorization": f"Bearer {token}"},
    )

    app.dependency_overrides.pop(get_delete_cv_use_case, None)

    assert response.status_code == 400
