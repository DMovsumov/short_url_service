import asyncio
import contextlib
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.infrastructure.cache import cache
from src.infrastructure.config import settings
from src.infrastructure.database import async_session_factory, close_db, init_db
from src.infrastructure.persistence.repositories import ShortUrlRepositoryImpl
from src.infrastructure.rate_limit import limiter
from src.presentation.api.routes import auth_router, links_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await init_db()
    await cache.connect()
    stop_event = asyncio.Event()

    async def expire_worker() -> None:
        while not stop_event.is_set():
            try:
                async with async_session_factory() as session:
                    repo = ShortUrlRepositoryImpl(session)
                    await repo.delete_expired()
                    await session.commit()
            except Exception as e:
                logger.exception("Error in expire worker: %s", e)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=60)
            except asyncio.TimeoutError:
                continue

    task = asyncio.create_task(expire_worker())
    yield
    stop_event.set()
    task.cancel()
    with contextlib.suppress(Exception):
        await task
    await cache.close()
    await close_db()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="Short URL service with DDD architecture",
        version="0.1.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    allowed_origins = [
        origin.strip()
        for origin in settings.cors_allow_origins.split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "healthy"}

    app.include_router(auth_router, prefix=settings.api_prefix)
    app.include_router(links_router, prefix=settings.api_prefix)

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
