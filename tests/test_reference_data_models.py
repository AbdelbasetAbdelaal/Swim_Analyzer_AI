"""
Tests for Reference Data Manager domain models and dataclass defaults.
"""

from models.reference_data_models import (
    ReferenceDataset, ReferenceMetric, ReferenceStrokeType, ReferenceSkillLevel, ReferenceAthleteCategory,
    ReferenceSourceType, ReferenceBenchmarkEligibility, ReferenceValidationStatus,
    ReferenceMeasurementDomain
)

def test_reference_dataset_creation_and_defaults():
    ds = ReferenceDataset(
        name="Test Freestyle Dataset",
        stroke=ReferenceStrokeType.FREESTYLE.value,
        age_min=18,
        age_max=25,
        sex="Male",
        skill_level=ReferenceSkillLevel.ELITE.value,
        athlete_category=ReferenceAthleteCategory.ADULT.value
    )

    assert ds.name == "Test Freestyle Dataset"
    assert ds.stroke == "FREESTYLE"
    assert ds.age_min == 18
    assert ds.age_max == 25
    assert ds.sex == "Male"
    assert ds.source_type == ReferenceSourceType.COACH_DEFINED.value
    assert ds.evidence_status == "INSUFFICIENT_EVIDENCE"
    assert ds.benchmark_eligibility == ReferenceBenchmarkEligibility.CONTEXT_ONLY.value
    assert ds.validation_status == ReferenceValidationStatus.DRAFT.value
    assert ds.is_archived is False
    assert ds.metrics == []
    assert ds.sources == []
    assert ds.validation_events == []

def test_null_metric_values_preserved():
    """Verify that null metric values remain null and are not coerced to 0 or 100."""
    metric = ReferenceMetric(
        metric_name="stroke_rate",
        display_name="Stroke Rate",
        value_min=None,
        value_typical=None,
        value_median=None,
        value_max=None,
        unit="spm",
        measurement_domain=ReferenceMeasurementDomain.CALIBRATED_PHYSICAL.value,
        status="unavailable"
    )

    assert metric.value_min is None
    assert metric.value_typical is None
    assert metric.value_median is None
    assert metric.value_max is None
    assert metric.status == "unavailable"
