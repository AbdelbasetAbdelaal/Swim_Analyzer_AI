"""
Tests for ReferenceCSVService validation, record type detection (METRIC vs SOURCE), and null preservation.
"""

from pathlib import Path
from services.reference_csv_service import ReferenceCSVService

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_FILE = str(PROJECT_ROOT / "data" / "reference" / "swimming_reference_data_v2_scientific_registry.csv")

def test_complete_155_row_registry_csv_validation():
    """Verifies that importing the complete 155-row CSV yields 155 valid rows and 0 invalid rows."""
    with open(CSV_FILE, encoding="utf-8-sig") as f:
        content = f.read()

    preview = ReferenceCSVService.parse_and_validate_csv(content)
    assert preview.total_rows == 155
    assert preview.valid_rows == 155
    assert preview.invalid_rows == 0
    assert preview.duplicate_rows == 0

def test_five_source_registry_records_are_valid_context_only():
    """Verifies that rows 151-155 are parsed as record_type SOURCE and status CONTEXT_ONLY."""
    with open(CSV_FILE, encoding="utf-8-sig") as f:
        content = f.read()

    preview = ReferenceCSVService.parse_and_validate_csv(content)
    source_rows = preview.row_results[150:]
    assert len(source_rows) == 5

    for r in source_rows:
        assert r.is_valid is True
        assert r.norm_row.record_type == "SOURCE"
        assert r.benchmark_eligibility == "CONTEXT_ONLY"
        assert "no metric_name required" in r.warnings[0]

def test_valid_metric_row_with_metric_name():
    raw_csv = "record_type,dataset_name,stroke,metric_name,unit,value_typical\nMETRIC,Olympic 2024,FREESTYLE,Swim Velocity,m/s,2.15\n"
    preview = ReferenceCSVService.parse_and_validate_csv(raw_csv)
    assert preview.valid_rows == 1
    assert preview.row_results[0].norm_row.record_type == "METRIC"
    assert preview.row_results[0].metric_name == "Swim Velocity"

def test_metric_row_without_metric_name_is_invalid():
    raw_csv = "record_type,dataset_name,stroke,unit,value_typical\nMETRIC,Olympic 2024,FREESTYLE,m/s,2.15\n"
    preview = ReferenceCSVService.parse_and_validate_csv(raw_csv)
    assert preview.invalid_rows == 1
    assert "Missing required field 'metric_name'." in preview.row_results[0].errors

def test_valid_source_row_without_metric_name():
    raw_csv = "record_type,dataset_name,stroke,source_title,doi\nSOURCE,SOURCE_REGISTRY_TEST,BACKSTROKE,Kinematic Review 2025,10.1016/test.2025\n"
    preview = ReferenceCSVService.parse_and_validate_csv(raw_csv)
    assert preview.valid_rows == 1
    r = preview.row_results[0]
    assert r.norm_row.record_type == "SOURCE"
    assert r.benchmark_eligibility == "CONTEXT_ONLY"

def test_null_value_preservation():
    raw_csv = "record_type,dataset_name,stroke,metric_name,value_min,value_typical,value_max\nMETRIC,Study 1,FREESTYLE,Stroke Rate,,,60.0\n"
    preview = ReferenceCSVService.parse_and_validate_csv(raw_csv)
    assert preview.valid_rows == 1
    m = preview.row_results[0].norm_row
    assert m.value_min is None
    assert m.value_typical is None
    assert m.value_max == 60.0
