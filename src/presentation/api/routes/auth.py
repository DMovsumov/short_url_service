from authx import AuthX
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import APIKeyCookie
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands import LoginCommand, RefreshTokenCommand, RegisterCommand
from src.application.handlers.auth import (
    AuthHandler,
    EmailAlreadyExistsError,
    InvalidCredentialsError,
)
from src.infrastructure.auth import jwt_service
from src.infrastructure.config import settings
from src.infrastructure.database import get_db
from src.infrastructure.persistence.repositories import UserRepositoryImpl
from src.presentation.api.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)

access_token_cookie = APIKeyCookie(
    name=settings.access_token_cookie_name,
    auto_error=False,
)
refresh_token_cookie = APIKeyCookie(
    name=settings.refresh_token_cookie_name,
    auto_error=False,
)


def get_auth_handler(db: AsyncSession = Depends(get_db)) -> AuthHandler:
    repository = UserRepositoryImpl(db)

    return AuthHandler(repository, jwt_service)


def get_authx() -> AuthX:

    return jwt_service.authx


def _set_token_cookies(
    response: Response, access_token: str, refresh_token: str
) -> None:
    cookie_kwargs = {
        "httponly": settings.cookie_httponly,
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
    }

    if settings.cookie_domain:
        cookie_kwargs["domain"] = settings.cookie_domain

    response.set_cookie(
        key=settings.access_token_cookie_name,
        value=access_token,
        **cookie_kwargs,
    )
    response.set_cookie(
        key=settings.refresh_token_cookie_name,
        value=refresh_token,
        **cookie_kwargs,
    )


def _clear_token_cookies(response: Response) -> None:
    cookie_kwargs = {
        "httponly": settings.cookie_httponly,
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
        "path": "/",
    }

    if settings.cookie_domain:
        cookie_kwargs["domain"] = settings.cookie_domain

    response.delete_cookie(
        key=settings.access_token_cookie_name,
        **cookie_kwargs,
    )
    response.delete_cookie(
        key=settings.refresh_token_cookie_name,
        **cookie_kwargs,
    )


async def verify_token(
    access_token: str | None = Depends(access_token_cookie),
) -> str:
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    user_id = jwt_service.verify_token(access_token, token_type="access")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return user_id


async def get_optional_user_id(
    access_token: str | None = Depends(access_token_cookie),
) -> str | None:
    if not access_token:
        return None

    return jwt_service.verify_token(access_token, token_type="access")


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Email already exists"},
        429: {"description": "Too many requests"},
    },
)
@limiter.limit("5/minute")
async def register(
    request: Request,
    body: RegisterRequest,
    response: Response,
    handler: AuthHandler = Depends(get_auth_handler),
) -> TokenResponse:
    command = RegisterCommand(
        email=body.email,
        password=body.password,
    )

    try:
        tokens = await handler.register(command)
        _set_token_cookies(response, tokens.access_token, tokens.refresh_token)

        return TokenResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
        )
    except EmailAlreadyExistsError:
        raise HTTPException(status_code=400, detail="Email already registered")
    except Exception:
        raise HTTPException(status_code=400, detail="Registration failed")


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        401: {"description": "Invalid credentials"},
        429: {"description": "Too many requests"},
    },
)
@limiter.limit("10/minute")
async def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    handler: AuthHandler = Depends(get_auth_handler),
) -> TokenResponse:
    command = LoginCommand(
        email=body.email,
        password=body.password,
    )

    try:
        tokens = await handler.login(command)
        _set_token_cookies(response, tokens.access_token, tokens.refresh_token)

        return TokenResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
        )
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    responses={
        401: {"description": "Invalid refresh token"},
    },
)
async def refresh_token(
    response: Response,
    refresh_token: str | None = Depends(refresh_token_cookie),
    handler: AuthHandler = Depends(get_auth_handler),
) -> TokenResponse:
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found",
        )

    command = RefreshTokenCommand(refresh_token=refresh_token)

    try:
        tokens = await handler.refresh_tokens(command)
        _set_token_cookies(response, tokens.access_token, tokens.refresh_token)

        return TokenResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout(response: Response) -> None:
    _clear_token_cookies(response)
