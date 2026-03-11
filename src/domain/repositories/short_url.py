from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from src.domain.entities import ShortUrl


class ShortUrlRepository(ABC):
    @abstractmethod
    async def add(self, short_url: ShortUrl) -> ShortUrl: ...

    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[ShortUrl]: ...

    @abstractmethod
    async def get_by_short_code(self, short_code: str) -> Optional[ShortUrl]: ...

    @abstractmethod
    async def update(self, short_url: ShortUrl) -> ShortUrl: ...

    @abstractmethod
    async def delete(self, id: UUID) -> bool: ...

    @abstractmethod
    async def exists_by_short_code(self, short_code: str) -> bool: ...

    @abstractmethod
    async def get_stats(self, short_code: str) -> Optional[dict]: ...

    @abstractmethod
    async def get_by_original_url(self, original_url: str) -> Optional[ShortUrl]: ...

    @abstractmethod
    async def delete_expired(self) -> int: ...

    @abstractmethod
    async def get_expired(
        self, limit: int = 100, offset: int = 0
    ) -> list[ShortUrl]: ...

    @abstractmethod
    async def count_expired(self) -> int: ...

    @abstractmethod
    async def increment_access_and_get(self, short_code: str) -> Optional[ShortUrl]: ...

    @abstractmethod
    async def get_by_owner(
        self, owner_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[ShortUrl]: ...
