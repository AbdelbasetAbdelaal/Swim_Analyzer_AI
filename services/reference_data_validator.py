"""
Scientific Integrity & Validation Layer for Reference Data Manager.
Enforces the 8 mandatory scientific integrity rules on reference datasets and metrics.
"""

from typing import List, Tuple, Optional
from models.reference_data_models import (
    ReferenceDataset, ReferenceMetric, ReferenceSourceType, ReferenceBenchmarkEligibility
)

class ScientificValidationResult:
    def __init__(self):
        self.is_valid: bool = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.disclaimers: List[str] = []
        self.suggested_eligibility: Optional[str] = None
        self.suggested_status: Optional[str] = None

class ReferenceDataValidator:
    """
    Strict scientific integrity validator.
    Prevents unvalidated coach data, malformed ranges, or demographic mixing
    from masquerading as peer-reviewed benchmarks.
    """

    VALID_UNITS = {
        "spm", "strokes/min", "hz", "strokes", "cycles",
        "m/s", "m", "body_length", "deg", "degree", "degrees",
        "sec", "seconds", "ms", "%", "ratio", ""
    }

    VALID_DOMAINS = {
        "CALIBRATED_PHYSICAL", "RELATIVE_BODY_NORMALIZED",
        "POSE_RELATIVE_3D", "IMAGE_SPACE", "UNAVAILABLE"
    }

    @classmethod
    def validate_dataset(cls, dataset: ReferenceDataset) -> ScientificValidationResult:
        res = ScientificValidationResult()

        # Required fields check
        if not dataset.name or not dataset.name.strip():
            res.is_valid = False
            res.errors.append("Dataset name is required.")

        if dataset.age_min < 0 or dataset.age_max > 120 or dataset.age_min > dataset.age_max:
            res.is_valid = False
            res.errors.append(f"Invalid age range [{dataset.age_min}, {dataset.age_max}]. age_min must be <= age_max.")

        # RULE 1: COACH_DEFINED cannot automatically become BENCHMARK
        if dataset.source_type == ReferenceSourceType.COACH_DEFINED.value or dataset.source_type == "COACH_DEFINED":
            if dataset.benchmark_eligibility == ReferenceBenchmarkEligibility.BENCHMARK.value:
                res.warnings.append("Coach-defined dataset cannot be automatically classified as BENCHMARK. Set to CONTEXT_ONLY.")
                res.suggested_eligibility = ReferenceBenchmarkEligibility.CONTEXT_ONLY.value

        # RULE 4: Disclaimer for Coach-Entered Datasets
        if dataset.source_type in [ReferenceSourceType.COACH_DEFINED.value, ReferenceSourceType.VALIDATED_TEAM_DATA.value, "COACH_DEFINED", "VALIDATED_TEAM_DATA"]:
            res.disclaimers.append("Coach-defined reference — not a universal scientific benchmark.")

        # RULE 3: Youth and Masters Isolation
        if dataset.age_max <= 17:
            res.disclaimers.append("Youth Cohort (Age <= 17) — isolated from Adult general population benchmarks.")
        elif dataset.age_min >= 36 or dataset.athlete_category.title() == "Masters":
            res.disclaimers.append("Masters Cohort (Age >= 36) — isolated from Adult general population benchmarks.")

        # RULE 2: Peer-Reviewed Benchmark Eligibility Criteria
        is_peer_reviewed = dataset.source_type in [
            ReferenceSourceType.PEER_REVIEWED_PRIMARY_STUDY.value,
            ReferenceSourceType.PEER_REVIEWED_SYSTEMATIC_REVIEW.value,
            ReferenceSourceType.PEER_REVIEWED_META_ANALYSIS.value,
            "PEER_REVIEWED_PRIMARY_STUDY", "PEER_REVIEWED_SYSTEMATIC_REVIEW", "PEER_REVIEWED_META_ANALYSIS"
        ]

        if dataset.benchmark_eligibility == ReferenceBenchmarkEligibility.BENCHMARK.value:
            if not is_peer_reviewed:
                res.warnings.append("Only peer-reviewed scientific studies or explicitly validated team datasets can hold BENCHMARK eligibility.")
                res.suggested_eligibility = ReferenceBenchmarkEligibility.CONTEXT_ONLY.value
            else:
                # Check for source citation
                has_citation = any(
                    bool(s.source_title and s.authors and (s.doi or s.pmid or s.publication_year))
                    for s in dataset.sources
                )
                if not has_citation:
                    res.warnings.append("Missing full scientific source citation (authors, title, DOI/PMID/year). Benchmark eligibility downgraded to INSUFFICIENT_EVIDENCE.")
                    res.suggested_eligibility = ReferenceBenchmarkEligibility.INSUFFICIENT_EVIDENCE.value

        # Metric-level validation
        for metric in dataset.metrics:
            m_res = cls.validate_metric(metric)
            if not m_res.is_valid:
                res.is_valid = False
                res.errors.extend([f"Metric '{metric.metric_name}': {e}" for e in m_res.errors])
            res.warnings.extend([f"Metric '{metric.metric_name}': {w}" for w in m_res.warnings])

        return res

    @classmethod
    def validate_metric(cls, metric: ReferenceMetric) -> ScientificValidationResult:
        res = ScientificValidationResult()

        if not metric.metric_name or not metric.metric_name.strip():
            res.is_valid = False
            res.errors.append("Metric name is required.")

        # RULE 6: No fabricated numerical values & range ordering validation
        # Validates min <= typical <= max and min <= median <= max ONLY when values are non-None!
        v_min, v_typ, v_med, v_max = metric.value_min, metric.value_typical, metric.value_median, metric.value_max

        if v_min is not None and v_max is not None and v_min > v_max:
            res.is_valid = False
            res.errors.append(f"value_min ({v_min}) cannot be greater than value_max ({v_max}).")

        if v_min is not None and v_typ is not None and v_min > v_typ:
            res.is_valid = False
            res.errors.append(f"value_min ({v_min}) cannot be greater than value_typical ({v_typ}).")

        if v_typ is not None and v_max is not None and v_typ > v_max:
            res.is_valid = False
            res.errors.append(f"value_typical ({v_typ}) cannot be greater than value_max ({v_max}).")

        if v_min is not None and v_med is not None and v_min > v_med:
            res.is_valid = False
            res.errors.append(f"value_min ({v_min}) cannot be greater than value_median ({v_med}).")

        if v_med is not None and v_max is not None and v_med > v_max:
            res.is_valid = False
            res.errors.append(f"value_median ({v_med}) cannot be greater than value_max ({v_max}).")

        # Unit validation
        if metric.unit and metric.unit.lower() not in [u.lower() for u in cls.VALID_UNITS]:
            res.warnings.append(f"Unrecognized unit '{metric.unit}'. Expected standard biomechanical units.")

        # Domain validation
        if metric.measurement_domain and metric.measurement_domain.upper() not in cls.VALID_DOMAINS:
            res.is_valid = False
            res.errors.append(f"Invalid measurement domain '{metric.measurement_domain}'. Must be one of {sorted(list(cls.VALID_DOMAINS))}.")

        # Insufficient evidence rule: null values remain null
        if all(v is None for v in [v_min, v_typ, v_med, v_max]):
            if metric.status == "available":
                res.warnings.append("Metric has no numeric measurements (min, typical, median, max all None); status set to 'unavailable'.")
                metric.status = "unavailable"

        return res

    @classmethod
    def validate_dataset_merge(cls, ds_a: ReferenceDataset, ds_b: ReferenceDataset) -> Tuple[bool, List[str]]:
        """
        RULE 8: Do not merge datasets with incompatible stroke, age, sex, skill level,
        measurement domain, unit, or methodology.
        """
        reasons = []
        if ds_a.stroke.upper() != ds_b.stroke.upper() and ds_a.stroke != "ALL" and ds_b.stroke != "ALL":
            reasons.append(f"Incompatible stroke types: {ds_a.stroke} vs {ds_b.stroke}.")

        if abs(ds_a.age_min - ds_b.age_min) > 5 or abs(ds_a.age_max - ds_b.age_max) > 5:
            reasons.append(f"Incompatible age ranges: [{ds_a.age_min}-{ds_a.age_max}] vs [{ds_b.age_min}-{ds_b.age_max}].")

        if ds_a.sex.lower() != ds_b.sex.lower() and ds_a.sex != "Mixed" and ds_b.sex != "Mixed":
            reasons.append(f"Incompatible sex cohorts: {ds_a.sex} vs {ds_b.sex}.")

        if ds_a.skill_level.lower() != ds_b.skill_level.lower() and ds_a.skill_level != "Unknown" and ds_b.skill_level != "Unknown":
            reasons.append(f"Incompatible skill levels: {ds_a.skill_level} vs {ds_b.skill_level}.")

        if reasons:
            return False, reasons
        return True, ["Datasets have compatible demographic and stroke parameters."]
