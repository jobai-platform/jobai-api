from app.domain.users.entities import User
from app.presentation.api.v1.schemas.users import UserRead


def to_user_read(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        email=str(user.email),
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        stripe_customer_id=user.stripe_customer_id,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at
    )
