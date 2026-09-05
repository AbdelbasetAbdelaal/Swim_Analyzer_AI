"""
Tests for ReferenceCSVNormalizer schema normalization layer.
Verifies column cleanup, source_type mapping, and dataset context resolution.
"""

from services.reference_csv_normalizer import ReferenceCSVNormalizer

def test_normalization_source_type_mapping():
    raw_row = {
        "dataset_name": "European Finalists 2021",
        "stroke": "BUTTERFLY",
        "metric_name": "Start Time",
        "source_type": "PEER_REVIEWED_ORIGINAL_RESEARCH",
        "value_typical": "5.53"
    }

    norm = ReferenceCSVNormalizer.normalize_row(1, raw_row)
    assert norm.is_valid is True
    assert norm.dataset_name == "European Finalists 2021"
    assert norm.stroke == "BUTTERFLY"
    assert norm.source_type == "PEER_REVIEWED_PRIMARY_STUDY"
    assert norm.value_typical == 5.53

def test_missing_dataset_name_context_fallback():
    raw_row = {
        "stroke": "FREESTYLE",
        "metric_name": "Stroke Rate",
        "source_title": "Olympic Crawl Study 2024",
        "value_typical": "58.0"
    }

    norm = ReferenceCSVNormalizer.normalize_row(1, raw_row, dataset_metadata_context={"dataset_name": "Olympic Context"})
    assert norm.dataset_name == "Olympic Context"
