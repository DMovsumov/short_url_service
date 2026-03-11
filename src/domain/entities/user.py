from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


@dataclass
class User:
    email: str
    password_hash: str
    id: UUID = field(default_factory=uuid4)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(cls, email: str, password: str, **kwargs) -> "User":
        password_hash = _pwd_context.hash(password)

        return cls(
            email=email,
            password_hash=password_hash,
            **kwargs,
        )

    def verify_password(self, password: str) -> bool:
        return _pwd_context.verify(password, self.password_hash)

    def deactivate(self) -> None:
        self.is_active = False
        self.updated_at = datetime.utcnow()
