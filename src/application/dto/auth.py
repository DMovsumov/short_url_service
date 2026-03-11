from dataclasses import dataclass
from uuid import UUID


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str


@dataclass
class UserAuthDto:
    id: UUID
    email: str
