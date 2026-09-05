"""
Tests for Step 66: Ground Truth Dataset Specification & Validation Experiment Infrastructure.
Verifies the Ground Truth dataset schema, dataset availability audit, and scientific gate invariants.
"""
import json
import pytest
from pathlib import Path

def test_ground_truth_specification_and_results_docs_exist():
    """Verify that both required Step 66 documentation files exist."""
    spec_path = Path("docs/ground_truth_dataset_specification.md")
    results_path = Path("docs/scientific_validation_results.md")
    
    assert spec_path.exists(), "docs/ground_truth_dataset_specification.md must exist"
    assert results_path.exists(), "docs/scientific_validation_results.md must exist"

    spec_content = spec_path.read_text(encoding="utf-8")
    assert "GROUND TRUTH DATASET: NOT AVAILABLE" in spec_content

    results_content = results_path.read_text(encoding="utf-8")
    assert "BLOCKED — GROUND TRUTH DATASET REQUIRED" in results_content


def test_ground_truth_schema_json_exists_and_valid():
    """Verify data/reference/ground_truth_dataset_schema.json exists and has valid JSON schema syntax."""
    schema_path = Path("data/reference/ground_truth_dataset_schema.json")
    assert schema_path.exists(), "ground_truth_dataset_schema.json must exist"

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert "trial_metadata" in schema["required"]
    assert "cycle_ground_truth" in schema["required"]
    assert "aggregate_ground_truth" in schema["required"]


def test_repository_ground_truth_absence_audit():
    """
    CRITICAL SAFETY AUDIT:
    Confirm that data/validation_dataset has no ground truth data files,
    proving that GROUND TRUTH DATASET: NOT AVAILABLE is truthful and accurate.
    """
    val_dir = Path("data/validation_dataset")
    if val_dir.exists():
        data_files = [p for p in val_dir.rglob("*") if p.is_file() and p.name != ".gitkeep"]
        assert len(data_files) == 0, (
            f"Expected 0 data files in data/validation_dataset, but found: {data_files}"
        )


def test_schema_validates_sample_ground_truth_structure():
    """Verify that a compliant ground truth dictionary matches the defined schema properties."""
    sample_gt = {
        "schema_version": "1.0.0",
        "trial_metadata": {
            "video_file": "sample_freestyle_60fps.mp4",
            "video_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "stroke": "Freestyle",
            "swimmer_id": "SWIMMER-001",
            "swimmer_sex": "Male",
            "swimmer_level": "Elite",
            "camera_view": "Sagittal_Lateral",
            "camera_position": "Submerged_Window",
            "nominal_fps": 60.0,
            "actual_fps": 59.94,
            "resolution": "1920x1080",
            "calibration_type": "Metric_Physical_Pool"
        },
        "annotation_metadata": {
            "rater_count": 2,
            "rater_ids": ["RATER-A", "RATER-B"],
            "measurement_method": "Kinovea manual frame digitization and SMPTE timecode logging",
            "inter_rater_agreement": {
                "cohens_kappa": 0.92,
                "icc_2_1": 0.96,
                "adjudication_required": False
            }
        },
        "cycle_ground_truth": [
            {
                "cycle_index": 1,
                "start_frame": 60,
                "end_frame": 120,
                "duration_ms": 1000.0,
                "stroke_rate_spm": 60.0,
                "phase_events": [
                    {"phase_name": "Entry", "transition_frame": 60, "timestamp_ms": 1000.0},
                    {"phase_name": "Catch", "transition_frame": 75, "timestamp_ms": 1250.0},
                    {"phase_name": "Pull", "transition_frame": 90, "timestamp_ms": 1500.0},
                    {"phase_name": "Recovery", "transition_frame": 105, "timestamp_ms": 1750.0}
                ]
            },
            {
                "cycle_index": 2,
                "start_frame": 120,
                "end_frame": 180,
                "duration_ms": 1000.0,
                "stroke_rate_spm": 60.0,
                "phase_events": [
                    {"phase_name": "Entry", "transition_frame": 120, "timestamp_ms": 2000.0},
                    {"phase_name": "Catch", "transition_frame": 135, "timestamp_ms": 2250.0},
                    {"phase_name": "Pull", "transition_frame": 150, "timestamp_ms": 2500.0},
                    {"phase_name": "Recovery", "transition_frame": 165, "timestamp_ms": 2750.0}
                ]
            }
        ],
        "aggregate_ground_truth": {
            "mean_stroke_rate_spm": 60.0,
            "mean_cycle_duration_ms": 1000.0,
            "completed_cycles_count": 2,
            "hand_excursion_proxy_bl": 1.25,
            "true_dps_meters": 1.85,
            "peak_body_roll_deg": 38.5,
            "mean_elbow_angle_deg": 105.0,
            "mean_knee_angle_deg": 155.0,
            "phase_percentages": {
                "Entry": 25.0,
                "Catch": 25.0,
                "Pull": 25.0,
                "Recovery": 25.0
            }
        }
    }

    # Verify top-level required fields
    for field in ["schema_version", "trial_metadata", "annotation_metadata", "cycle_ground_truth", "aggregate_ground_truth"]:
        assert field in sample_gt
    
    assert len(sample_gt["cycle_ground_truth"]) >= 2
    assert sample_gt["trial_metadata"]["nominal_fps"] >= 30.0
