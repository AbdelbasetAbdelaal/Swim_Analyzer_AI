"""
Swim Analyzer AI - Ground Truth Validation Infrastructure.
"""
from .ground_truth_models import (
    GroundTruthSample,
    GroundTruthManifest,
    MetricComparison,
    ValidationCohortResult,
)
from .ground_truth_comparator import GroundTruthComparator
from .ground_truth_policy import ValidationStatus, GroundTruthValidationPolicy
from .data_leakage_validator import DataLeakageValidator
from .provenance_contract import (
    SourceModality,
    AngleDimension,
    ALLOWED_METRIC_MODALITIES,
    ProvenanceValidator,
    MetricProvenanceRecord,
)
from .ground_truth_runner import GroundTruthValidationRunner
from .ground_truth_ingestion import GroundTruthIngestionService, compute_file_sha256

__all__ = [
    "GroundTruthSample",
    "GroundTruthManifest",
    "MetricComparison",
    "ValidationCohortResult",
    "GroundTruthComparator",
    "ValidationStatus",
    "GroundTruthValidationPolicy",
    "DataLeakageValidator",
    "SourceModality",
    "AngleDimension",
    "ALLOWED_METRIC_MODALITIES",
    "ProvenanceValidator",
    "MetricProvenanceRecord",
    "GroundTruthValidationRunner",
    "GroundTruthIngestionService",
    "compute_file_sha256",
]
