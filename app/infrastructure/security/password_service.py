from passlib.context import CryptContext

from app.application.users.ports import PasswordHasher


pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")

class PasswordService:
    """ Hash and verify passwords by bcrypt. """

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)


class PasswordServiceAdapter(PasswordHasher):
    """ Adapter for password service that implements the PasswordHasher port."""

    def __init__(self, service: PasswordService | None = None) -> None:
        # instantiate PasswordService when not provided
        self._service = service or PasswordService()

    def hash_password(self, raw_password: str) -> str:
        return self._service.hash_password(raw_password)

    def verify(self, raw_password: str, hashed_password: str) -> bool:
        return self._service.verify_password(raw_password, hashed_password)
