from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class MetricDelta:
    """Represents the difference between two metrics."""
    metric_name: str
    old_value: float
    new_value: float
    delta: float
    is_improvement: bool
    unit: str = ""
    # For qualitative/string metrics
    old_label: str = ""
    new_label: str = ""

@dataclass
class ComparisonReport:
    """
    A structured, stroke-agnostic comparison between two analysis sessions.
    Designed to be AI-ready for future natural language generation.
    """
    athlete_id: str
    session_a_id: str
    session_b_id: str
    
    # 1. Overall Performance
    overall_score_delta: Optional[MetricDelta] = None
    
    # 2. Technique Metrics (Stroke-agnostic list of deltas)
    technique_deltas: List[MetricDelta] = field(default_factory=list)
    
    # 3. Scientific Confidence
    confidence_delta: Optional[MetricDelta] = None
    
    # 4. Movement Errors
    resolved_errors: List[str] = field(default_factory=list)
    new_errors: List[str] = field(default_factory=list)
    persistent_errors: List[str] = field(default_factory=list)
    
    # 5. Stroke Statistics
    cycles_delta: Optional[MetricDelta] = None
    cycle_duration_delta: Optional[MetricDelta] = None
    
    # 6. Coach Summary (Can be populated by rules or AI)
    coach_summary: str = ""
    
    # 7. Future Compatibility Fields (Placeholders as requested)
    biomechanical_improvements: List[str] = field(default_factory=list)
    performance_trends: str = ""
    fatigue_indicators: List[str] = field(default_factory=list)
    personalized_coaching_recommendations: List[str] = field(default_factory=list)
    
    # Internal UI references
    video_path_a: str = ""
    video_path_b: str = ""
