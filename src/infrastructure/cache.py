import json
import logging
from datetime import datetime
from typing import Any, Optional

from redis.asyncio import Redis

from .config import settings

logger = logging.getLogger(__name__)

DEFAULT_TTL = 300
SHORT_URL_TTL = 600
STATS_TTL = 60

SHORT_URL_KEY_PREFIX = "short_url:"
STATS_KEY_PREFIX = "stats:"


class RedisCache:
    def __init__(self):
        self._redis: Optional[Redis] = None

    async def connect(self) -> None:
        self._redis = Redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()
            self._redis = None

    @property
    def is_connected(self) -> bool:
        return self._redis is not None

    async def get(self, key: str) -> Optional[Any]:
        if not self._redis:
            return None
        try:
            value = await self._redis.get(key)

            if value is None:
                return None

            return json.loads(value)
        except Exception as e:
            logger.warning("Redis GET error for key '%s': %s", key, e)

            return None

    async def set(self, key: str, value: Any, ttl: int = DEFAULT_TTL) -> bool:
        if not self._redis:
            return False
        try:
            serialized = json.dumps(value, default=self._json_serializer)
            await self._redis.setex(key, ttl, serialized)

            return True
        except Exception as e:
            logger.warning("Redis SET error for key '%s': %s", key, e)

            return False

    async def delete(self, key: str) -> bool:
        if not self._redis:
            return False
        try:
            await self._redis.delete(key)

            return True
        except Exception as e:
            logger.warning("Redis DELETE error for key '%s': %s", key, e)

            return False

    async def delete_pattern(self, pattern: str) -> int:
        if not self._redis:
            return 0
        try:
            keys = await self._redis.keys(pattern)

            if keys:
                return await self._redis.delete(*keys)

            return 0
        except Exception as e:
            logger.warning(
                "Redis DELETE_PATTERN error for pattern '%s': %s", pattern, e
            )

            return 0

    async def exists(self, key: str) -> bool:
        if not self._redis:
            return False
        try:
            return bool(await self._redis.exists(key))
        except Exception as e:
            logger.warning("Redis EXISTS error for key '%s': %s", key, e)

            return False

    @staticmethod
    def _json_serializer(obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()

        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    @staticmethod
    def _json_deserializer(data: dict[str, Any]) -> dict[str, Any]:
        for key, value in data.items():
            if key.endswith("_at") and isinstance(value, str):
                try:
                    data[key] = datetime.fromisoformat(value.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass

        return data


cache = RedisCache()


async def get_cache() -> RedisCache:
    return cache
