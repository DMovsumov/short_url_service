from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class CreateShortUrlDto:
    original_url: str
    short_code: Optional[str] = None
    expires_at: Optional[datetime] = None


@dataclass
class UpdateShortUrlDto:
    original_url: str


@dataclass
class ShortUrlDto:
    id: UUID
    short_code: str
    original_url: str
    access_count: int
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    owner_id: Optional[UUID] = None
