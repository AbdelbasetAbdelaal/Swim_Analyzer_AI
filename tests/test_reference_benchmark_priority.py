"""
Tests for benchmark resolution priority rules.
Verifies that compatibility ALWAYS overrides priority hierarchy.
"""

from models.reference_data_models import ReferenceDataset, ReferenceMetric
from services.reference_resolver import ReferenceDataResolver

def test_compatibility_overrides_priority_hierarchy():
    """
    A scientifically validated adult male dataset must NOT outrank
    a matching 13-year-old dataset for a 13-year-old athlete.
    """
    ds_adult_peer = ReferenceDataset(
        dataset_id="ds_adult_peer",
        name="Adult Male Elite Study",
        stroke="FREESTYLE",
        age_min=18,
        age_max=25,
        sex="Male",
        source_type="PEER_REVIEWED_PRIMARY_STUDY",
        validation_status="SCIENTIFICALLY_VALIDATED",
        metrics=[ReferenceMetric(metric_name="stroke_rate", value_typical=58.0, unit="spm")]
    )

    ds_youth_coach = ReferenceDataset(
        dataset_id="ds_youth_coach",
        name="Youth 11-13 Team Reference",
        stroke="FREESTYLE",
        age_min=11,
        age_max=13,
        sex="Male",
        source_type="COACH_DEFINED",
        validation_status="COACH_VALIDATED",
        metrics=[ReferenceMetric(metric_name="stroke_rate", value_typical=50.0, unit="spm")]
    )

    # Resolving for a 12-year-old athlete: ds_adult_peer gives 0 score due to age boundary violation!
    resolved = ReferenceDataResolver.resolve_metric_reference(
        datasets=[ds_adult_peer, ds_youth_coach],
        metric_name="stroke_rate",
        stroke="FREESTYLE",
        athlete_age=12,
        athlete_sex="Male"
    )

    assert resolved.selected_dataset_id == "ds_youth_coach"
    assert resolved.selected_dataset_name == "Youth 11-13 Team Reference"
    assert any("Youth Cohort" in d for d in resolved.disclaimers)
