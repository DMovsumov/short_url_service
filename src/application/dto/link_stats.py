from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class LinkStatsDto:
    original_url: str
    created_at: datetime
    access_count: int
    last_accessed_at: Optional[datetime] = None
