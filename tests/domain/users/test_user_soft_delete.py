from datetime import datetime, timedelta, timezone
from uuid import uuid4


# The tests follow TDD: domain classes are referenced as imports from app.domain.users.entities
# and app.domain.common.deletion. They will guide the implementation.


def test_user_soft_delete_sets_deletion_info_and_scheduled_purge():
    # Arrange
    user_id = uuid4()
    created_at = datetime.now(timezone.utc) - timedelta(days=30)

    # Create a user domain instance (factory or constructor expected in domain layer)
    # We assume an immutable dataclass-style User with id, email, created_at and deletion info
    from app.domain.users.entities import User
    from app.domain.users.value_objects import Email

    user = User(id=user_id, email=Email.from_raw("user@example.com"), created_at=created_at)

    # Precondition
    assert not user.deletion.is_deleted
    assert user.deletion.deleted_at is None

    # Act: mark as deleted using domain service
    from app.domain.common.domain_services import SoftDeleteService

    service = SoftDeleteService()
    deletion_time = datetime.now(timezone.utc)
    retention = timedelta(days=365)
    user_after = service.mark_deleted(user, when=deletion_time, retention=retention)

    # Assert
    assert user_after.deletion.is_deleted
    assert user_after.deletion.deleted_at == deletion_time
    assert user_after.deletion.scheduled_purge_at == deletion_time + retention


def test_user_restore_clears_deletion_info():
    from datetime import datetime, timezone
    from uuid import uuid4

    user_id = uuid4()
    created_at = datetime.now(timezone.utc) - timedelta(days=100)

    from app.domain.users.entities import User
    from app.domain.users.value_objects import Email
    user = User(id=user_id, email=Email.from_raw("user2@example.com"), created_at=created_at)

    from app.domain.common.domain_services import SoftDeleteService
    service = SoftDeleteService()
    deletion_time = datetime.now(timezone.utc)
    user_deleted = service.mark_deleted(user, when=deletion_time)

    # Sanity check
    assert user_deleted.deletion.is_deleted

    # Act: restore
    user_restored = service.restore(user_deleted)

    # Assert
    assert not user_restored.deletion.is_deleted
    assert user_restored.deletion.deleted_at is None
    assert user_restored.deletion.scheduled_purge_at is None

