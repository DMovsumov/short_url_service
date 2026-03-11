from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class CreateShortUrlCommand:
    original_url: str
    owner_id: Optional[UUID] = None
    short_code: Optional[str] = None
    expires_at: Optional[datetime] = None


@dataclass
class UpdateShortUrlCommand:
    short_code: str
    original_url: str
    user_id: Optional[UUID] = None


@dataclass
class DeleteShortUrlCommand:
    short_code: str
    reason: str = "user"
    user_id: Optional[UUID] = None


@dataclass
class GetShortUrlCommand:
    short_code: str


@dataclass
class IncrementAccessCommand:
    short_code: str


@dataclass
class GetLinkStatsCommand:
    short_code: str


@dataclass
class GetShortUrlByOriginalCommand:
    original_url: str


@dataclass
class GetExpiredLinksCommand:
    limit: int = 100
    offset: int = 0
