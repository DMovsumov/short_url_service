from typing import Optional
from uuid import UUID

from src.domain.entities import ShortUrl

from .cache import (
    SHORT_URL_KEY_PREFIX,
    SHORT_URL_TTL,
    STATS_KEY_PREFIX,
    STATS_TTL,
    cache,
)


class ShortUrlCacheService:
    @staticmethod
    def _get_short_url_key(short_code: str) -> str:
        return f"{SHORT_URL_KEY_PREFIX}{short_code}"

    @staticmethod
    def _get_stats_key(short_code: str) -> str:
        return f"{STATS_KEY_PREFIX}{short_code}"

    @staticmethod
    def _entity_to_dict(short_url: ShortUrl) -> dict:
        return {
            "id": str(short_url.id),
            "original_url": short_url.original_url,
            "short_code": short_url.short_code,
            "owner_id": str(short_url.owner_id) if short_url.owner_id else None,
            "access_count": short_url.access_count,
            "expires_at": short_url.expires_at,
            "deleted_at": short_url.deleted_at,
            "deleted_reason": short_url.deleted_reason,
            "created_at": short_url.created_at,
            "updated_at": short_url.updated_at,
        }

    @staticmethod
    def _dict_to_entity(data: dict) -> ShortUrl:
        return ShortUrl(
            id=UUID(data["id"]),
            original_url=data["original_url"],
            short_code=data["short_code"],
            owner_id=UUID(data["owner_id"]) if data.get("owner_id") else None,
            access_count=data["access_count"],
            expires_at=data["expires_at"],
            deleted_at=data["deleted_at"],
            deleted_reason=data["deleted_reason"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )

    async def get_short_url(self, short_code: str) -> Optional[ShortUrl]:
        key = self._get_short_url_key(short_code)
        data = await cache.get(key)

        if data:
            data = cache._json_deserializer(data)

            return self._dict_to_entity(data)

        return None

    async def set_short_url(
        self, short_url: ShortUrl, ttl: int = SHORT_URL_TTL
    ) -> bool:
        key = self._get_short_url_key(short_url.short_code)
        data = self._entity_to_dict(short_url)

        return await cache.set(key, data, ttl)

    async def delete_short_url(self, short_code: str) -> bool:
        key = self._get_short_url_key(short_code)

        return await cache.delete(key)

    async def get_stats(self, short_code: str) -> Optional[dict]:
        key = self._get_stats_key(short_code)
        data = await cache.get(key)

        if data:
            return cache._json_deserializer(data)

        return None

    async def set_stats(
        self, short_code: str, stats: dict, ttl: int = STATS_TTL
    ) -> bool:
        key = self._get_stats_key(short_code)

        return await cache.set(key, stats, ttl)

    async def delete_stats(self, short_code: str) -> bool:
        key = self._get_stats_key(short_code)

        return await cache.delete(key)

    async def invalidate_short_url(self, short_code: str) -> None:
        await self.delete_short_url(short_code)
        await self.delete_stats(short_code)


short_url_cache = ShortUrlCacheService()


async def get_short_url_cache() -> ShortUrlCacheService:
    return short_url_cache
