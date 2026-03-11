from typing import Optional

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
from src.application.dto import LinkStatsDto
from src.domain.entities import ShortUrl
from src.domain.repositories import ShortUrlRepository
from src.domain.services import ShortCodeGenerator


class ShortUrlHandler:
    def __init__(
        self,
        repository: ShortUrlRepository,
        code_generator: Optional[ShortCodeGenerator] = None,
    ):
        self.repository = repository
        self.code_generator = code_generator or ShortCodeGenerator()

    async def create(self, command: CreateShortUrlCommand) -> ShortUrl:
        short_code = command.short_code

        if not short_code:
            short_code = self.code_generator.generate()

            while await self.repository.exists_by_short_code(short_code):
                short_code = self.code_generator.generate()
        else:
            if await self.repository.exists_by_short_code(short_code):
                raise ValueError(f"Short code '{short_code}' already exists")

        short_url = ShortUrl(
            original_url=command.original_url,
            short_code=short_code,
            owner_id=command.owner_id,
            expires_at=command.expires_at,
        )

        return await self.repository.add(short_url)

    async def get(self, command: GetShortUrlCommand) -> Optional[ShortUrl]:
        return await self.repository.get_by_short_code(command.short_code)

    async def update(self, command: UpdateShortUrlCommand) -> ShortUrl:
        short_url = await self.repository.get_by_short_code(command.short_code)

        if not short_url:
            raise ValueError(f"Short URL with code {command.short_code} not found")

        if command.user_id is not None and short_url.owner_id != command.user_id:
            raise ValueError("You don't have permission to update this short URL")

        short_url.update_url(command.original_url)

        return await self.repository.update(short_url)

    async def delete(self, command: DeleteShortUrlCommand) -> bool:
        short_url = await self.repository.get_by_short_code(command.short_code)

        if not short_url:
            return False

        if command.user_id is not None and short_url.owner_id != command.user_id:
            raise ValueError("You don't have permission to delete this short URL")

        if command.reason == "expired":
            short_url.mark_deleted("expired")
            await self.repository.update(short_url)

            return True

        return await self.repository.delete(short_url.id)

    async def increment_access(
        self, command: IncrementAccessCommand
    ) -> Optional[ShortUrl]:
        return await self.repository.increment_access_and_get(command.short_code)

    async def get_stats(self, command: GetLinkStatsCommand) -> Optional[LinkStatsDto]:
        stats = await self.repository.get_stats(command.short_code)
        if not stats:
            return None

        return LinkStatsDto(
            original_url=stats["original_url"],
            created_at=stats["created_at"],
            access_count=stats["access_count"],
            last_accessed_at=stats["last_accessed_at"],
        )

    async def get_by_original_url(
        self, command: GetShortUrlByOriginalCommand
    ) -> Optional[ShortUrl]:
        return await self.repository.get_by_original_url(command.original_url)

    async def delete_expired(self) -> int:
        return await self.repository.delete_expired()

    async def get_expired(self, command: GetExpiredLinksCommand) -> list[ShortUrl]:
        return await self.repository.get_expired(
            limit=command.limit, offset=command.offset
        )

    async def count_expired(self) -> int:
        return await self.repository.count_expired()
