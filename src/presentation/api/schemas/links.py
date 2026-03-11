from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, field_validator


class CreateLinkRequest(BaseModel):
    url: HttpUrl = Field(..., description="Original URL to shorten")
    custom_alias: Optional[str] = Field(
        default=None,
        min_length=4,
        max_length=10,
        pattern=r"^[a-zA-Z0-9]+$",
        description="Custom short code (optional, unique alias)",
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Expiration time (ISO 8601 format, minute precision)",
    )

    @field_validator("expires_at")
    @classmethod
    def _ensure_minute_precision(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is None:

            return None
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        else:
            v = v.astimezone(timezone.utc)

        return v.replace(second=0, microsecond=0)


class UpdateLinkRequest(BaseModel):
    url: HttpUrl = Field(..., description="New original URL")


class LinkResponse(BaseModel):
    id: UUID
    short_code: str
    original_url: str
    short_url: str
    access_count: int
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RedirectResponse(BaseModel):
    short_code: str
    original_url: str
    access_count: int


class LinkStatsResponse(BaseModel):
    original_url: str
    created_at: datetime
    access_count: int
    last_accessed_at: Optional[datetime] = None


class ErrorResponse(BaseModel):
    detail: str


class ExpiredLinksResponse(BaseModel):
    links: list[LinkResponse]
    total: int
    limit: int
    offset: int
