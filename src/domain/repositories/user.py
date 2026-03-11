from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from src.domain.entities import User


class UserRepository(ABC):
    @abstractmethod
    async def add(self, user: User) -> User: ...

    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[User]: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]: ...

    @abstractmethod
    async def update(self, user: User) -> User: ...

    @abstractmethod
    async def delete(self, id: UUID) -> bool: ...
