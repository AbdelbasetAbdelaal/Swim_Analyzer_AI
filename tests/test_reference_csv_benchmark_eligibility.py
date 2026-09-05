"""
Tests for scientific benchmark eligibility policy in CSV pipeline.
Verifies Strict Mode reset for coach data and adult vs youth boundary preservation.
"""

from services.reference_csv_service import ReferenceCSVService

def test_strict_mode_coach_data_remains_context_only():
    raw_csv = (
        "dataset_name,stroke,metric_name,unit,value_typical,source_type,benchmark_eligibility\n"
        "Coach Training Targets,FREESTYLE,Stroke Rate,spm,58.0,COACH_DEFINED,BENCHMARK\n"
    )

    preview = ReferenceCSVService.parse_and_validate_csv(raw_csv, strict_scientific_mode=True)
    assert preview.valid_rows == 1
    r = preview.row_results[0]
    assert r.benchmark_eligibility == "CONTEXT_ONLY"

def test_adult_validated_data_can_be_benchmark():
    raw_csv = (
        "dataset_name,stroke,metric_name,unit,value_typical,source_type,benchmark_eligibility\n"
        "European Finalists 2021,BUTTERFLY,Stroke Rate,spm,56.1,PEER_REVIEWED_PRIMARY_STUDY,BENCHMARK\n"
    )

    preview = ReferenceCSVService.parse_and_validate_csv(raw_csv, strict_scientific_mode=True)
    assert preview.valid_rows == 1
    r = preview.row_results[0]
    assert r.benchmark_eligibility == "BENCHMARK"
