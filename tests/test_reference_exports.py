"""
Tests for ReferenceExportService (CSV, JSON, YAML exporters).
"""

import json
import yaml
from models.reference_data_models import ReferenceDataset, ReferenceMetric, ReferenceSource
from services.reference_export_service import ReferenceExportService

def test_csv_json_yaml_exports():
    ds = ReferenceDataset(
        dataset_id="ds_export_001",
        name="Olympic Export Study",
        stroke="FREESTYLE",
        age_min=18,
        age_max=25,
        sex="Male",
        source_type="PEER_REVIEWED_PRIMARY_STUDY",
        benchmark_eligibility="BENCHMARK",
        validation_status="SCIENTIFICALLY_VALIDATED",
        metrics=[ReferenceMetric(metric_name="stroke_rate", value_typical=58.0, unit="spm")],
        sources=[ReferenceSource(source_title="Olympic Study", authors="Jones et al.", publication_year=2024, doi="10.1016/j.jbiomech.2024.100")]
    )

    # 1. CSV Export
    csv_out = ReferenceExportService.export_to_csv([ds])
    assert "ds_export_001" in csv_out
    assert "Olympic Export Study" in csv_out
    assert "stroke_rate" in csv_out
    assert "10.1016/j.jbiomech.2024.100" in csv_out

    # 2. JSON Export
    json_out = ReferenceExportService.export_to_json([ds])
    json_data = json.loads(json_out)
    assert len(json_data) == 1
    assert json_data[0]["name"] == "Olympic Export Study"
    assert json_data[0]["metrics"][0]["metric_name"] == "stroke_rate"

    # 3. YAML Export
    yaml_out = ReferenceExportService.export_to_yaml([ds])
    yaml_data = yaml.safe_load(yaml_out)
    assert "reference_datasets" in yaml_data
    assert yaml_data["reference_datasets"][0]["name"] == "Olympic Export Study"
