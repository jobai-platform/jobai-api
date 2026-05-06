from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from app.application.storage.ports import StorageGateway, UploadedFile
from app.application.users.candidate_profile_ports import CandidateProfileRepository
from app.domain.common.exceptions import BadRequestError, NotFoundError

logger = logging.getLogger(__name__)

_ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
_MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
_URL_SPLIT_DEPTH = 4


@dataclass(frozen=True)
class UploadCVCommand:
    user_id: UUID
    filename: str
    content_type: str
    data: bytes


class UploadCVUseCase:
    def __init__(self, profile_repo: CandidateProfileRepository, storage: StorageGateway) -> None:
        self._profile_repo = profile_repo
        self._storage = storage

    async def execute(self, cmd: UploadCVCommand) -> UploadedFile:
        profile = await self._profile_repo.get_by_user_id(cmd.user_id)
        if profile is None:
            raise NotFoundError(code="profile_not_found", details="Candidate profile not found")

        if not cmd.data:
            raise BadRequestError(code="invalid_file", details="File is empty")
        if len(cmd.data) > _MAX_SIZE_BYTES:
            raise BadRequestError(code="file_too_large", details="File exceeds 5 MB limit")
        if cmd.content_type not in _ALLOWED_MIME_TYPES:
            raise BadRequestError(code="invalid_file_type", details="Only PDF and Word documents are accepted")

        key = f"cvs/{cmd.user_id}/{cmd.filename}"
        uploaded = await self._storage.upload(
            bucket="jobai-cvs",
            key=key,
            data=cmd.data,
            content_type=cmd.content_type,
        )

        profile.upsert(cv_url=uploaded.url)
        await self._profile_repo.save(profile)

        logger.info("UploadCV: user_id=%s key=%s size=%d", cmd.user_id, key, uploaded.size)
        return uploaded


class DeleteCVUseCase:
    def __init__(self, profile_repo: CandidateProfileRepository, storage: StorageGateway) -> None:
        self._profile_repo = profile_repo
        self._storage = storage

    async def execute(self, user_id: UUID) -> None:
        profile = await self._profile_repo.get_by_user_id(user_id)
        if profile is None:
            raise NotFoundError(code="profile_not_found", details="Candidate profile not found")
        if not profile.cv_url:
            raise BadRequestError(code="no_cv", details="No CV to delete")

        key = _extract_key(profile.cv_url)
        await self._storage.delete(bucket="jobai-cvs", key=key)

        profile.clear_cv()
        await self._profile_repo.save(profile)

        logger.info("DeleteCV: user_id=%s key=%s", user_id, key)


def _extract_key(url: str) -> str:
    # url is like http://host:port/bucket/cvs/user/file — extract key after /bucket/
    parts = url.split("/", _URL_SPLIT_DEPTH)
    return parts[_URL_SPLIT_DEPTH] if len(parts) > _URL_SPLIT_DEPTH else url
