import json
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class PhaseEvent:
    frame: int
    phase: str

@dataclass
class Labels:
    stroke_rate: float
    stroke_length: float
    body_roll: float
    kick_frequency: float
    stroke_cycles: int
    events: List[PhaseEvent]
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Labels':
        events = [PhaseEvent(**e) for e in data.get('events', [])]
        return cls(
            stroke_rate=float(data.get('stroke_rate', 0.0)),
            stroke_length=float(data.get('stroke_length', 0.0)),
            body_roll=float(data.get('body_roll', 0.0)),
            kick_frequency=float(data.get('kick_frequency', 0.0)),
            stroke_cycles=int(data.get('stroke_cycles', 0)),
            events=events
        )

class ReferenceLoader:
    @staticmethod
    def load(file_path: str) -> Labels:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return Labels.from_dict(data)
