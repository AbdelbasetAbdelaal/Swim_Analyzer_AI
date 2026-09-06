"""
Domain models for Ground Truth Validation in Swim Analyzer AI.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
import json
from pathlib import Path


class InclusionStatus(str, Enum):
    INCLUDED = "INCLUDED"
    AMBIGUOUS = "AMBIGUOUS"
    EXCLUDED = "EXCLUDED"


class QualityStatus(str, Enum):
    PASSED = "PASSED"
    SUSPECT = "SUSPECT"
    FAILED = "FAILED"


class AnnotationStatus(str, Enum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    PENDING_SECOND_RATER = "PENDING_SECOND_RATER"
    PENDING_ADJUDICATION = "PENDING_ADJUDICATION"


class MeasurementType(str, Enum):
    MEASURED_PHYSICAL_QUANTITY = "MEASURED_PHYSICAL_QUANTITY"
    PROXY_ESTIMATE_NORMALIZED = "PROXY_ESTIMATE_NORMALIZED"


@dataclass
class CyclePhaseEvent:
    phase_name: str
    transition_frame: int
    timestamp_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {"phase_name": self.phase_name, "transition_frame": self.transition_frame}
        if self.timestamp_ms is not None:
            d["timestamp_ms"] = self.timestamp_ms
        return d


@dataclass
class CycleAnnotation:
    cycle_index: int
    start_frame: int
    end_frame: int
    duration_ms: float
    stroke_rate_spm: float
    phase_events: List[CyclePhaseEvent] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle_index": self.cycle_index,
            "start_frame": self.start_frame,
            "end_frame": self.end_frame,
            "duration_ms": self.duration_ms,
            "stroke_rate_spm": self.stroke_rate_spm,
            "phase_events": [pe.to_dict() for pe in self.phase_events],
        }


@dataclass
class GroundTruthSample:
    sample_id: str
    participant_id: str
    session_id: str
    stroke_type: str
    video_id: str
    video_filename: str
    source_type: str
    annotation_version: str
    annotator_id: str
    annotation_timestamp: str
    video_fps: float
    video_duration: float
    frame_count: int
    exclusion_status: str = InclusionStatus.INCLUDED.value
    exclusion_reason: Optional[str] = None
    video_sha256: Optional[str] = None
    secondary_annotator_id: Optional[str] = None
    pool_context: Dict[str, Any] = field(default_factory=dict)
    demographics: Dict[str, Any] = field(default_factory=dict)
    cycle_annotations: List[CycleAnnotation] = field(default_factory=list)
    metric_annotations: Dict[str, Any] = field(default_factory=dict)
    annotation_notes: str = ""
    quality_flags: Dict[str, Any] = field(default_factory=dict)
    is_synthetic_fixture: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GroundTruthSample":
        cycles = []
        for c in data.get("cycle_annotations", []):
            phases = [CyclePhaseEvent(**p) for p in c.get("phase_events", [])]
            c_copy = dict(c)
            c_copy["phase_events"] = phases
            cycles.append(CycleAnnotation(**c_copy))

        return cls(
            sample_id=data["sample_id"],
            participant_id=data["participant_id"],
            session_id=data["session_id"],
            stroke_type=data["stroke_type"],
            video_id=data["video_id"],
            video_filename=data["video_filename"],
            source_type=data["source_type"],
            annotation_version=data["annotation_version"],
            annotator_id=data["annotator_id"],
            annotation_timestamp=data["annotation_timestamp"],
            video_fps=float(data["video_fps"]),
            video_duration=float(data["video_duration"]),
            frame_count=int(data["frame_count"]),
            exclusion_status=data.get("exclusion_status", InclusionStatus.INCLUDED.value),
            exclusion_reason=data.get("exclusion_reason"),
            video_sha256=data.get("video_sha256"),
            secondary_annotator_id=data.get("secondary_annotator_id"),
            pool_context=data.get("pool_context", {}),
            demographics=data.get("demographics", {}),
            cycle_annotations=cycles,
            metric_annotations=data.get("metric_annotations", {}),
            annotation_notes=data.get("annotation_notes", ""),
            quality_flags=data.get("quality_flags", {}),
            is_synthetic_fixture=data.get("is_synthetic_fixture", False),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "participant_id": self.participant_id,
            "session_id": self.session_id,
            "stroke_type": self.stroke_type,
            "video_id": self.video_id,
            "video_filename": self.video_filename,
            "video_sha256": self.video_sha256,
            "source_type": self.source_type,
            "annotation_version": self.annotation_version,
            "annotator_id": self.annotator_id,
            "secondary_annotator_id": self.secondary_annotator_id,
            "annotation_timestamp": self.annotation_timestamp,
            "video_fps": self.video_fps,
            "video_duration": self.video_duration,
            "frame_count": self.frame_count,
            "pool_context": self.pool_context,
            "demographics": self.demographics,
            "cycle_annotations": [c.to_dict() for c in self.cycle_annotations],
            "metric_annotations": self.metric_annotations,
            "annotation_notes": self.annotation_notes,
            "quality_flags": self.quality_flags,
            "exclusion_status": self.exclusion_status,
            "exclusion_reason": self.exclusion_reason,
            "is_synthetic_fixture": self.is_synthetic_fixture,
        }

    @property
    def is_eligible_for_validation(self) -> bool:
        """Determines if this sample meets all inclusion criteria."""
        return (
            self.exclusion_status == InclusionStatus.INCLUDED.value
            and not self.is_synthetic_fixture
            and self.video_fps >= 30.0
            and self.frame_count >= 30
        )


@dataclass
class ManifestRecord:
    sample_id: str
    video_path: str
    stroke: str
    participant_id: str
    annotation_file: str
    annotation_status: str
    quality_status: str
    inclusion_status: str
    validator_version: str
    video_sha256: Optional[str] = None
    session_id: Optional[str] = None
    exclusion_reason: Optional[str] = None
    split: str = "VALIDATION_OFFICIAL"

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "sample_id": self.sample_id,
            "video_path": self.video_path,
            "stroke": self.stroke,
            "participant_id": self.participant_id,
            "annotation_file": self.annotation_file,
            "annotation_status": self.annotation_status,
            "quality_status": self.quality_status,
            "inclusion_status": self.inclusion_status,
            "validator_version": self.validator_version,
            "split": self.split,
        }
        if self.video_sha256:
            d["video_sha256"] = self.video_sha256
        if self.session_id:
            d["session_id"] = self.session_id
        if self.exclusion_reason:
            d["exclusion_reason"] = self.exclusion_reason
        return d


@dataclass
class GroundTruthManifest:
    manifest_version: str
    manifest_id: str
    created_at: str
    cohort_name: str
    protocol_version: str
    records: List[ManifestRecord]
    description: str = ""
    is_synthetic_manifest: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GroundTruthManifest":
        records = [ManifestRecord(**r) for r in data["records"]]
        return cls(
            manifest_version=data["manifest_version"],
            manifest_id=data["manifest_id"],
            created_at=data["created_at"],
            cohort_name=data["cohort_name"],
            protocol_version=data["protocol_version"],
            records=records,
            description=data.get("description", ""),
            is_synthetic_manifest=data.get("is_synthetic_manifest", False),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "manifest_id": self.manifest_id,
            "created_at": self.created_at,
            "cohort_name": self.cohort_name,
            "protocol_version": self.protocol_version,
            "description": self.description,
            "is_synthetic_manifest": self.is_synthetic_manifest,
            "records": [r.to_dict() for r in self.records],
        }

    def get_eligible_records(self, allow_synthetic: bool = False) -> List[ManifestRecord]:
        """Returns records that are strictly eligible for validation analysis."""
        eligible = []
        for r in self.records:
            if r.inclusion_status != InclusionStatus.INCLUDED.value:
                continue
            if r.annotation_status != AnnotationStatus.COMPLETE.value:
                continue
            if r.quality_status == QualityStatus.FAILED.value:
                continue
            if self.is_synthetic_manifest and not allow_synthetic:
                continue
            eligible.append(r)
        return eligible


@dataclass
class MetricComparison:
    metric_name: str
    unit: str
    measurement_type: str
    sample_count: int
    valid_comparison_count: int
    missing_ai_count: int
    missing_gt_count: int
    mae: Optional[float] = None
    rmse: Optional[float] = None
    bias: Optional[float] = None
    mape: Optional[float] = None
    correlation_pearson: Optional[float] = None
    status: str = "NOT_VALIDATED — INSUFFICIENT GROUND TRUTH"
    threshold_status: str = "TBD — REQUIRES DOMAIN JUSTIFICATION"
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "unit": self.unit,
            "measurement_type": self.measurement_type,
            "sample_count": self.sample_count,
            "valid_comparison_count": self.valid_comparison_count,
            "missing_ai_count": self.missing_ai_count,
            "missing_gt_count": self.missing_gt_count,
            "mae": self.mae,
            "rmse": self.rmse,
            "bias": self.bias,
            "mape": self.mape,
            "correlation_pearson": self.correlation_pearson,
            "status": self.status,
            "threshold_status": self.threshold_status,
            "notes": self.notes,
        }


@dataclass
class ValidationRunMetadata:
    run_id: str
    git_commit_sha: str
    protocol_version: str
    schema_version: str
    config_version: str
    app_version: str
    run_timestamp: str
    is_synthetic_run: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "git_commit_sha": self.git_commit_sha,
            "protocol_version": self.protocol_version,
            "schema_version": self.schema_version,
            "config_version": self.config_version,
            "app_version": self.app_version,
            "run_timestamp": self.run_timestamp,
            "is_synthetic_run": self.is_synthetic_run,
        }


@dataclass
class ValidationCohortResult:
    metadata: ValidationRunMetadata
    overall_status: str
    cohort_name: str
    total_manifest_records: int
    eligible_records_count: int
    excluded_records_count: int
    ambiguous_records_count: int
    metric_comparisons: Dict[str, MetricComparison] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "overall_status": self.overall_status,
            "cohort_name": self.cohort_name,
            "total_manifest_records": self.total_manifest_records,
            "eligible_records_count": self.eligible_records_count,
            "excluded_records_count": self.excluded_records_count,
            "ambiguous_records_count": self.ambiguous_records_count,
            "metric_comparisons": {k: v.to_dict() for k, v in self.metric_comparisons.items()},
            "warnings": self.warnings,
        }
