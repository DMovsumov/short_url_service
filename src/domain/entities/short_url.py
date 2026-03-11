from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4


@dataclass
class ShortUrl:
    original_url: str
    short_code: str
    id: UUID = field(default_factory=uuid4)
    owner_id: Optional[UUID] = None
    access_count: int = 0
    expires_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    deleted_reason: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def increment_access(self) -> None:
        self.access_count += 1
        self.updated_at = datetime.now(timezone.utc)

    def mark_deleted(self, reason: str) -> None:
        now = datetime.now(timezone.utc)
        self.deleted_at = now
        self.deleted_reason = reason
        self.updated_at = now

    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False

        now = datetime.now(timezone.utc)
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        return now > expires_at

    def update_url(self, new_url: str) -> None:
        self.original_url = new_url
        self.updated_at = datetime.now(timezone.utc)
