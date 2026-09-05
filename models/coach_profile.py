from dataclasses import dataclass, field
from typing import Optional
import uuid

@dataclass
class CoachProfile:
    username: str
    password_hash: str
    salt: str
    full_name: str
    role: str = "coach"
    email: Optional[str] = None
    coach_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "coach_id": self.coach_id,
            "username": self.username,
            "password_hash": self.password_hash,
            "salt": self.salt,
            "full_name": self.full_name,
            "role": self.role,
            "email": self.email,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'CoachProfile':
        return cls(
            coach_id=data.get("coach_id", str(uuid.uuid4())),
            username=data["username"],
            password_hash=data["password_hash"],
            salt=data["salt"],
            full_name=data.get("full_name", data["username"]),
            role=data.get("role", "coach"),
            email=data.get("email"),
            created_at=data.get("created_at", "")
        )
