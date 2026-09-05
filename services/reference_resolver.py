"""
Benchmark Priority Engine / Reference Data Resolver.
Evaluates demographic compatibility and resolves priority among primary peer-reviewed datasets,
coach-validated team datasets, coach-defined references, and scientific YAML benchmarks.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from models.reference_data_models import ReferenceDataset, ReferenceMetric, ReferenceBenchmarkEligibility, ReferenceValidationStatus

@dataclass
class ResolvedReferenceMatch:
    metric_name: str
    selected_dataset_id: str
    selected_dataset_name: str
    source_type: str
    benchmark_eligibility: str
    validation_status: str
    reference_metric: Optional[ReferenceMetric]
    compatibility_score: float  # REFERENCE_MATCH_SCORE (0.0 to 100.0)
    selection_reason: str
    scientific_confidence: str  # High, Medium, Low, Insufficient Evidence
    warnings: List[str] = field(default_factory=list)
    disclaimers: List[str] = field(default_factory=list)

class ReferenceDataResolver:
    @staticmethod
    def _normalize_metric_name(name: str) -> str:
        """Normalize a metric name for comparison: lowercase, spaces→underscores.
        Allows 'Stroke Rate' to match 'stroke_rate', 'DPS' to match 'dps', etc.
        """
        return name.lower().replace(" ", "_").replace("-", "_")


    """
    Evaluates reference dataset priority.
    Enforces compatibility-first policy: demographic incompatibility (age, sex, stroke)
    immediately disqualifies a dataset regardless of scientific prestige.
    """

    PRIORITY_WEIGHTS = {
        "PEER_REVIEWED_SYSTEMATIC_REVIEW": 100,
        "PEER_REVIEWED_META_ANALYSIS": 95,
        "PEER_REVIEWED_PRIMARY_STUDY": 90,
        "VALIDATED_TEAM_DATA": 70,
        "COACH_DEFINED": 50,
        "IMPORTED_REFERENCE": 30,
        "UNKNOWN": 10
    }

    @classmethod
    def calculate_compatibility(
        cls, dataset: ReferenceDataset, stroke: str, age: int, sex: str, skill_level: str = "Unknown", test_protocol: Optional[str] = None
    ) -> Tuple[float, List[str]]:
        """
        Calculates REFERENCE_MATCH_SCORE (0.0 to 100.0).
        If stroke, age, or sex is fundamentally incompatible, returns 0.0.
        """
        reasons = []
        score = 100.0

        # 1. Stroke compatibility
        ds_stroke = dataset.stroke.upper()
        target_stroke = stroke.upper()
        if ds_stroke != "ALL" and ds_stroke != target_stroke:
            return 0.0, [f"Incompatible stroke: dataset is for {dataset.stroke}, athlete swimming {stroke}."]

        # 2. Age compatibility
        if age < dataset.age_min or age > dataset.age_max:
            # Youth (<=17) vs Adult (18-25) vs Masters (>=36) hard boundary
            if (age <= 17 and dataset.age_min >= 18) or (age >= 18 and dataset.age_max <= 17):
                return 0.0, [f"Youth vs Adult age boundary violation: athlete age {age}, dataset range [{dataset.age_min}-{dataset.age_max}]."]
            if (age >= 36 and dataset.age_max <= 35) or (age <= 35 and dataset.age_min >= 36):
                return 0.0, [f"Masters vs Adult age boundary violation: athlete age {age}, dataset range [{dataset.age_min}-{dataset.age_max}]."]

            score -= 30.0
            reasons.append(f"Age {age} outside dataset range [{dataset.age_min}-{dataset.age_max}].")

        # 3. Sex compatibility (Hard boundary for single-sex benchmark datasets)
        ds_sex = dataset.sex.lower()
        target_sex = sex.lower()
        if ds_sex != "mixed" and target_sex != "mixed" and ds_sex != target_sex:
            return 0.0, [f"Sex boundary violation: dataset is for {dataset.sex}, athlete is {sex}."]

        # 4. Skill level compatibility
        if dataset.skill_level != "Unknown" and skill_level != "Unknown":
            if dataset.skill_level.lower() != skill_level.lower():
                score -= 15.0
                reasons.append(f"Skill level difference: dataset is {dataset.skill_level}, athlete is {skill_level}.")

        # 5. TEST_SPECIFIC protocol compatibility
        if dataset.benchmark_eligibility == "TEST_SPECIFIC":
            if not test_protocol or test_protocol.lower() not in (dataset.description or "").lower():
                return 0.0, ["TEST_SPECIFIC protocol mismatch: Athlete/test protocol does not match dataset requirements."]

        # Archived datasets get score = 0
        if dataset.is_archived:
            return 0.0, ["Dataset is archived."]

        # Rejected datasets get score = 0
        if dataset.validation_status == ReferenceValidationStatus.REJECTED.value:
            return 0.0, ["Dataset validation status is REJECTED."]

        return max(0.0, score), reasons

    @classmethod
    def resolve_metric_reference(
        cls,
        datasets: List[ReferenceDataset],
        metric_name: str,
        stroke: str,
        athlete_age: int,
        athlete_sex: str,
        athlete_skill: str = "Unknown",
        test_protocol: Optional[str] = None
    ) -> ResolvedReferenceMatch:
        """
        Finds the highest-priority compatible benchmark dataset for a given metric.
        Excludes CONTEXT_ONLY, SOURCE_REGISTRY_*, and unvalidated COACH_DEFINED datasets from primary benchmark selection.
        """
        candidates = []

        for ds in datasets:
            # Policy Rule Enforcement: CONTEXT_ONLY & SOURCE_REGISTRY records must NEVER be selected as primary numerical benchmarks
            if ds.benchmark_eligibility == ReferenceBenchmarkEligibility.CONTEXT_ONLY.value or ds.name.startswith("SOURCE_REGISTRY_"):
                continue

            if ds.source_type == "COACH_DEFINED" and ds.benchmark_eligibility != ReferenceBenchmarkEligibility.BENCHMARK.value:
                continue

            compat_score, warnings = cls.calculate_compatibility(ds, stroke, athlete_age, athlete_sex, athlete_skill, test_protocol=test_protocol)
            if compat_score <= 0.0:
                continue

            # Find matching metric in dataset
            # Find matching metric in dataset — normalized comparison handles
            # display-name vs snake_case mismatches (e.g. "Stroke Rate" == "stroke_rate")
            _norm = cls._normalize_metric_name
            m_match = next(
                (m for m in ds.metrics
                 if _norm(m.metric_name) == _norm(metric_name)
                 or _norm(m.display_name) == _norm(metric_name)),
                None
            )

            if not m_match:
                continue

            # Base priority weight
            source_weight = cls.PRIORITY_WEIGHTS.get(ds.source_type, 10)
            if ds.validation_status == ReferenceValidationStatus.SCIENTIFICALLY_VALIDATED.value:
                source_weight += 20
            elif ds.validation_status == ReferenceValidationStatus.COACH_VALIDATED.value:
                source_weight += 10

            # Total ranking index
            total_rank = (compat_score * 2.0) + source_weight
            candidates.append((total_rank, compat_score, ds, m_match, warnings))

        if not candidates:
            return ResolvedReferenceMatch(
                metric_name=metric_name,
                selected_dataset_id="",
                selected_dataset_name="No Compatible Reference",
                source_type="NONE",
                benchmark_eligibility=ReferenceBenchmarkEligibility.INSUFFICIENT_EVIDENCE.value,
                validation_status="UNVALIDATED",
                reference_metric=None,
                compatibility_score=0.0,
                selection_reason="No compatible reference dataset found for this metric and demographic group.",
                scientific_confidence="Insufficient Evidence",
                warnings=["INSUFFICIENT_EVIDENCE: No matching population reference dataset available."]
            )

        # Sort candidates by total_rank descending
        candidates.sort(key=lambda x: x[0], reverse=True)
        best_rank, best_compat, best_ds, best_metric, warnings = candidates[0]

        # Determine scientific confidence
        if best_ds.validation_status == ReferenceValidationStatus.SCIENTIFICALLY_VALIDATED.value and best_compat >= 90.0:
            confidence = "High"
        elif best_ds.validation_status in [ReferenceValidationStatus.COACH_VALIDATED.value, ReferenceValidationStatus.SCIENTIFICALLY_VALIDATED.value] and best_compat >= 60.0:
            confidence = "Medium"
        else:
            confidence = "Low"

        # Disclaimers
        disclaimers = []
        if best_ds.source_type in ["COACH_DEFINED", "VALIDATED_TEAM_DATA"]:
            disclaimers.append("Coach-defined reference — not a universal scientific benchmark.")
        if athlete_age <= 17:
            disclaimers.append("Youth Cohort (Age <= 17) reference match.")

        reason = (
            f"Selected '{best_ds.name}' ({best_ds.source_type}) with REFERENCE_MATCH_SCORE={best_compat:.1f}/100. "
            f"Validation status: {best_ds.validation_status}."
        )

        return ResolvedReferenceMatch(
            metric_name=metric_name,
            selected_dataset_id=best_ds.dataset_id,
            selected_dataset_name=best_ds.name,
            source_type=best_ds.source_type,
            benchmark_eligibility=best_ds.benchmark_eligibility,
            validation_status=best_ds.validation_status,
            reference_metric=best_metric,
            compatibility_score=best_compat,
            selection_reason=reason,
            scientific_confidence=confidence,
            warnings=warnings,
            disclaimers=disclaimers
        )
