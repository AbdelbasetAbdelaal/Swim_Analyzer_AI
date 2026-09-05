"""
Domain models for the Reference Data Manager.
Defines ReferenceDataset, ReferenceMetric, ReferenceSource, ReferenceValidationEvent,
and associated scientific taxonomy Enums.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum

class ReferenceStrokeType(str, Enum):
    FREESTYLE = "FREESTYLE"
    BACKSTROKE = "BACKSTROKE"
    BREASTSTROKE = "BREASTSTROKE"
    BUTTERFLY = "BUTTERFLY"
    ALL = "ALL"

class ReferenceSkillLevel(str, Enum):
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"
    ELITE = "Elite"
    UNKNOWN = "Unknown"

class ReferenceAthleteCategory(str, Enum):
    YOUTH = "Youth"
    ADULT = "Adult"
    MASTERS = "Masters"
    SPRINTER = "Sprinter"
    DISTANCE = "Distance"
    IM = "IM"
    CUSTOM = "Custom"

class ReferenceSourceType(str, Enum):
    PEER_REVIEWED_SYSTEMATIC_REVIEW = "PEER_REVIEWED_SYSTEMATIC_REVIEW"
    PEER_REVIEWED_META_ANALYSIS = "PEER_REVIEWED_META_ANALYSIS"
    PEER_REVIEWED_PRIMARY_STUDY = "PEER_REVIEWED_PRIMARY_STUDY"
    VALIDATED_TEAM_DATA = "VALIDATED_TEAM_DATA"
    COACH_DEFINED = "COACH_DEFINED"
    IMPORTED_REFERENCE = "IMPORTED_REFERENCE"
    UNKNOWN = "UNKNOWN"

CANONICAL_SOURCE_TYPE_MAPPING: Dict[str, str] = {
    "PEER_REVIEWED_ORIGINAL_RESEARCH": "PEER_REVIEWED_PRIMARY_STUDY",
    "PEER_REVIEWED_PRIMARY_STUDY": "PEER_REVIEWED_PRIMARY_STUDY",
    "PEER_REVIEWED": "PEER_REVIEWED_PRIMARY_STUDY",
    "ORIGINAL_RESEARCH": "PEER_REVIEWED_PRIMARY_STUDY",
    "PEER_REVIEWED_SYSTEMATIC_REVIEW": "PEER_REVIEWED_SYSTEMATIC_REVIEW",
    "SYSTEMATIC_REVIEW": "PEER_REVIEWED_SYSTEMATIC_REVIEW",
    "PEER_REVIEWED_META_ANALYSIS": "PEER_REVIEWED_META_ANALYSIS",
    "META_ANALYSIS": "PEER_REVIEWED_META_ANALYSIS",
    "VALIDATED_TEAM_DATA": "VALIDATED_TEAM_DATA",
    "TEAM_DATA": "VALIDATED_TEAM_DATA",
    "COACH_DEFINED": "COACH_DEFINED",
    "IMPORTED_REFERENCE": "IMPORTED_REFERENCE",
    "SCIENTIFIC_POLICY": "IMPORTED_REFERENCE",
    "UNKNOWN": "UNKNOWN"
}

class ReferenceBenchmarkPriority(str, Enum):
    P0 = "P0"  # Highest scientific priority
    P1 = "P1"  # Strong supporting benchmark
    P2 = "P2"  # Contextual reference only
    P3 = "P3"  # Non-benchmark contextual information

class ReferenceBenchmarkEligibility(str, Enum):
    BENCHMARK = "BENCHMARK"
    CONTEXT_ONLY = "CONTEXT_ONLY"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

class ReferenceValidationStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    COACH_VALIDATED = "COACH_VALIDATED"
    SCIENTIFICALLY_VALIDATED = "SCIENTIFICALLY_VALIDATED"
    VALIDATED_REFERENCE = "VALIDATED_REFERENCE"
    REJECTED = "REJECTED"

class ReferenceMeasurementDomain(str, Enum):
    CALIBRATED_PHYSICAL = "CALIBRATED_PHYSICAL"
    RELATIVE_BODY_NORMALIZED = "RELATIVE_BODY_NORMALIZED"
    POSE_RELATIVE_3D = "POSE_RELATIVE_3D"
    IMAGE_SPACE = "IMAGE_SPACE"
    UNAVAILABLE = "UNAVAILABLE"

@dataclass
class ReferenceMetric:
    metric_id: str = ""
    dataset_id: str = ""
    metric_name: str = ""
    display_name: str = ""
    value_min: Optional[float] = None
    value_typical: Optional[float] = None
    value_median: Optional[float] = None
    value_max: Optional[float] = None
    uncertainty_sd: Optional[float] = None
    unit: str = ""
    measurement_domain: str = "UNAVAILABLE"
    status: str = "unavailable"  # "available" or "unavailable"
    method: str = ""
    notes: str = ""
    event_distance: str = ""
    course: str = ""
    evidence_grade: str = ""
    context_only_reason: str = ""
    population_match_required: str = ""

@dataclass
class ReferenceSource:
    source_id: str = ""
    dataset_id: str = ""
    source_type: str = "UNKNOWN"
    source_title: str = ""
    authors: str = ""
    publication_year: Optional[int] = None
    doi: str = ""
    pmid: str = ""
    url: str = ""
    sample_size: Optional[int] = None
    population_description: str = ""

@dataclass
class ReferenceValidationEvent:
    event_id: str = ""
    dataset_id: str = ""
    timestamp: str = ""
    user: str = "Coach/Admin"
    action: str = "CREATE"  # CREATE, EDIT, VALIDATE, REJECT, ARCHIVE, IMPORT, EXPORT, DELETE
    old_status: str = ""
    new_status: str = ""
    notes: str = ""

@dataclass
class ReferenceDatasetVersion:
    version_id: str = ""
    version_name: str = "manual_reference_v1"
    filename: str = ""
    imported_at: str = ""
    record_count: int = 0
    valid_count: int = 0
    rejected_count: int = 0
    is_active: bool = True
    importer: str = "System/Coach"

@dataclass
class ReferenceDataset:
    dataset_id: str = ""
    name: str = ""
    description: str = ""
    stroke: str = "FREESTYLE"
    age_min: Optional[int] = 0
    age_max: Optional[int] = 100
    sex: str = "Mixed"  # Male, Female, Mixed, Unknown
    skill_level: str = "Unknown"
    athlete_category: str = "Adult"
    training_level: str = ""
    source_type: str = "COACH_DEFINED"
    evidence_status: str = "INSUFFICIENT_EVIDENCE"
    benchmark_eligibility: str = "CONTEXT_ONLY"
    benchmark_priority: str = "P2"  # P0, P1, P2, P3
    validation_status: str = "DRAFT"
    is_archived: bool = False
    is_active: bool = True
    dataset_version: str = "manual_reference_v1"
    created_at: str = ""
    updated_at: str = ""
    metrics: List[ReferenceMetric] = field(default_factory=list)
    sources: List[ReferenceSource] = field(default_factory=list)
    validation_events: List[ReferenceValidationEvent] = field(default_factory=list)

    def __post_init__(self):
        if self.validation_status in ["SCIENTIFICALLY_VALIDATED", "VALIDATED_REFERENCE", "COACH_VALIDATED"] and self.benchmark_eligibility == "CONTEXT_ONLY":
            self.benchmark_eligibility = "BENCHMARK"
