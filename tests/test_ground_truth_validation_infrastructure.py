"""
Comprehensive test suite for Ground Truth Validation Infrastructure (Step 68).
Verifies schemas, gating, leakage protection, comparison mathematics, runner isolation,
metadata recording, and scientific safety invariants.
"""
import json
import pytest
from pathlib import Path
import numpy as np

from analysis.validation.ground_truth_models import (
    GroundTruthSample,
    GroundTruthManifest,
    ManifestRecord,
    InclusionStatus,
    AnnotationStatus,
    QualityStatus,
    MeasurementType,
)
from analysis.validation.ground_truth_comparator import GroundTruthComparator, METRIC_REGISTRY
from analysis.validation.ground_truth_policy import (
    GroundTruthValidationPolicy,
    ValidationStatus,
    ThresholdStatus,
)
from analysis.validation.data_leakage_validator import DataLeakageValidator
from analysis.validation.ground_truth_runner import GroundTruthValidationRunner, get_git_commit_sha


@pytest.fixture
def repo_root():
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def runner(repo_root):
    return GroundTruthValidationRunner()


@pytest.fixture
def valid_sample_dict():
    return {
        "sample_id": "GT-FREE-001",
        "participant_id": "PARTICIPANT-001",
        "session_id": "SESS-2026-A",
        "stroke_type": "Freestyle",
        "video_id": "VID-001",
        "video_filename": "trial_01.mp4",
        "video_sha256": "a" * 64,
        "source_type": "HIGH_SPEED_OPTICAL_DUAL_RATER",
        "annotation_version": "1.0.0",
        "annotator_id": "RATER-A",
        "secondary_annotator_id": "RATER-B",
        "annotation_timestamp": "2026-09-06T10:00:00Z",
        "video_fps": 60.0,
        "video_duration": 15.0,
        "frame_count": 900,
        "exclusion_status": "INCLUDED",
        "exclusion_reason": None,
        "metric_annotations": {
            "stroke_rate_spm": 62.5,
            "cycle_duration_ms": 960.0,
            "mean_elbow_angle_deg": 115.0,
            "hand_excursion_proxy_bl": 1.25,
            "true_dps_meters": None,
            "body_roll_amplitude_deg": 38.0,
            "stroke_symmetry_percent": 96.0,
        },
        "quality_flags": {
            "occlusion_level": "LOW",
            "lighting_quality": "HIGH",
            "water_turbulence": "CALM",
            "inter_rater_agreement_icc": 0.96,
            "requires_adjudication": False,
        },
        "is_synthetic_fixture": False,
    }


# ---------------------------------------------------------------------------
# 1. Schema Validation Tests
# ---------------------------------------------------------------------------

def test_ground_truth_schema_valid(runner, valid_sample_dict):
    """Valid sample dictionary passes schema validation."""
    is_valid, err = runner.validate_sample_schema(valid_sample_dict)
    assert is_valid is True, f"Expected valid schema, got error: {err}"


def test_ground_truth_schema_missing_required_field(runner, valid_sample_dict):
    """Missing required field (participant_id) is rejected."""
    bad_sample = dict(valid_sample_dict)
    del bad_sample["participant_id"]
    is_valid, err = runner.validate_sample_schema(bad_sample)
    assert is_valid is False
    assert "participant_id" in err


def test_ground_truth_schema_invalid_type_rejection(runner, valid_sample_dict):
    """Invalid data type (string instead of float for video_fps) is rejected."""
    bad_sample = dict(valid_sample_dict)
    bad_sample["video_fps"] = "not-a-number"
    is_valid, err = runner.validate_sample_schema(bad_sample)
    assert is_valid is False


def test_ground_truth_manifest_schema_validation(runner):
    """Valid and invalid manifest payloads are correctly accepted and rejected."""
    valid_manifest = {
        "manifest_version": "1.0.0",
        "manifest_id": "MANIFEST-TEST-001",
        "created_at": "2026-09-06T10:00:00Z",
        "cohort_name": "Test Cohort",
        "protocol_version": "1.0.0",
        "records": [
            {
                "sample_id": "GT-FREE-001",
                "video_path": "data/ground_truth/raw/test.mp4",
                "stroke": "Freestyle",
                "participant_id": "PARTICIPANT-001",
                "annotation_file": "data/ground_truth/annotations/test.json",
                "annotation_status": "COMPLETE",
                "quality_status": "PASSED",
                "inclusion_status": "INCLUDED",
                "validator_version": "1.0.0",
            }
        ]
    }
    is_valid, err = runner.validate_manifest_schema(valid_manifest)
    assert is_valid is True, err

    # Bad manifest: missing records
    bad_manifest = dict(valid_manifest)
    del bad_manifest["records"]
    is_valid, err = runner.validate_manifest_schema(bad_manifest)
    assert is_valid is False


# ---------------------------------------------------------------------------
# 2. Manifest Filtering & Exclusion Gates
# ---------------------------------------------------------------------------

def test_manifest_ambiguous_sample_exclusion():
    """Ambiguous samples must be strictly excluded from eligible validation records."""
    manifest = GroundTruthManifest(
        manifest_version="1.0.0",
        manifest_id="M-01",
        created_at="2026-09-06T10:00:00Z",
        cohort_name="Cohort",
        protocol_version="1.0.0",
        records=[
            ManifestRecord(
                sample_id="GT-01", video_path="v1.mp4", stroke="Freestyle", participant_id="P1",
                annotation_file="a1.json", annotation_status="COMPLETE", quality_status="PASSED",
                inclusion_status=InclusionStatus.AMBIGUOUS.value, validator_version="1.0.0"
            ),
            ManifestRecord(
                sample_id="GT-02", video_path="v2.mp4", stroke="Freestyle", participant_id="P2",
                annotation_file="a2.json", annotation_status="COMPLETE", quality_status="PASSED",
                inclusion_status=InclusionStatus.INCLUDED.value, validator_version="1.0.0"
            ),
        ]
    )
    eligible = manifest.get_eligible_records()
    assert len(eligible) == 1
    assert eligible[0].sample_id == "GT-02"


def test_manifest_excluded_and_failed_samples_exclusion():
    """Explicitly excluded or quality-failed samples are filtered out."""
    manifest = GroundTruthManifest(
        manifest_version="1.0.0",
        manifest_id="M-01",
        created_at="2026-09-06T10:00:00Z",
        cohort_name="Cohort",
        protocol_version="1.0.0",
        records=[
            ManifestRecord(
                sample_id="GT-01", video_path="v1.mp4", stroke="Freestyle", participant_id="P1",
                annotation_file="a1.json", annotation_status="COMPLETE", quality_status="PASSED",
                inclusion_status=InclusionStatus.EXCLUDED.value, exclusion_reason="Turn included",
                validator_version="1.0.0"
            ),
            ManifestRecord(
                sample_id="GT-02", video_path="v2.mp4", stroke="Freestyle", participant_id="P2",
                annotation_file="a2.json", annotation_status="COMPLETE", quality_status=QualityStatus.FAILED.value,
                inclusion_status=InclusionStatus.INCLUDED.value, validator_version="1.0.0"
            ),
            ManifestRecord(
                sample_id="GT-03", video_path="v3.mp4", stroke="Freestyle", participant_id="P3",
                annotation_file="a3.json", annotation_status=AnnotationStatus.INCOMPLETE.value,
                quality_status=QualityStatus.PASSED.value, inclusion_status=InclusionStatus.INCLUDED.value,
                validator_version="1.0.0"
            ),
        ]
    )
    assert len(manifest.get_eligible_records()) == 0


# ---------------------------------------------------------------------------
# 3. Data Leakage Protection Tests
# ---------------------------------------------------------------------------

def test_participant_split_leakage_detection():
    """Participant appearing across both validation and non-validation splits triggers leakage failure."""
    records = [
        {"sample_id": "S1", "participant_id": "P-101", "video_id": "V1", "split": "VALIDATION_OFFICIAL"},
        {"sample_id": "S2", "participant_id": "P-102", "video_id": "V2", "split": "VALIDATION_OFFICIAL"},
        {"sample_id": "S3", "participant_id": "P-101", "video_id": "V3", "split": "EXPLORATORY"}, # LEAK!
    ]
    is_valid, errors = DataLeakageValidator.validate_manifest_splits(records)
    assert is_valid is False
    assert any("P-101" in err for err in errors)


def test_video_split_leakage_detection():
    """Video asset appearing across splits triggers leakage failure."""
    records = [
        {"sample_id": "S1", "participant_id": "P-101", "video_id": "V-SHARED", "split": "VALIDATION_OFFICIAL"},
        {"sample_id": "S2", "participant_id": "P-102", "video_id": "V-SHARED", "split": "BENCHMARK_CALIBRATION"},
    ]
    is_valid, errors = DataLeakageValidator.validate_manifest_splits(records)
    assert is_valid is False
    assert any("V-SHARED" in err for err in errors)


def test_clean_participant_split_passes():
    """Disjoint participant sets across splits pass without error."""
    records = [
        {"sample_id": "S1", "participant_id": "P-01", "video_id": "V1", "split": "VALIDATION_OFFICIAL"},
        {"sample_id": "S2", "participant_id": "P-02", "video_id": "V2", "split": "VALIDATION_OFFICIAL"},
        {"sample_id": "S3", "participant_id": "P-03", "video_id": "V3", "split": "EXPLORATORY"},
    ]
    is_valid, errors = DataLeakageValidator.validate_manifest_splits(records)
    assert is_valid is True
    assert len(errors) == 0


# ---------------------------------------------------------------------------
# 4. Statistical Comparator Mathematics
# ---------------------------------------------------------------------------

def test_comparator_statistics_accuracy():
    """Verifies exact algebraic correctness for MAE, RMSE, Bias, and MAPE."""
    y_ai = [60.0, 65.0, 70.0, 55.0]
    y_gt = [58.0, 64.0, 72.0, 56.0]
    # diffs = [+2.0, +1.0, -2.0, -1.0]
    # abs_diffs = [2.0, 1.0, 2.0, 1.0] -> sum = 6.0, mean = 1.5
    # sq_diffs = [4.0, 1.0, 4.0, 1.0] -> sum = 10.0, mean = 2.5 -> sqrt(2.5) = 1.58113883
    # bias = (2 + 1 - 2 - 1) / 4 = 0.0
    # mape = (2/58 + 1/64 + 2/72 + 1/56) / 4 * 100 = (0.03448 + 0.015625 + 0.027778 + 0.017857) / 4 * 100 = 2.3935%

    mae, rmse, bias, mape, r = GroundTruthComparator.compute_statistics(y_ai, y_gt)

    assert pytest.approx(mae, abs=1e-4) == 1.5
    assert pytest.approx(rmse, abs=1e-4) == np.sqrt(2.5)
    assert pytest.approx(bias, abs=1e-4) == 0.0
    assert mape is not None
    assert pytest.approx(mape, abs=1e-2) == 2.39
    assert r is not None and r > 0.90


def test_comparator_zero_valid_samples_handling():
    """Zero valid samples must handle gracefully without dividing by zero."""
    mae, rmse, bias, mape, r = GroundTruthComparator.compute_statistics([], [])
    assert mae is None
    assert rmse is None
    assert bias is None
    assert mape is None
    assert r is None

    res = GroundTruthComparator.compare_metric("stroke_rate", [])
    assert res.sample_count == 0
    assert res.valid_comparison_count == 0
    assert res.status == ValidationStatus.NOT_VALIDATED_INSUFFICIENT_GROUND_TRUTH.value
    assert res.threshold_status == ThresholdStatus.TBD_REQUIRES_DOMAIN_JUSTIFICATION.value


def test_comparator_missing_measurements_handling():
    """Handles missing AI or GT measurements by updating counters and computing on complete pairs only."""
    pairs = [
        (60.0, 60.0),
        (None, 62.0), # AI missing
        (58.0, None), # GT missing
        (None, None), # Both missing
        (64.0, 62.0), # Pair valid
    ]
    res = GroundTruthComparator.compare_metric("stroke_rate", pairs)
    assert res.sample_count == 5
    assert res.valid_comparison_count == 2
    assert res.missing_ai_count == 2
    assert res.missing_gt_count == 2
    assert pytest.approx(res.mae, abs=1e-4) == 1.0 # |60-60| + |64-62| / 2 = 1.0


# ---------------------------------------------------------------------------
# 5. Scientific Measurement Classification & Proxy Invariants
# ---------------------------------------------------------------------------

def test_stroke_length_proxy_classification_invariant():
    """Stroke length proxy must NOT be classified as physical center-of-mass translation."""
    sl_meta = METRIC_REGISTRY["stroke_length_proxy"]
    assert sl_meta["type"] == MeasurementType.PROXY_ESTIMATE_NORMALIZED.value
    assert sl_meta["unit"] == "BL"
    assert "NOT literal CoM displacement" in sl_meta["description"]

    true_dps_meta = METRIC_REGISTRY["true_dps"]
    assert true_dps_meta["type"] == MeasurementType.MEASURED_PHYSICAL_QUANTITY.value
    assert true_dps_meta["unit"] == "m"


def test_validation_policy_thresholds_tbd():
    """Default policy requires domain justification and does not invent thresholds."""
    status, thresh_status, notes = GroundTruthValidationPolicy.evaluate_metric_status(
        metric_name="stroke_rate",
        valid_count=15,
        mae=1.2,
        rmse=1.5,
        bias=0.1,
        custom_thresholds=None,
    )
    assert status == ValidationStatus.NOT_VALIDATED_INSUFFICIENT_GROUND_TRUTH.value
    assert thresh_status == ThresholdStatus.TBD_REQUIRES_DOMAIN_JUSTIFICATION.value
    assert "TBD — REQUIRES DOMAIN JUSTIFICATION" in notes


# ---------------------------------------------------------------------------
# 6. Synthetic Fixture Isolation & Runner Execution
# ---------------------------------------------------------------------------

def test_synthetic_fixture_isolation_gate(runner, repo_root):
    """Official validation run rejects synthetic manifest unless allow_synthetic is explicitly True."""
    synth_manifest_path = repo_root / "tests" / "fixtures" / "synthetic_ground_truth" / "synthetic_manifest.json"
    assert synth_manifest_path.exists(), "synthetic_manifest.json fixture must exist"

    # Must raise when allow_synthetic=False
    with pytest.raises(ValueError, match="SYNTHETIC FIXTURE ISOLATION GATE"):
        runner.run_validation_experiment(synth_manifest_path, allow_synthetic=False)

    # When allow_synthetic=True, execution succeeds but result is flagged as test fixture
    def mock_service(video_path, stroke_sel):
        return {"stroke_rate": 60.5, "cycle_duration": 995.0, "mean_elbow_angle": 108.0}

    result = runner.run_validation_experiment(
        synth_manifest_path,
        allow_synthetic=True,
        analysis_service_override=mock_service
    )
    assert result.metadata.is_synthetic_run is True
    assert result.overall_status == "TEST FIXTURE — NOT SCIENTIFIC GROUND TRUTH"
    assert "stroke_rate" in result.metric_comparisons
    sr_comp = result.metric_comparisons["stroke_rate"]
    assert sr_comp.valid_comparison_count == 1
    assert pytest.approx(sr_comp.mae, abs=1e-4) == 0.5


def test_validation_runner_metadata_and_commit_sha():
    """Validates that git commit SHA and run metadata are recorded correctly."""
    sha = get_git_commit_sha()
    assert isinstance(sha, str)
    assert len(sha) >= 7
    assert sha != "UNKNOWN_COMMIT_SHA"


def test_official_manifest_file_exists_and_empty(repo_root):
    """
    CRITICAL GROUND TRUTH GATE:
    Verifies that the official ground truth manifest exists, is valid according to schema,
    and has exactly 0 records, confirming that no unverified or fake ground truth is committed.
    """
    official_manifest_path = repo_root / "data" / "ground_truth" / "manifests" / "ground_truth_manifest.json"
    assert official_manifest_path.exists()

    with open(official_manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["manifest_version"] == "1.0.0"
    assert data["is_synthetic_manifest"] is False
    assert len(data["records"]) == 0
