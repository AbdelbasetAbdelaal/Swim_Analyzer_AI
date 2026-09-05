import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional

@dataclass
class AnalysisSession:
    """Represents a single completed video analysis session."""
    athlete_id: Optional[str]
    analysis_timestamp: str
    original_video_filename: str
    processed_video_filename: str
    metadata_json_path: str
    report_json_path: str
    performance_score: Optional[float]  # None = INSUFFICIENT_EVIDENCE (no complete cycle detected)
    scientific_confidence: str
    completed_cycles: int
    stroke_type: str
    processing_time_seconds: float
    account_id: str
    benchmark_summary_json: Optional[str] = None
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'AnalysisSession':
        # Remove any unexpected keys for forward compatibility
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered_data)
