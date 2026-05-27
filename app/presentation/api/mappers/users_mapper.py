from uuid import uuid4

from app.domain.users.entities import Candidate
from app.domain.users.value_objects import Email
from app.presentation.api.v1.schemas.users import UserRead, UserUpdate


def to_candidate_read(candidate: Candidate) -> UserRead:
    return UserRead(
        id=candidate.id,
        email=str(candidate.email),
        username=candidate.username,
        first_name=candidate.first_name,
        last_name=candidate.last_name,
        linkedin_id=candidate.linkedin_id,
        avatar_url=candidate.avatar_url,
        role=candidate.role,
        is_active=candidate.is_active,
        created_at=candidate.created_at,
        updated_at=candidate.updated_at,
    )


def to_domain_candidate(payload: UserUpdate) -> Candidate:
    """
    Mapper API → Domain (partial update).
    Only fields explicitly provided are set; others stay None so
    repo.update() can merge safely.
    """
    data = payload.model_dump(exclude_unset=True)

    email_vo = None
    if "email" in data and data["email"] is not None:
        email_vo = Email.from_raw(str(data["email"]))

    return Candidate(
        id=uuid4(),  # placeholder — repo.update() ignores this field, uses the route's user_id param
        email=email_vo,
        username=data.get("username"),
        first_name=data.get("first_name"),
        last_name=data.get("last_name"),
        role=data.get("role"),
        is_active=data.get("is_active"),
    )


# Backwards-compatible aliases — remove once all callers are updated
to_user_read = to_candidate_read
to_domain_user = to_domain_candidate
