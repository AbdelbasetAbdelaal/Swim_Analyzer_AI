from dataclasses import dataclass, field
from typing import Dict, Optional
from enum import Enum

class AgeGroup(str, Enum):
    U10 = "8-10"
    U13 = "11-13"
    U17 = "14-17"
    ADULT = "18-25"
    SENIOR = "26-35"
    MASTERS = "Masters"

    @classmethod
    def from_age(cls, age: int) -> "AgeGroup":
        if age <= 10:
            return cls.U10
        elif age <= 13:
            return cls.U13
        elif age <= 17:
            return cls.U17
        elif age <= 25:
            return cls.ADULT
        elif age <= 35:
            return cls.SENIOR
        else:
            return cls.MASTERS

class GenderCategory(str, Enum):
    MALE = "Male"
    FEMALE = "Female"
    MIXED = "Mixed"

class SkillLevel(str, Enum):
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"
    NATIONAL = "National"
    ELITE = "Elite"
    OLYMPIC = "Olympic"

from models.scientific_evidence_models import MetricEvidenceMetadata

@dataclass
class PopulationStats:
    """Scientific reference population statistics for a specific metric."""
    mean: float
    std: float
    elite_mean: float
    unit: str = ""
    higher_is_better: bool = True
    evidence: MetricEvidenceMetadata = field(default_factory=MetricEvidenceMetadata)

@dataclass
class MetricBenchmarkComparison:
    """Detailed scientific population comparison for a single metric."""
    metric_name: str = ""
    raw_value: Optional[float] = None
    population_mean: Optional[float] = None
    population_std: Optional[float] = None
    z_score: Optional[float] = None
    percentile: Optional[float] = None
    elite_mean: Optional[float] = None
    elite_delta: Optional[float] = None
    skill_level: Optional[str] = "N/A"
    unit: str = ""
    measurement_confidence: float = 1.0
    population_confidence: float = 0.95
    benchmark_confidence: float = 0.95
    evidence: MetricEvidenceMetadata = field(default_factory=MetricEvidenceMetadata)

@dataclass
class BenchmarkConfidence:
    """Decoupled confidence scores for measurement, population, and benchmark model."""
    measurement_confidence: float = 1.0
    population_confidence: float = 0.95
    benchmark_confidence: float = 0.95
    overall_confidence: float = 0.95

@dataclass
class BenchmarkResult:
    """Aggregates population comparisons across all biomechanical metrics."""
    stroke_type: str = "Freestyle"
    age_group: str = "18-25"
    gender: str = "Male"
    overall_skill_level: str = "Intermediate"
    dataset_version: str = "1.1.0"
    dataset_name: str = ""
    dataset_id: str = ""
    scientific_revision: str = "2026.08"
    validation_status: str = "partially_validated"
    is_population_compatible: bool = True
    confidence: BenchmarkConfidence = field(default_factory=BenchmarkConfidence)
    comparisons: Dict[str, MetricBenchmarkComparison] = field(default_factory=dict)
