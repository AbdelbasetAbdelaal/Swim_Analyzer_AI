"""
Tests for Benchmark Priority and Eligibility Policy.
Verifies P0 vs P1 vs P2 behavior and explicit eligibility conditions.
"""

from models.reference_data_models import ReferenceDataset, ReferenceMetric
from services.reference_resolver import ReferenceDataResolver

def test_p0_validated_benchmark_outranks_p2_contextual():
    ds_p0 = ReferenceDataset(
        dataset_id="ds_p0",
        name="P0 European Finalists Study",
        stroke="FREESTYLE",
        age_min=18,
        age_max=25,
        sex="Male",
        source_type="PEER_REVIEWED_PRIMARY_STUDY",
        benchmark_eligibility="BENCHMARK",
        benchmark_priority="P0",
        validation_status="VALIDATED_REFERENCE",
        metrics=[ReferenceMetric(metric_name="stroke_rate", value_typical=56.0, unit="spm")]
    )

    ds_p2 = ReferenceDataset(
        dataset_id="ds_p2",
        name="P2 Contextual Review",
        stroke="FREESTYLE",
        age_min=18,
        age_max=25,
        sex="Male",
        source_type="COACH_DEFINED",
        benchmark_eligibility="CONTEXT_ONLY",
        benchmark_priority="P2",
        validation_status="DRAFT",
        metrics=[ReferenceMetric(metric_name="stroke_rate", value_typical=60.0, unit="spm")]
    )

    resolved = ReferenceDataResolver.resolve_metric_reference(
        datasets=[ds_p2, ds_p0],
        metric_name="stroke_rate",
        stroke="FREESTYLE",
        athlete_age=20,
        athlete_sex="Male"
    )

    assert resolved.selected_dataset_id == "ds_p0"
    assert resolved.selected_dataset_name == "P0 European Finalists Study"

def test_incompatible_cohort_returns_zero_score():
    ds = ReferenceDataset(
        name="Youth 10-12 Reference",
        stroke="FREESTYLE",
        age_min=10,
        age_max=12,
        sex="Male"
    )
    # 25-year-old adult matching against youth 10-12
    score, warn = ReferenceDataResolver.calculate_compatibility(ds, stroke="FREESTYLE", age=25, sex="Male")
    assert score == 0.0
    assert any("Youth vs Adult age boundary violation" in w for w in warn)
