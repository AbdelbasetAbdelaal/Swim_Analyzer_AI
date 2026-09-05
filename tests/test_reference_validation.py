"""
Tests for ReferenceDataValidator and the 8 Scientific Integrity Rules.
"""

from models.reference_data_models import (
    ReferenceDataset, ReferenceMetric, ReferenceSource,
    ReferenceSourceType, ReferenceBenchmarkEligibility
)
from services.reference_data_validator import ReferenceDataValidator

def test_rule_1_coach_defined_defaults_to_context_only():
    """RULE 1: COACH_DEFINED datasets cannot automatically become scientific benchmarks."""
    ds = ReferenceDataset(
        name="Club Swim Reference",
        source_type=ReferenceSourceType.COACH_DEFINED.value,
        benchmark_eligibility=ReferenceBenchmarkEligibility.BENCHMARK.value
    )
    val_res = ReferenceDataValidator.validate_dataset(ds)
    assert val_res.suggested_eligibility == ReferenceBenchmarkEligibility.CONTEXT_ONLY.value
    assert any("Coach-defined reference" in d for d in val_res.disclaimers)

def test_rule_2_peer_reviewed_eligibility_criteria():
    """RULE 2: Peer-reviewed datasets holding BENCHMARK eligibility require full citation."""
    ds = ReferenceDataset(
        name="Peer Reviewed Primary Study",
        source_type=ReferenceSourceType.PEER_REVIEWED_PRIMARY_STUDY.value,
        benchmark_eligibility=ReferenceBenchmarkEligibility.BENCHMARK.value,
        sources=[ReferenceSource(source_type=ReferenceSourceType.PEER_REVIEWED_PRIMARY_STUDY.value)]  # Missing title/authors/doi
    )
    val_res = ReferenceDataValidator.validate_dataset(ds)
    assert val_res.suggested_eligibility == ReferenceBenchmarkEligibility.INSUFFICIENT_EVIDENCE.value

def test_rule_3_youth_and_masters_isolation():
    """RULE 3: Youth and Masters data must NOT be silently treated as adult general population benchmarks."""
    ds_youth = ReferenceDataset(name="Youth Swimmers", age_min=10, age_max=13)
    val_youth = ReferenceDataValidator.validate_dataset(ds_youth)
    assert any("Youth Cohort" in d for d in val_youth.disclaimers)

    ds_masters = ReferenceDataset(name="Masters Swimmers", age_min=40, age_max=55)
    val_masters = ReferenceDataValidator.validate_dataset(ds_masters)
    assert any("Masters Cohort" in d for d in val_masters.disclaimers)

def test_rule_4_coach_disclaimer():
    """RULE 4: Coach-entered datasets must carry disclaimer."""
    ds = ReferenceDataset(name="My Team Baseline", source_type="COACH_DEFINED")
    val_res = ReferenceDataValidator.validate_dataset(ds)
    assert "Coach-defined reference — not a universal scientific benchmark." in val_res.disclaimers

def test_rule_6_invalid_range_ordering():
    """RULE 6: Invalid range ordering (min > max or min > typical) fails validation."""
    metric_bad_min_max = ReferenceMetric(
        metric_name="stroke_rate",
        value_min=65.0,
        value_max=55.0,  # Invalid: min > max
        unit="spm",
        measurement_domain="CALIBRATED_PHYSICAL"
    )
    val_m1 = ReferenceDataValidator.validate_metric(metric_bad_min_max)
    assert val_m1.is_valid is False
    assert any("cannot be greater than value_max" in e for e in val_m1.errors)

    metric_bad_typ = ReferenceMetric(
        metric_name="stroke_rate",
        value_min=50.0,
        value_typical=45.0,  # Invalid: min > typical
        value_max=60.0,
        unit="spm",
        measurement_domain="CALIBRATED_PHYSICAL"
    )
    val_m2 = ReferenceDataValidator.validate_metric(metric_bad_typ)
    assert val_m2.is_valid is False
    assert any("cannot be greater than value_typical" in e for e in val_m2.errors)

def test_rule_8_incompatible_dataset_merge_prevention():
    """RULE 8: Do not merge datasets with incompatible stroke, age, sex, or skill level."""
    ds_freestyle = ReferenceDataset(name="FS Dataset", stroke="FREESTYLE", age_min=18, age_max=25, sex="Male")
    ds_butterfly = ReferenceDataset(name="FLY Dataset", stroke="BUTTERFLY", age_min=18, age_max=25, sex="Male")

    can_merge, reasons = ReferenceDataValidator.validate_dataset_merge(ds_freestyle, ds_butterfly)
    assert can_merge is False
    assert any("Incompatible stroke types" in r for r in reasons)
