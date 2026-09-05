from dataclasses import dataclass, field
from typing import Optional
import uuid

@dataclass
class AthleteProfile:
    full_name: str
    age: int
    gender: str
    height_cm: float
    weight_kg: float
    swimming_level: str
    preferred_stroke: str
    coach_id: str
    athlete_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    shoulder_width_cm: Optional[float] = None
    notes: str = ""
    training_goals: str = ""
    swimmer_tags: list = field(default_factory=list)
    schema_version: str = "1.0"

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "athlete_id": self.athlete_id,
            "coach_id": self.coach_id,
            "full_name": self.full_name,
            "age": self.age,
            "gender": self.gender,
            "height_cm": self.height_cm,
            "weight_kg": self.weight_kg,
            "shoulder_width_cm": self.shoulder_width_cm,
            "swimming_level": self.swimming_level,
            "preferred_stroke": self.preferred_stroke,
            "notes": self.notes,
            "training_goals": self.training_goals,
            "swimmer_tags": self.swimmer_tags
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'AthleteProfile':
        return cls(
            coach_id=data["coach_id"],
            athlete_id=data.get("athlete_id", str(uuid.uuid4())),
            full_name=data["full_name"],
            age=data["age"],
            gender=data["gender"],
            height_cm=data["height_cm"],
            weight_kg=data["weight_kg"],
            shoulder_width_cm=data.get("shoulder_width_cm"),
            swimming_level=data.get("swimming_level", "Beginner"),
            preferred_stroke=data.get("preferred_stroke", "Freestyle"),
            notes=data.get("notes", ""),
            training_goals=data.get("training_goals", ""),
            swimmer_tags=data.get("swimmer_tags", []),
            schema_version=data.get("schema_version", "1.0")
        )
