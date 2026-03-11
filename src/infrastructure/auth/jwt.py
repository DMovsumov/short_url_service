from datetime import timedelta
from typing import Optional

import jwt
from authx import AuthX, AuthXConfig
from passlib.context import CryptContext

from src.infrastructure.config import settings


class PasswordService:
    def __init__(self):
        self._pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

    def hash_password(self, password: str) -> str:

        return self._pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:

        return self._pwd_context.verify(plain_password, hashed_password)


class JWTService:
    def __init__(self):
        self._config = AuthXConfig(
            JWT_ALGORITHM=settings.jwt_algorithm,
            JWT_SECRET_KEY=settings.jwt_secret,
            JWT_ACCESS_TOKEN_EXPIRES=timedelta(seconds=settings.jwt_expiration),
            JWT_TOKEN_LOCATION=["cookies"],
            JWT_HEADER_TYPE="Bearer",
            JWT_HEADER_NAME="Authorization",
        )
        self._authx = AuthX(config=self._config)
        self._password_service = PasswordService()

    @property
    def authx(self) -> AuthX:

        return self._authx

    @property
    def password_service(self) -> PasswordService:

        return self._password_service

    def create_access_token(self, subject: str) -> str:

        return self._authx.create_access_token(uid=subject)

    def create_refresh_token(self, subject: str) -> str:

        return self._authx.create_refresh_token(uid=subject)

    def verify_token(self, token: str, token_type: str = "access") -> Optional[str]:
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
                options={"verify_aud": False},
            )
            if payload.get("type") != token_type:

                return None
            return payload.get("sub")
        except jwt.ExpiredSignatureError:

            return None
        except jwt.InvalidTokenError:

            return None


jwt_service = JWTService()
