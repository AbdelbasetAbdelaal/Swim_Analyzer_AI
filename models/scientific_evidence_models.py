from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

class EvidenceLevel(str, Enum):
    LEVEL_A = "LEVEL_A" # Peer-reviewed scientific journal research
    LEVEL_B = "LEVEL_B" # Official governing body / sports science institute data
    LEVEL_C = "LEVEL_C" # Established academic textbooks (e.g. Maglischo 2003)
    LEVEL_D = "LEVEL_D" # Secondary professional sources (ASCA monographs)
    LEVEL_E = "LEVEL_E" # Unverified web sources (Prohibited from production validation)

class ValidationStatus(str, Enum):
    VALIDATED = "VALIDATED"                   # Fully supported by Level A/B empirical evidence
    PARTIALLY_VALIDATED = "PARTIALLY_VALIDATED" # Supported by Level C/D or adjacent cohort extrapolation
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE" # Insufficient sample size or missing data
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"   # Multiple valid studies report statistically incompatible bounds
    PLACEHOLDER = "PLACEHOLDER"               # Derived index or heuristic baseline awaiting empirical field study

    @property
    def badge_label(self) -> str:
        if self == ValidationStatus.VALIDATED:
            return "✓ Validated"
        elif self == ValidationStatus.PARTIALLY_VALIDATED:
            return "⚠ Partially Validated"
        elif self == ValidationStatus.INSUFFICIENT_EVIDENCE:
            return "⚠ Insufficient Evidence"
        elif self == ValidationStatus.CONFLICTING_EVIDENCE:
            return "✕ Conflicting Evidence"
        else:
            return "! Placeholder"

    @property
    def badge_color(self) -> str:
        if self == ValidationStatus.VALIDATED:
            return "#00F0FF" # Cyan
        elif self == ValidationStatus.PARTIALLY_VALIDATED:
            return "#FF8C00" # Orange
        elif self == ValidationStatus.INSUFFICIENT_EVIDENCE:
            return "#FFD700" # Gold/Yellow
        elif self == ValidationStatus.CONFLICTING_EVIDENCE:
            return "#F44336" # Red
        else:
            return "#FF007F" # Pink/Red

class SourceRelationship(str, Enum):
    DIRECTLY_SUPPORTED = "DIRECTLY_SUPPORTED"   # Production YAML mean/std matches reported paper values
    DERIVED_FROM_SOURCE = "DERIVED_FROM_SOURCE" # Converted or calculated from reported parameters (e.g. Hz to spm)
    APPROXIMATED = "APPROXIMATED"               # Estimated from reported range curves or interpolated across cohorts
    UNVERIFIED = "UNVERIFIED"                   # Source cannot be verified or lacks empirical statistical figures

class SourceAccessLevel(str, Enum):
    FULL_TEXT_VERIFIED = "FULL_TEXT_VERIFIED"
    ABSTRACT_VERIFIED = "ABSTRACT_VERIFIED"
    METADATA_ONLY = "METADATA_ONLY"
    UNVERIFIED = "UNVERIFIED"

class DefinitionMatchingStatus(str, Enum):
    EXACT_MATCH = "EXACT_MATCH"
    COMPATIBLE_DEFINITION = "COMPATIBLE_DEFINITION"
    DEFINITION_MISMATCH = "DEFINITION_MISMATCH"
    UNKNOWN_DEFINITION = "UNKNOWN_DEFINITION"

class PopulationMatchingStatus(str, Enum):
    EXACT_MATCH = "EXACT_MATCH"
    COMPATIBLE = "COMPATIBLE"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    POPULATION_MISMATCH = "POPULATION_MISMATCH"
    UNKNOWN = "UNKNOWN"

class ReviewStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    EXTRACTED = "EXTRACTED"
    PENDING_REVIEW = "PENDING_REVIEW"
    SCIENTIFICALLY_ACCEPTED = "SCIENTIFICALLY_ACCEPTED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"

class SourceQuality(str, Enum):
    PEER_REVIEWED_FULL_TEXT = "PEER_REVIEWED_FULL_TEXT"
    PEER_REVIEWED_ABSTRACT_ONLY = "PEER_REVIEWED_ABSTRACT_ONLY"
    OFFICIAL_ORGANIZATION = "OFFICIAL_ORGANIZATION"
    TEXTBOOK = "TEXTBOOK"
    SECONDARY_REVIEW = "SECONDARY_REVIEW"
    OTHER = "OTHER"

class AuditDecision(str, Enum):
    ACCEPT = "ACCEPT"
    ACCEPT_AS_DERIVED = "ACCEPT_AS_DERIVED"
    REFERENCE_ONLY = "REFERENCE_ONLY"
    REJECT = "REJECT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

class PopulationCompatibility(str, Enum):
    COMPATIBLE = "COMPATIBLE"
    POPULATION_MISMATCH = "POPULATION_MISMATCH"

class DefinitionCompatibility(str, Enum):
    COMPATIBLE = "COMPATIBLE"
    DEFINITION_MISMATCH = "DEFINITION_MISMATCH"

class BenchmarkPolicy(str, Enum):
    PRIMARY_STUDY_TRACE_REQUIRED = "PRIMARY_STUDY_TRACE_REQUIRED"
    CONDITIONAL_PRIMARY_STUDY_TRACE = "CONDITIONAL_PRIMARY_STUDY_TRACE"
    TEST_SPECIFIC_ONLY = "TEST_SPECIFIC_ONLY"
    AGE_STRATIFIED_PRIMARY_STUDY_REQUIRED = "AGE_STRATIFIED_PRIMARY_STUDY_REQUIRED"

class StudyType(str, Enum):
    PRIMARY_STUDY = "primary_study"
    SYSTEMATIC_REVIEW = "systematic_review"
    META_ANALYSIS = "meta_analysis"

@dataclass
class ScientificEvidenceRecord:
    """
    Granular, evidence-first scientific observation record.
    Preserves original scientific values, units, exact table/page locations, and conversion formulas.
    """
    evidence_id: str
    source_id: str
    title: str
    authors: List[str]
    year: int
    doi: Optional[str] = None
    url: Optional[str] = None
    publication: str = ""
    stroke: str = "Freestyle"
    event_distance: str = "100m"
    population_description: str = ""
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    mean_age: Optional[float] = None
    gender: str = "Mixed"
    skill_level: str = "National"
    sample_size: int = 0
    measurement_name: str = ""
    measurement_definition: str = ""
    measurement_method: str = ""
    measurement_units: str = ""
    reported_mean: Optional[float] = None
    reported_std: Optional[float] = None
    reported_min: Optional[float] = None
    reported_max: Optional[float] = None
    confidence_interval: Optional[str] = None
    statistical_method: str = "Mean +/- SD"
    table_or_figure_reference: str = ""
    page_reference: str = ""
    source_quote: str = ""
    source_access_level: SourceAccessLevel = SourceAccessLevel.FULL_TEXT_VERIFIED
    source_quality: SourceQuality = SourceQuality.PEER_REVIEWED_FULL_TEXT
    extraction_method: str = "Manual Scientific Audit & Open API Retrieval"
    relationship_to_benchmark: SourceRelationship = SourceRelationship.DIRECTLY_SUPPORTED
    population_compatibility: PopulationMatchingStatus = PopulationMatchingStatus.EXACT_MATCH
    definition_compatibility: DefinitionMatchingStatus = DefinitionMatchingStatus.EXACT_MATCH
    unit_compatibility: bool = True
    scientific_status: ReviewStatus = ReviewStatus.SCIENTIFICALLY_ACCEPTED
    audit_decision: AuditDecision = AuditDecision.ACCEPT
    conversion_formula: Optional[str] = None
    converted_value: Optional[float] = None
    converted_unit: Optional[str] = None
    reviewed_by: str = "Lead Scientific Software Architect"
    reviewed_at: str = "2026-08-08"
    study_type: str = "primary_study"
    primary_study_identifier: Optional[str] = None
    test_distance_m: Optional[int] = None
    notes: str = ""

@dataclass
class CandidateEvidence:
    """
    Untrusted semantic extraction payload directly from Gemini.
    Must never be used as a benchmark until deterministic validation converts it to an EvidenceRecord.
    """
    source_id: str
    pmid: Optional[str]
    pmcid: Optional[str]
    doi: Optional[str]
    title: str
    stroke: Optional[str]
    population_sex: Optional[str]
    population_age: Optional[str]
    competitive_level: Optional[str]
    metric: Optional[str]
    mean: Optional[float]
    sd: Optional[float]
    unit: Optional[str]
    sample_size: Optional[int]
    table_or_figure: Optional[str]
    source_quote: Optional[str]
    xml_block_type: str
    confidence: Optional[str] = None
    study_type: str = "primary_study"
    primary_study_identifier: Optional[str] = None
    test_distance_m: Optional[int] = None
    notes: Optional[str] = None

@dataclass
class AggregatedEvidence:
    """
    Represents the output of the EvidenceAggregator combining multiple SCIENTIFICALLY_ACCEPTED studies.
    """
    metric_name: str
    stroke: str
    gender: str
    age_group: str
    aggregated_mean: float
    aggregated_std: float
    unit: str
    total_sample_size: int
    source_records: List[ScientificEvidenceRecord]
    is_conflicting: bool = False

@dataclass
class ScientificSource:
    """Represents a peer-reviewed scientific paper or official governing body dataset."""
    source_id: str
    title: str
    authors: List[str]
    publication_year: int
    journal_or_organization: str
    doi: Optional[str] = None
    pmid: Optional[str] = None
    url: Optional[str] = None
    stroke: str = "Freestyle"
    population: str = "Competitive Swimmers"
    sample_size: int = 0
    age_range: str = "18-25"
    gender: str = "Mixed"
    competitive_level: str = "National"
    measured_metrics: List[str] = field(default_factory=list)
    evidence_quality: EvidenceLevel = EvidenceLevel.LEVEL_A
    access_level: str = "FULL_TEXT_VERIFIED"
    verification_status: str = "VERIFIED_CORRECT"
    study_type: str = "primary_study"
    benchmark_policy: Optional[str] = None
    priority: int = 1
    test_context: Optional[Dict[str, Any]] = None
    notes: str = ""

@dataclass
class MetricEvidenceMetadata:
    """Scientific evidence provenance attached to every population benchmark parameter."""
    validation_status: ValidationStatus = ValidationStatus.PARTIALLY_VALIDATED
    evidence_level: EvidenceLevel = EvidenceLevel.LEVEL_C
    source_ids: List[str] = field(default_factory=list)
    sample_size: int = 0
    event_distance: str = "100m"
    measurement_method: str = "3D Kinematic Motion Capture / Video Analysis"
    source_relationship: SourceRelationship = SourceRelationship.APPROXIMATED
    population_compatibility: PopulationCompatibility = PopulationCompatibility.COMPATIBLE
    definition_compatibility: DefinitionCompatibility = DefinitionCompatibility.COMPATIBLE
    reported_source_value: str = ""
    reported_source_std: str = ""
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "validation_status": self.validation_status.value,
            "evidence_level": self.evidence_level.value,
            "source_ids": self.source_ids,
            "sample_size": self.sample_size,
            "event_distance": self.event_distance,
            "measurement_method": self.measurement_method,
            "source_relationship": self.source_relationship.value,
            "population_compatibility": self.population_compatibility.value,
            "definition_compatibility": self.definition_compatibility.value,
            "reported_source_value": self.reported_source_value,
            "reported_source_std": self.reported_source_std,
            "notes": self.notes
        }
