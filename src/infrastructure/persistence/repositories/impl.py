from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import ShortUrl, User
from src.domain.repositories import ShortUrlRepository, UserRepository
from src.infrastructure.persistence.models import ShortUrl as ShortUrlModel
from src.infrastructure.persistence.models import User as UserModel


class ShortUrlRepositoryImpl(ShortUrlRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, short_url: ShortUrl) -> ShortUrl:
        model = ShortUrlModel(
            id=short_url.id,
            original_url=short_url.original_url,
            short_code=short_url.short_code,
            owner_id=short_url.owner_id,
            access_count=short_url.access_count,
            expires_at=short_url.expires_at,
            deleted_at=short_url.deleted_at,
            deleted_reason=short_url.deleted_reason,
        )
        self.session.add(model)

        await self.session.flush()

        return self._to_entity(model)

    async def get_by_id(self, id: UUID) -> Optional[ShortUrl]:
        stmt = select(ShortUrlModel).where(
            ShortUrlModel.id == id, ShortUrlModel.deleted_at.is_(None)
        )

        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        return self._to_entity(model) if model else None

    async def get_by_short_code(self, short_code: str) -> Optional[ShortUrl]:
        stmt = select(ShortUrlModel).where(
            ShortUrlModel.short_code == short_code,
            ShortUrlModel.deleted_at.is_(None),
        )

        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        return self._to_entity(model) if model else None

    async def update(self, short_url: ShortUrl) -> ShortUrl:
        stmt = select(ShortUrlModel).where(ShortUrlModel.id == short_url.id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            raise ValueError(f"ShortUrl with id {short_url.id} not found")

        model.original_url = short_url.original_url
        model.access_count = short_url.access_count
        model.updated_at = short_url.updated_at
        model.expires_at = short_url.expires_at
        model.deleted_at = short_url.deleted_at
        model.deleted_reason = short_url.deleted_reason

        await self.session.flush()

        return self._to_entity(model)

    async def delete(self, id: UUID) -> bool:
        stmt = select(ShortUrlModel).where(ShortUrlModel.id == id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return False

        model.deleted_at = datetime.now(timezone.utc)
        model.deleted_reason = "user"
        await self.session.flush()

        return True

    async def exists_by_short_code(self, short_code: str) -> bool:
        stmt = select(ShortUrlModel.id).where(
            ShortUrlModel.short_code == short_code, ShortUrlModel.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)

        return result.scalar_one_or_none() is not None

    async def get_stats(self, short_code: str) -> Optional[dict]:
        stmt = select(
            ShortUrlModel.original_url,
            ShortUrlModel.created_at,
            ShortUrlModel.access_count,
            ShortUrlModel.updated_at,
        ).where(
            ShortUrlModel.short_code == short_code,
            ShortUrlModel.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        row = result.first()

        if not row:
            return None

        return {
            "original_url": row.original_url,
            "created_at": row.created_at,
            "access_count": row.access_count,
            "last_accessed_at": row.updated_at if row.access_count > 0 else None,
        }

    @staticmethod
    def _to_entity(model: ShortUrlModel) -> ShortUrl:
        return ShortUrl(
            id=model.id,
            original_url=model.original_url,
            short_code=model.short_code,
            owner_id=model.owner_id,
            access_count=model.access_count,
            expires_at=model.expires_at,
            deleted_at=getattr(model, "deleted_at", None),
            deleted_reason=getattr(model, "deleted_reason", None),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def get_by_original_url(self, original_url: str) -> Optional[ShortUrl]:
        stmt = select(ShortUrlModel).where(
            ShortUrlModel.original_url == original_url,
            ShortUrlModel.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        return self._to_entity(model) if model else None

    async def delete_expired(self) -> int:
        now = datetime.now(timezone.utc)
        stmt = (
            update(ShortUrlModel)
            .where(
                ShortUrlModel.deleted_at.is_(None),
                ShortUrlModel.expires_at.is_not(None),
                ShortUrlModel.expires_at < now,
            )
            .values(deleted_at=now, deleted_reason="expired", updated_at=now)
            .returning(ShortUrlModel.id)
        )
        result = await self.session.execute(stmt)
        rows = result.fetchall()

        await self.session.flush()

        return len(rows)

    async def get_expired(self, limit: int = 100, offset: int = 0) -> list[ShortUrl]:
        stmt = (
            select(ShortUrlModel)
            .where(
                ShortUrlModel.deleted_reason == "expired",
                ShortUrlModel.deleted_at.is_not(None),
            )
            .order_by(ShortUrlModel.deleted_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    async def count_expired(self) -> int:
        stmt = (
            select(func.count())
            .select_from(ShortUrlModel)
            .where(
                ShortUrlModel.deleted_reason == "expired",
                ShortUrlModel.deleted_at.is_not(None),
            )
        )
        result = await self.session.execute(stmt)

        return result.scalar() or 0

    async def increment_access_and_get(self, short_code: str) -> Optional[ShortUrl]:
        now = datetime.now(timezone.utc)

        stmt = (
            update(ShortUrlModel)
            .where(
                ShortUrlModel.short_code == short_code,
                ShortUrlModel.deleted_at.is_(None),
            )
            .values(access_count=ShortUrlModel.access_count + 1, updated_at=now)
            .returning(
                ShortUrlModel.id,
                ShortUrlModel.original_url,
                ShortUrlModel.short_code,
                ShortUrlModel.owner_id,
                ShortUrlModel.access_count,
                ShortUrlModel.expires_at,
                ShortUrlModel.deleted_at,
                ShortUrlModel.deleted_reason,
                ShortUrlModel.created_at,
                ShortUrlModel.updated_at,
            )
        )
        result = await self.session.execute(stmt)
        row = result.fetchone()

        if not row:
            return None

        await self.session.flush()

        return ShortUrl(
            id=row.id,
            original_url=row.original_url,
            short_code=row.short_code,
            owner_id=row.owner_id,
            access_count=row.access_count,
            expires_at=row.expires_at,
            deleted_at=row.deleted_at,
            deleted_reason=row.deleted_reason,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def get_by_owner(
        self, owner_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[ShortUrl]:
        stmt = (
            select(ShortUrlModel)
            .where(
                ShortUrlModel.owner_id == owner_id,
                ShortUrlModel.deleted_at.is_(None),
            )
            .order_by(ShortUrlModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]


class UserRepositoryImpl(UserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, user: User) -> User:
        model = UserModel(
            id=user.id,
            email=user.email,
            password_hash=user.password_hash,
            is_active=user.is_active,
        )
        self.session.add(model)
        await self.session.flush()

        return self._to_entity(model)

    async def get_by_id(self, id: UUID) -> Optional[User]:
        stmt = select(UserModel).where(UserModel.id == id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        return self._to_entity(model) if model else None

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(UserModel).where(UserModel.email == email)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        return self._to_entity(model) if model else None

    async def update(self, user: User) -> User:
        stmt = select(UserModel).where(UserModel.id == user.id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            raise ValueError(f"User with id {user.id} not found")

        model.email = user.email
        model.is_active = user.is_active
        model.updated_at = user.updated_at

        await self.session.flush()

        return self._to_entity(model)

    async def delete(self, id: UUID) -> bool:
        stmt = select(UserModel).where(UserModel.id == id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return False

        await self.session.delete(model)
        await self.session.flush()

        return True

    @staticmethod
    def _to_entity(model: UserModel) -> User:
        return User(
            id=model.id,
            email=model.email,
            password_hash=model.password_hash,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
