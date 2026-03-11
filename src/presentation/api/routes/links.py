from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.responses import RedirectResponse

from src.application.commands import (
    CreateShortUrlCommand,
    DeleteShortUrlCommand,
    GetExpiredLinksCommand,
    GetLinkStatsCommand,
    GetShortUrlByOriginalCommand,
    GetShortUrlCommand,
    IncrementAccessCommand,
    UpdateShortUrlCommand,
)
from src.application.handlers import ShortUrlHandler
from src.domain.services import ShortCodeGenerator
from src.infrastructure.cache_service import ShortUrlCacheService, get_short_url_cache
from src.infrastructure.config import settings
from src.infrastructure.database import get_db
from src.infrastructure.persistence.repositories import ShortUrlRepositoryImpl
from src.presentation.api.routes.auth import get_optional_user_id, verify_token
from src.presentation.api.schemas import (
    CreateLinkRequest,
    ErrorResponse,
    ExpiredLinksResponse,
    LinkResponse,
    LinkStatsResponse,
    UpdateLinkRequest,
)

router = APIRouter(prefix="/links", tags=["links"])
limiter = Limiter(key_func=get_remote_address)


def get_handler(db=Depends(get_db)) -> ShortUrlHandler:
    repository = ShortUrlRepositoryImpl(db)
    code_generator = ShortCodeGenerator(length=settings.short_code_length)

    return ShortUrlHandler(repository, code_generator)


def get_current_user_id(
    user_id: Optional[str] = Depends(get_optional_user_id),
) -> Optional[UUID]:
    if user_id:
        return UUID(user_id)

    return None


def require_authenticated_user(user_id: str = Depends(verify_token)) -> UUID:
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UUID(user_id)


@router.post(
    "/shorten",
    response_model=LinkResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid URL"},
        409: {"model": ErrorResponse, "description": "Short code already exists"},
        429: {"description": "Too many requests"},
    },
)
@limiter.limit("20/minute")
async def shorten_url(
    request: Request,
    body: CreateLinkRequest,
    handler: ShortUrlHandler = Depends(get_handler),
    cache_service: ShortUrlCacheService = Depends(get_short_url_cache),
    user_id: Optional[UUID] = Depends(get_current_user_id),
) -> LinkResponse:
    command = CreateShortUrlCommand(
        original_url=str(body.url),
        owner_id=user_id,
        short_code=body.custom_alias,
        expires_at=body.expires_at,
    )

    try:
        short_url = await handler.create(command)
        await cache_service.set_short_url(short_url)

        return LinkResponse(
            id=short_url.id,
            short_code=short_url.short_code,
            original_url=short_url.original_url,
            short_url=f"{settings.short_url_base}/links/{short_url.short_code}",
            access_count=short_url.access_count,
            expires_at=short_url.expires_at,
            created_at=short_url.created_at,
            updated_at=short_url.updated_at,
        )
    except ValueError as e:
        error_message = str(e)

        if "already exists" in error_message:
            raise HTTPException(status_code=409, detail=error_message)
        raise HTTPException(status_code=400, detail=error_message)


@router.get(
    "/search",
    response_model=LinkResponse,
    responses={404: {"model": ErrorResponse}},
)
async def search_by_original_url(
    original_url: str = Query(..., description="Original URL to search for"),
    handler: ShortUrlHandler = Depends(get_handler),
) -> LinkResponse:
    command = GetShortUrlByOriginalCommand(original_url=original_url)

    short_url = await handler.get_by_original_url(command)

    if not short_url:
        raise HTTPException(status_code=404, detail="Short URL not found")

    return LinkResponse(
        id=short_url.id,
        short_code=short_url.short_code,
        original_url=short_url.original_url,
        short_url=f"{settings.short_url_base}/links/{short_url.short_code}",
        access_count=short_url.access_count,
        expires_at=short_url.expires_at,
        created_at=short_url.created_at,
        updated_at=short_url.updated_at,
    )


@router.get(
    "/expired",
    response_model=ExpiredLinksResponse,
)
async def get_expired_links(
    limit: int = Query(
        default=100, ge=1, le=1000, description="Maximum number of links to return"
    ),
    offset: int = Query(default=0, ge=0, description="Number of links to skip"),
    handler: ShortUrlHandler = Depends(get_handler),
) -> ExpiredLinksResponse:
    total = await handler.count_expired()

    command = GetExpiredLinksCommand(limit=limit, offset=offset)
    expired_links = await handler.get_expired(command)

    return ExpiredLinksResponse(
        links=[
            LinkResponse(
                id=link.id,
                short_code=link.short_code,
                original_url=link.original_url,
                short_url=f"{settings.short_url_base}/links/{link.short_code}",
                access_count=link.access_count,
                expires_at=link.expires_at,
                created_at=link.created_at,
                updated_at=link.updated_at,
            )
            for link in expired_links
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{short_code}",
    responses={404: {"model": ErrorResponse}},
)
async def redirect_by_short_code(
    short_code: str,
    handler: ShortUrlHandler = Depends(get_handler),
    cache_service: ShortUrlCacheService = Depends(get_short_url_cache),
) -> RedirectResponse:
    short_url = await cache_service.get_short_url(short_code)

    if not short_url:
        command = GetShortUrlCommand(short_code=short_code)
        short_url = await handler.get(command)

        if not short_url:
            raise HTTPException(status_code=404, detail="Short URL not found")

        await cache_service.set_short_url(short_url)

    if short_url.is_deleted():
        await cache_service.invalidate_short_url(short_code)
        raise HTTPException(status_code=404, detail="Short URL not found")

    if short_url.is_expired():
        await handler.delete(
            DeleteShortUrlCommand(short_code=short_code, reason="expired")
        )
        await cache_service.invalidate_short_url(short_code)
        raise HTTPException(status_code=404, detail="Short URL has expired")

    original_url = short_url.original_url

    updated_short_url = await handler.increment_access(
        IncrementAccessCommand(short_code=short_code)
    )

    if updated_short_url:
        await cache_service.set_short_url(updated_short_url)
        await cache_service.delete_stats(short_code)

    return RedirectResponse(url=original_url)


@router.put(
    "/{short_code}",
    response_model=LinkResponse,
    responses={
        404: {"model": ErrorResponse},
        403: {"model": ErrorResponse, "description": "Permission denied"},
    },
)
async def update_link(
    short_code: str,
    request: UpdateLinkRequest,
    handler: ShortUrlHandler = Depends(get_handler),
    cache_service: ShortUrlCacheService = Depends(get_short_url_cache),
    user_id: UUID = Depends(require_authenticated_user),
) -> LinkResponse:
    command = UpdateShortUrlCommand(
        short_code=short_code,
        original_url=str(request.url),
        user_id=user_id,
    )

    try:
        short_url = await handler.update(command)
        await cache_service.invalidate_short_url(short_code)

        return LinkResponse(
            id=short_url.id,
            short_code=short_url.short_code,
            original_url=short_url.original_url,
            short_url=f"{settings.short_url_base}/links/{short_url.short_code}",
            access_count=short_url.access_count,
            expires_at=short_url.expires_at,
            created_at=short_url.created_at,
            updated_at=short_url.updated_at,
        )
    except ValueError as e:
        error_message = str(e)
        if "permission" in error_message.lower():
            raise HTTPException(status_code=403, detail=error_message)
        raise HTTPException(status_code=404, detail=error_message)


@router.delete(
    "/{short_code}",
    status_code=204,
    responses={
        404: {"model": ErrorResponse},
        403: {"model": ErrorResponse, "description": "Permission denied"},
    },
)
async def delete_link(
    short_code: str,
    handler: ShortUrlHandler = Depends(get_handler),
    cache_service: ShortUrlCacheService = Depends(get_short_url_cache),
    user_id: UUID = Depends(require_authenticated_user),
) -> None:
    command = DeleteShortUrlCommand(short_code=short_code, user_id=user_id)

    try:
        deleted = await handler.delete(command)

        if not deleted:
            raise HTTPException(status_code=404, detail="Short URL not found")

        await cache_service.invalidate_short_url(short_code)
    except ValueError as e:
        error_message = str(e)

        if "permission" in error_message.lower():
            raise HTTPException(status_code=403, detail=error_message)

        raise HTTPException(status_code=404, detail=error_message)


@router.get(
    "/{short_code}/stats",
    response_model=LinkStatsResponse,
    responses={
        404: {"model": ErrorResponse},
        401: {"model": ErrorResponse, "description": "Authentication required"},
    },
)
async def get_link_stats(
    short_code: str,
    handler: ShortUrlHandler = Depends(get_handler),
    cache_service: ShortUrlCacheService = Depends(get_short_url_cache),
    user_id: UUID = Depends(require_authenticated_user),
) -> LinkStatsResponse:
    cached_stats = await cache_service.get_stats(short_code)

    if cached_stats:
        return LinkStatsResponse(
            original_url=cached_stats["original_url"],
            created_at=cached_stats["created_at"],
            access_count=cached_stats["access_count"],
            last_accessed_at=cached_stats["last_accessed_at"],
        )

    command = GetLinkStatsCommand(short_code=short_code)
    stats = await handler.get_stats(command)

    if not stats:
        raise HTTPException(status_code=404, detail="Short URL not found")

    await cache_service.set_stats(
        short_code,
        {
            "original_url": stats.original_url,
            "created_at": stats.created_at,
            "access_count": stats.access_count,
            "last_accessed_at": stats.last_accessed_at,
        },
    )

    return LinkStatsResponse(
        original_url=stats.original_url,
        created_at=stats.created_at,
        access_count=stats.access_count,
        last_accessed_at=stats.last_accessed_at,
    )


@router.post(
    "/cleanup",
    response_model=dict,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
    },
)
async def cleanup_expired_links(
    handler: ShortUrlHandler = Depends(get_handler),
    cache_service: ShortUrlCacheService = Depends(get_short_url_cache),
    user_id: UUID = Depends(require_authenticated_user),
) -> dict:
    expired_links = await handler.get_expired(GetExpiredLinksCommand(limit=1000))
    expired_short_codes = [link.short_code for link in expired_links]

    deleted_count = await handler.delete_expired()

    for short_code in expired_short_codes:
        await cache_service.invalidate_short_url(short_code)

    return {"deleted_count": deleted_count}
