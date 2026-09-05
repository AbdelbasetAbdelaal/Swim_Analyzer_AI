"""
Domain models for structured data passing across layers.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum

class StrokeType(str, Enum):
    AUTO_DETECT = "Auto Detect"
    FREESTYLE = "Freestyle"
    BACKSTROKE = "Backstroke"
    BREASTSTROKE = "Breaststroke"
    BUTTERFLY = "Butterfly"
    UNKNOWN = "Unknown"

@dataclass
class StrokeDetectionResult:
    predicted_stroke: StrokeType = StrokeType.UNKNOWN
    confidence: Optional[float] = None
    predictions: Dict[str, float] = field(default_factory=dict)
    selected_stroke: StrokeType = StrokeType.AUTO_DETECT
    manual_override: bool = False
    is_inconsistent: bool = False
    classification_status: str = "INSUFFICIENT_EVIDENCE" # "ACCEPTED", "MODERATE_CONFIDENCE", "INSUFFICIENT_EVIDENCE", "INSUFFICIENT_VISIBILITY", "REVIEW_REQUIRED", "UNKNOWN"
    classification_reason: str = ""
    feature_values: Dict[str, Any] = field(default_factory=dict)
    feature_contributions: Dict[str, float] = field(default_factory=dict)
    classifier_version: str = "2.0.0-Hybrid-Engine"
    threshold_version: str = "HYBRID_DECISION_v2.0"
    
    # Scientific Decision Contract Fields
    confidence_type: str = "UNCALIBRATED_DECISION_SCORE"
    uncertainty: Optional[float] = None
    rule_prediction: Optional[StrokeType] = None
    ai_prediction: Optional[StrokeType] = None
    agreement: Optional[bool] = None
    evidence: Dict[str, Any] = field(default_factory=dict)
    missing_evidence: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    method: str = "HYBRID_FUSION"

    def to_decision_contract(self) -> Dict[str, Any]:
        """Returns the machine-readable scientific decision contract dictionary."""
        return {
            "stroke_detection": {
                "prediction": self.predicted_stroke.value if self.predicted_stroke else "Unknown",
                "status": self.classification_status,
                "confidence": round(self.confidence, 4) if self.confidence is not None else None,
                "confidence_type": self.confidence_type,
                "uncertainty": round(self.uncertainty, 4) if self.uncertainty is not None else None,
                "rule_prediction": self.rule_prediction.value if self.rule_prediction else None,
                "ai_prediction": self.ai_prediction.value if self.ai_prediction else None,
                "agreement": self.agreement,
                "evidence": self.evidence,
                "missing_evidence": self.missing_evidence,
                "conflicts": self.conflicts,
                "method": self.method,
                "classifier_version": self.classifier_version
            }
        }

@dataclass
class ValidatedMetric:
    """A generic metric with confidence, reliability, validation status, and measurement domain."""
    name: str = ""
    value: Optional[float] = None
    unit: str = ""
    measurement_domain: str = "unavailable" # "calibrated_physical", "relative_body_normalized", "pose_relative_3d", "image_space", "unavailable"
    status: str = "available" # "available", "unavailable", "low_confidence", "insufficient_evidence"
    confidence: float = 1.0
    reliability: float = 1.0
    valid: bool = True
    is_estimated: bool = False
    is_insufficient_data: bool = False
    reason_if_invalid: str = ""
    calibration_required: bool = False
    calibration_status: str = "uncalibrated" # "calibrated", "uncalibrated", "missing", "invalid"
    method: str = "computed"
    dependencies: List[str] = field(default_factory=list)

    def format_display_value(self) -> str:
        """Returns domain-aware formatted representation (P1-8)."""
        if getattr(self, 'is_insufficient_data', False) or not self.valid or self.value is None:
            return "N/A"
        domain = getattr(self, 'measurement_domain', 'unavailable')
        val = self.value
        unit = getattr(self, 'unit', '')
        if domain == "calibrated_physical":
            unit_str = f" {unit}" if unit else " m"
            return f"{val:.2f}{unit_str}"
        elif domain == "relative_body_normalized":
            return f"{val:.2f} body-length units"
        elif domain == "image_space":
            unit_str = f" {unit}" if unit else " px"
            return f"{val:.1f}{unit_str}"
        elif domain == "pose_relative" or domain == "pose_relative_3d":
            return f"{val:.1f}°" if "deg" in unit.lower() or "°" in unit else f"{val:.2f} (rel)"
        else:
            if unit:
                return f"{val:.1f} {unit}"
            return f"{val:.1f}"

@dataclass
class StrokeEvent:
    """Canonical stroke phase event."""
    stroke: str = "Unknown"
    phase: str = "Unknown"
    start_frame: int = 0
    end_frame: int = 0
    start_time_sec: float = 0.0
    end_time_sec: float = 0.0
    confidence: float = 1.0
    detection_method: str = "heuristic"  # "heuristic", "model", "manual"
    validity: bool = True
    reason: str = ""

    
@dataclass
class JointAngles:
    """Holds calculated angles for key joints in degrees and 3D spatial metrics."""
    left_elbow: Optional[ValidatedMetric] = None
    right_elbow: Optional[ValidatedMetric] = None
    left_knee: Optional[ValidatedMetric] = None
    right_knee: Optional[ValidatedMetric] = None
    left_shoulder: Optional[ValidatedMetric] = None
    right_shoulder: Optional[ValidatedMetric] = None
    left_hip: Optional[ValidatedMetric] = None
    right_hip: Optional[ValidatedMetric] = None
    body_roll: Optional[ValidatedMetric] = None
    # 3D Pose Analytics
    body_roll_3d: Optional[ValidatedMetric] = None
    core_torsion_3d: Optional[ValidatedMetric] = None
    hand_depth_left_3d: Optional[ValidatedMetric] = None
    hand_depth_right_3d: Optional[ValidatedMetric] = None

@dataclass
class VideoMetadata:
    """Stores metadata about the processed video and analysis environment."""
    filename: str = ""
    resolution_width: int = 0
    resolution_height: int = 0
    duration_seconds: float = 0.0
    total_frames: int = 0
    detected_fps: float = 0.0
    effective_fps: float = 0.0
    analysis_timestamp: str = ""
    swimming_style: str = "Freestyle"
    stroke_detection: Optional[StrokeDetectionResult] = None
    processing_time_sec: float = 0.0
    peak_ram_mb: float = 0.0
    peak_cpu_percent: float = 0.0
    average_processing_fps: float = 0.0
    calibration_mode: str = "Unknown"
    confidence_statistics: dict = field(default_factory=dict)
    software_version: str = "1.0.0"
    athlete_id: Optional[str] = None

@dataclass
class VQACriterionResult:
    """Result of a single VQA criterion evaluation."""
    name: str
    score: int
    weight: float
    passed: bool
    explanation_matters: str
    explanation_effect: str
    explanation_fix: str
    
@dataclass
class VQAResult:
    """Stores the complete diagnostic report of the Video Quality Assessment."""
    overall_score: int = 0
    analysis_confidence: str = "High"
    quality_class: str = "Unknown"  # Excellent, Good, Fair, Poor, Critical
    passed: bool = False  # False only if Critical
    warning_message: str = ""
    criteria: List[VQACriterionResult] = field(default_factory=list)
    
@dataclass
class PhaseTransition:
    """Logs a transition between stroke phases."""
    frame_index: int
    timestamp_ms: int
    from_phase: str
    to_phase: str
    reason: str
    confidence: float = 1.0
    
@dataclass
class StrokeStatistics:
    """Statistics about stroke phases across the video."""
    time_in_phases: Dict[str, float] = field(default_factory=lambda: {"Entry": 0.0, "Catch": 0.0, "Pull": 0.0, "Push": 0.0, "Recovery": 0.0, "Unknown": 0.0})
    completed_cycles: int = 0
    average_cycle_duration_ms: float = 0.0
    average_phase_confidence: float = 0.0
    transitions: List[PhaseTransition] = field(default_factory=list)

@dataclass
class FrameData:
    """Represents all analyzed data for a single video frame."""
    frame_index: int
    timestamp_ms: int
    raw_landmarks: Any  # MediaPipe landmarks object or normalized list
    is_valid: bool = True  # Flag if confidence is below threshold
    angles: JointAngles = field(default_factory=JointAngles)
    stroke_phase: str = "Unknown"
    phase_confidence: float = 0.0
    
@dataclass
class MovementError:
    """Represents a specific detected technique flaw."""
    frame_index: int
    timestamp_ms: int
    error_type: str
    description: str
    severity: str  # e.g., 'Low', 'Medium', 'High'
    confidence: float = 1.0
    supporting_metrics: dict = field(default_factory=dict)

@dataclass
class PerformanceReport:
    """Aggregates the overall performance score and all detected errors.
    overall_score=None means the score is INSUFFICIENT_EVIDENCE or METRIC_UNAVAILABLE.
    """
    overall_score: Optional[float] = None  # None = insufficient evidence, never default to 100.0
    status: str = "available"  # "available", "insufficient_evidence", "metric_unavailable"
    stroke_rate: ValidatedMetric = field(default_factory=ValidatedMetric)
    stroke_length: ValidatedMetric = field(default_factory=ValidatedMetric)
    kick_frequency: ValidatedMetric = field(default_factory=ValidatedMetric)
    stroke_symmetry: ValidatedMetric = field(default_factory=ValidatedMetric)
    errors: List[MovementError] = field(default_factory=list)
    feedback_summary: str = ""
    # Evidence sufficiency & component coverage (P0-2, P0-3, P0-12)
    evidence_sufficiency: str = "INSUFFICIENT"  # "INSUFFICIENT", "LIMITED", "SUFFICIENT"
    technique_assessment: str = "INSUFFICIENT EVIDENCE"  # "INSUFFICIENT EVIDENCE", "LIMITED EVIDENCE", or evaluated tier
    available_components: List[str] = field(default_factory=list)
    unavailable_components: List[str] = field(default_factory=list)
    total_components_count: int = 0

@dataclass
class StrokeSelection:
    """Authoritative single source of truth for user stroke selection."""
    selected_stroke: StrokeType
    selection_source: str = "USER"

    def to_dict(self) -> dict:
        stroke_val = self.selected_stroke.value if hasattr(self.selected_stroke, 'value') else str(self.selected_stroke)
        return {
            "selected_stroke": stroke_val,
            "selection_source": self.selection_source
        }

@dataclass
class ReliabilityResult:
    """Contains transparent, documented metrics for Video Analysis Reliability."""
    analysis_reliability_score: float = 100.0  # 0-100%
    analysis_reliability_level: str = "High"  # Low, Medium, High
    scientific_confidence: str = "High"  # High, Medium, Low
    confidence_status: str = "High Reliability"  # High Reliability, Moderate Reliability, Low Reliability
    
    # Decoupled measurement reliability & scientific validation status (P1-6)
    measurement_reliability_score: float = 100.0
    measurement_reliability_level: str = "High"
    scientific_validation_status: str = "NOT_VALIDATED — INSUFFICIENT GROUND TRUTH"

    # Detailed transparent breakdown components (P1-7)
    pose_tracking_coverage_pct: float = 100.0
    frame_coverage_pct: float = 100.0
    pose_validity_pct: float = 100.0
    landmark_visibility_pct: float = 100.0
    temporal_stability_pct: float = 100.0
    cycle_quality_pct: float = 100.0
    measurement_stability_pct: float = 100.0
    
    # Legacy compatibility fields
    analysis_confidence_score: float = 100.0
    analysis_confidence_level: str = "High"
    
    reasons: List[str] = field(default_factory=list)

@dataclass
class ConsistencyReport:
    """Final layer validation to ensure scientific trustworthiness of the report.
    overall_score=None propagates INSUFFICIENT_EVIDENCE from upstream scoring engines.
    """
    overall_score: Optional[float] = None  # None = INSUFFICIENT_EVIDENCE
    validation_status: str = "Inconclusive" # "Passed", "Warning", "Critical", "Inconclusive"
    warnings: List[str] = field(default_factory=list)
    failed_rules: List[str] = field(default_factory=list)
    passed_rules: List[str] = field(default_factory=list)
    scientific_confidence: str = "Inconclusive" # "High", "Medium", "Low", "Inconclusive"


@dataclass
class AnalysisResult:
    """Contains the accumulated analysis across the entire video."""
    video_path: str = ""
    stroke_type: str = ""
    stroke_selection: Optional[StrokeSelection] = None
    frames: List[FrameData] = field(default_factory=list)
    average_stroke_rate: float = 0.0
    report: Optional[PerformanceReport] = None
    vqa_result: Optional[VQAResult] = None
    stroke_statistics: Optional[StrokeStatistics] = None
    reliability: Optional[ReliabilityResult] = None
    consistency: Optional[ConsistencyReport] = None
    benchmark_result: Optional[Any] = None
    
    def get_angles_timeseries(self) -> Dict[str, List[Optional[float]]]:
        """Returns timeseries data suitable for plotting."""
        return {
            "timestamp_ms": [f.timestamp_ms for f in self.frames],
            "left_elbow": [f.angles.left_elbow.value if f.angles.left_elbow else None for f in self.frames],
            "right_elbow": [f.angles.right_elbow.value if f.angles.right_elbow else None for f in self.frames],
            "left_knee": [f.angles.left_knee.value if f.angles.left_knee else None for f in self.frames],
            "right_knee": [f.angles.right_knee.value if f.angles.right_knee else None for f in self.frames],
        }
