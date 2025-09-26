from datetime import timedelta, datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from fastapi.params import Security
from fastapi.security import OAuth2PasswordBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core import settings

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES


class AuthHandler:
    """
    Auth handler class is the core of our JWT authentication system. it handles password hashing, token creation, token verification, and user authentication.
    """

    def __init__(self) -> None:
        pass

    # bcrypt_salt = '$2b$12$KIXQJ4YhX6RPu7vZy0O5eu'  # bcrypt salt for hashing passwords
    bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
    oauth2_bearer = OAuth2PasswordBearer(tokenUrl='auth/token')

    async def verify_password(self, plain_password: str, salt: str, hashed_password: str) -> bool:
        """Verify a plain password against a hashed password with salt."""
        return self.bcrypt_context.verify(salt + plain_password, hashed_password)


    async def get_password_hash(self, password: str) -> str:
        """Hash a password with bcrypt."""
        return self.bcrypt_context.hash(password)


    async def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        Create access token
        :param data: dict
        :param expires_delta: Optional[timedelta]
        :rtype: str
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({'exp': expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt


    async def auth_wrapper(self, auth: HTTPAuthorizationCredentials = Security(oauth2_bearer)) -> str:
        """"
        Auth wrapper
        :param auth: HTTPAuthorizationCredentials
        :rtype: str
        """
        token = auth.credentials

        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail= 'Invalid token or expired token.',
                headers={'WWW-Authenticate': 'Bearer'}
            )

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get('sub')

            if username is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail='Invalid token or expired token.',
                    headers={'WWW-Authenticate': 'Bearer'}
                )
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f'Could not validate credentials: {str(e)}',
                headers={'WWW-Authenticate': 'Bearer'}
            )

