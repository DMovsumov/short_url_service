from typing import Optional
from uuid import UUID

from src.application.commands import LoginCommand, RefreshTokenCommand, RegisterCommand
from src.application.dto import TokenPair, UserAuthDto
from src.domain.entities import User
from src.domain.repositories import UserRepository
from src.infrastructure.auth import JWTService


class EmailAlreadyExistsError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class AuthHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        jwt_service: JWTService,
    ):
        self.user_repository = user_repository
        self.jwt_service = jwt_service

    async def register(self, command: RegisterCommand) -> TokenPair:
        existing_user = await self.user_repository.get_by_email(command.email)

        if existing_user:
            raise EmailAlreadyExistsError(f"Email {command.email} already registered")

        user = User.create(
            email=command.email,
            password=command.password,
        )

        await self.user_repository.add(user)

        access_token = self.jwt_service.create_access_token(subject=str(user.id))
        refresh_token = self.jwt_service.create_refresh_token(subject=str(user.id))

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def login(self, command: LoginCommand) -> TokenPair:
        user = await self.user_repository.get_by_email(command.email)

        if not user:
            raise InvalidCredentialsError("Invalid email or password")

        if not user.is_active:
            raise InvalidCredentialsError("User account is deactivated")

        if not user.verify_password(command.password):
            raise InvalidCredentialsError("Invalid email or password")

        access_token = self.jwt_service.create_access_token(subject=str(user.id))
        refresh_token = self.jwt_service.create_refresh_token(subject=str(user.id))

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def refresh_tokens(self, command: RefreshTokenCommand) -> TokenPair:
        user_id = self.jwt_service.verify_token(
            command.refresh_token, token_type="refresh"
        )

        if not user_id:
            raise InvalidCredentialsError("Invalid refresh token")

        access_token = self.jwt_service.create_access_token(subject=user_id)
        refresh_token = self.jwt_service.create_refresh_token(subject=user_id)

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def get_current_user(self, access_token: str) -> Optional[UserAuthDto]:
        user_id = self.jwt_service.verify_token(access_token, token_type="access")

        if not user_id:
            return None

        user = await self.user_repository.get_by_id(UUID(user_id))
        if not user or not user.is_active:
            return None

        return UserAuthDto(
            id=user.id,
            email=user.email,
        )
