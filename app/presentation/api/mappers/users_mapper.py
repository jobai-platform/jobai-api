from app.domain.users.entities import User
from app.domain.users.value_objects import Email
from app.presentation.api.v1.schemas.users import UserRead, UserUpdate


def to_user_read(user: User) -> UserRead:
    """
    Maps a User domain entity to a UserRead schema.
    :param user:
    :return:
    """
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


def to_domain_user(payload: UserUpdate) -> User:
    """
    Mapper API -> Domain (partial update
    Important: This returns a "partial" User object:
    - only fields explicitly provided are set
    - others are left as None so repo.update() can merge safely
    :param payload:
    :return:
    """
    data = payload.model_dump(exclude_unset=True)

    email_vo = None
    if "email" in data and data ["email"] is not None:
        email_vo = Email.from_raw(str(data["email"]))

    return User(
        id=None,
        email=email_vo,
        username=data.get("username"),
        first_name=data.get("first_name"),
        last_name=data.get("last_name"),
        hashed_password=data.get("hashed_password"),
        role=data.get("role"),
        is_active=data.get("is_active"),
        stripe_customer_id=data.get("stripe_customer_id"),
    )
