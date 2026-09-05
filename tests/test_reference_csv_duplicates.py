"""
Tests for canonical identity duplicate detection with record_type support.
Verifies that SOURCE and METRIC records with distinct identities are NOT false duplicates.
"""

from services.reference_csv_service import ReferenceCSVService

def test_distance_differentiation_prevents_false_duplicates():
    raw_csv = (
        "record_type,dataset_name,stroke,event_distance,sex,metric_name,unit,value_typical\n"
        "METRIC,EUROPEAN_FINALISTS_2021_MALE,BUTTERFLY,100m,Male,Start Time,s,5.53\n"
        "METRIC,EUROPEAN_FINALISTS_2021_MALE,BUTTERFLY,200m,Male,Start Time,s,5.91\n"
    )

    preview = ReferenceCSVService.parse_and_validate_csv(raw_csv)
    assert preview.total_rows == 2
    assert preview.valid_rows == 2
    assert preview.duplicate_rows == 0

def test_source_and_metric_isolation_in_duplicates():
    raw_csv = (
        "record_type,dataset_name,stroke,source_title,doi\n"
        "SOURCE,SOURCE_REGISTRY_TEST_1,FREESTYLE,CRAWL REVIEW,10.1016/c1\n"
        "SOURCE,SOURCE_REGISTRY_TEST_2,FREESTYLE,CRAWL REVIEW 2,10.1016/c2\n"
    )
    preview = ReferenceCSVService.parse_and_validate_csv(raw_csv)
    assert preview.total_rows == 2
    assert preview.valid_rows == 2
    assert preview.duplicate_rows == 0

def test_actual_duplicate_detection():
    raw_csv = (
        "record_type,dataset_name,stroke,event_distance,sex,metric_name,unit,value_typical\n"
        "METRIC,EUROPEAN_FINALISTS_2021_MALE,BUTTERFLY,100m,Male,Start Time,s,5.53\n"
        "METRIC,EUROPEAN_FINALISTS_2021_MALE,BUTTERFLY,100m,Male,Start Time,s,5.53\n"
    )

    preview = ReferenceCSVService.parse_and_validate_csv(raw_csv)
    assert preview.duplicate_rows == 1
