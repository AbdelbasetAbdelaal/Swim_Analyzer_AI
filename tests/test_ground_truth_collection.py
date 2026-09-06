"""
Tests for STEP 70: Real Ground Truth Data Collection, Double-Blind QC, and Manifest Ingestion.
Verifies AI freeze record, double-blind audit preservation, agreement metrics, and ingestion gates.
"""
import os
import sys
import json
import copy
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analysis.validation.ground_truth_qc import (
    GroundTruthQCEngine,
    calculate_icc_2_1,
    FORBIDDEN_AI_KEYS,
)
from analysis.validation.ground_truth_ingestion import GroundTruthIngestionService, compute_file_sha256
from analysis.validation.ground_truth_runner import GroundTruthValidationRunner
from analysis.validation.data_leakage_validator import DataLeakageValidator
from analysis.validation.ground_truth_models import InclusionStatus, AnnotationStatus


@pytest.fixture
def repo_root():
    return Path(__file__).resolve().parent.parent


def test_validation_freeze_record_integrity(repo_root):
    """Verifies that the validation freeze record exists and contains the immutable commit SHA and statement."""
    freeze_doc = repo_root / "docs" / "scientific" / "validation_freeze_record.md"
    assert freeze_doc.exists(), "validation_freeze_record.md must exist."
    content = freeze_doc.read_text(encoding="utf-8")
    
    assert "db33130abb4af653ccacc4bec872be25233b59e4" in content
    assert "The AI implementation used for the official validation cohort is frozen before Ground Truth annotation and validation." in content
    assert "SwimAnalyzer-1.0.0" in content


def test_pilot_cohort_manifest_integrity(repo_root):
    """Verifies the official pilot manifest has 8 valid records, 2 per stroke, 1:1 participant mapping."""
    manifest_path = repo_root / "data" / "ground_truth" / "manifests" / "ground_truth_manifest.json"
    assert manifest_path.exists(), "ground_truth_manifest.json must exist."
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    runner = GroundTruthValidationRunner()
    is_valid, err = runner.validate_manifest_schema(manifest_data)
    assert is_valid, f"Manifest failed schema validation: {err}"

    records = manifest_data.get("records", [])
    assert len(records) == 8, f"Expected 8 pilot records, found {len(records)}"

    strokes = [r["stroke"] for r in records]
    assert strokes.count("Freestyle") == 2
    assert strokes.count("Backstroke") == 2
    assert strokes.count("Breaststroke") == 2
    assert strokes.count("Butterfly") == 2

    # Check 1:1 independent participants
    p_ids = [r["participant_id"] for r in records]
    assert len(set(p_ids)) == 8, "Each pilot trial must belong to an independent participant."

    # Verify all are official validation split and included
    for r in records:
        assert r["split"] == "VALIDATION_OFFICIAL"
        assert r["inclusion_status"] == InclusionStatus.INCLUDED.value
        assert r["annotation_status"] == AnnotationStatus.COMPLETE.value


def test_pilot_qc_audit_trail_completeness(repo_root):
    """Verifies all 8 pilot samples preserve the full 5-file double-blind QC audit trail."""
    qc_base = repo_root / "data" / "ground_truth" / "quality_control"
    sample_ids = [
        "GT-FREE-001", "GT-FREE-002",
        "GT-BACK-001", "GT-BACK-002",
        "GT-BRST-001", "GT-BRST-002",
        "GT-FLY-001", "GT-FLY-002"
    ]

    for sid in sample_ids:
        sample_dir = qc_base / sid
        assert sample_dir.is_dir(), f"QC directory missing for {sid}"
        for required_file in ["rater_A.json", "rater_B.json", "agreement.json", "adjudication.json", "final_ground_truth.json"]:
            fp = sample_dir / required_file
            assert fp.is_file(), f"Required audit file '{required_file}' missing for {sid}"
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
                assert len(data) > 0


def test_blinding_enforcement(repo_root):
    """Verifies that GroundTruthQCEngine rejects rater data containing forbidden AI prediction keys."""
    qc_engine = GroundTruthQCEngine(repo_root=repo_root)

    # Clean annotation
    clean_rater = {"annotator_id": "RATER_01", "sample_id": "GT-FREE-001", "metrics": {"stroke_rate": 45.0}}
    violations = qc_engine.verify_blinding(clean_rater, "Rater A")
    assert len(violations) == 0

    # Polluted with AI predictions
    for forbidden in ["overall_score", "technique_score", "reliability_score", "predicted_stroke"]:
        dirty_rater = copy.deepcopy(clean_rater)
        dirty_rater[forbidden] = 95.0
        violations = qc_engine.verify_blinding(dirty_rater, "Rater A")
        assert len(violations) > 0, f"Expected violation for forbidden key '{forbidden}'"


def test_icc_2_1_calculation():
    """Verifies two-way random ICC(2,1) calculation on known pairs."""
    # Identical ratings -> ICC = 1.0
    pairs_identical = [(40.0, 40.0), (45.0, 45.0), (50.0, 50.0), (55.0, 55.0)]
    icc = calculate_icc_2_1(pairs_identical)
    assert icc == 1.0

    # Near identical ratings with slight variance -> ICC >= 0.95
    pairs_near = [(40.0, 40.5), (45.0, 44.8), (50.0, 50.2), (55.0, 54.9)]
    icc_near = calculate_icc_2_1(pairs_near)
    assert icc_near >= 0.95

    # Low agreement -> ICC < 0.90
    pairs_poor = [(40.0, 60.0), (50.0, 30.0), (45.0, 70.0), (60.0, 40.0)]
    icc_poor = calculate_icc_2_1(pairs_poor)
    assert icc_poor < 0.90


def test_temporal_frame_discrepancy_gate(repo_root):
    """Verifies inter-rater agreement flags divergence exceeding the 2-frame tolerance."""
    qc_engine = GroundTruthQCEngine(repo_root=repo_root)

    rater_a = {
        "annotator_id": "RATER_A",
        "cycle_annotations": [{"start_frame": 10, "end_frame": 50}],
        "metric_annotations": {"stroke_rate_spm": {"value": 45.0}}
    }

    # Within tolerance (diff = 1 frame)
    rater_b_ok = {
        "annotator_id": "RATER_B",
        "cycle_annotations": [{"start_frame": 11, "end_frame": 50}],
        "metric_annotations": {"stroke_rate_spm": {"value": 45.3}}
    }
    report_ok = qc_engine.evaluate_inter_rater_agreement("GT-TEST-001", rater_a, rater_b_ok, max_frame_tolerance=2)
    assert report_ok["all_temporal_passed"] is True
    assert report_ok["requires_adjudication"] is False

    # Exceeding tolerance (diff = 4 frames)
    rater_b_fail = {
        "annotator_id": "RATER_B",
        "cycle_annotations": [{"start_frame": 14, "end_frame": 50}],
        "metric_annotations": {"stroke_rate_spm": {"value": 45.3}}
    }
    report_fail = qc_engine.evaluate_inter_rater_agreement("GT-TEST-002", rater_a, rater_b_fail, max_frame_tolerance=2)
    assert report_fail["all_temporal_passed"] is False
    assert report_fail["requires_adjudication"] is True


def test_ingestion_duplicate_rejection(repo_root, tmp_path):
    """Verifies that GroundTruthIngestionService rejects duplicate sample_id."""
    manifest_file = tmp_path / "test_manifest.json"
    manifest_data = {
        "manifest_version": "1.0.0",
        "manifest_id": "MANIFEST-TEST",
        "created_at": "2026-09-06T12:00:00Z",
        "cohort_name": "Test Cohort",
        "protocol_version": "1.0.0",
        "description": "Test",
        "is_synthetic_manifest": False,
        "records": []
    }
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f)

    video_file = repo_root / "data" / "ground_truth" / "raw" / "freestyle" / "GT-FREE-001.mp4"
    ann_file = repo_root / "data" / "ground_truth" / "annotations" / "GT-FREE-001.json"
    
    ingestion = GroundTruthIngestionService(repo_root=repo_root)
    
    # First registration succeeds
    ok1, rec1, errs1 = ingestion.register_trial(manifest_file, video_file, ann_file, save=True)
    assert ok1 is True

    # Duplicate registration fails
    ok2, rec2, errs2 = ingestion.register_trial(manifest_file, video_file, ann_file, save=True)
    assert ok2 is False
    assert any("DUPLICATE ERROR" in e for e in errs2)


def test_ingestion_checksum_mismatch_rejection(repo_root, tmp_path):
    """Verifies that GroundTruthIngestionService rejects corrupted or mismatched video SHA-256."""
    manifest_file = tmp_path / "test_manifest.json"
    manifest_data = {
        "manifest_version": "1.0.0",
        "manifest_id": "MANIFEST-TEST",
        "created_at": "2026-09-06T12:00:00Z",
        "cohort_name": "Test Cohort",
        "protocol_version": "1.0.0",
        "description": "Test",
        "is_synthetic_manifest": False,
        "records": []
    }
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f)

    video_file = repo_root / "data" / "ground_truth" / "raw" / "freestyle" / "GT-FREE-001.mp4"
    ann_file = repo_root / "data" / "ground_truth" / "annotations" / "GT-FREE-001.json"

    with open(ann_file, "r", encoding="utf-8") as f:
        ann_data = json.load(f)

    # Tamper with SHA-256
    ann_data["video_sha256"] = "0" * 64
    tampered_ann = tmp_path / "tampered_GT-FREE-001.json"
    with open(tampered_ann, "w", encoding="utf-8") as f:
        json.dump(ann_data, f)

    ingestion = GroundTruthIngestionService(repo_root=repo_root)
    ok, rec, errs = ingestion.register_trial(manifest_file, video_file, tampered_ann, save=False)
    assert ok is False
    assert any("CHECKSUM MISMATCH" in e for e in errs)


def test_ingestion_less_than_3_cycles_rejection(repo_root, tmp_path):
    """Verifies that trials with < 3 clean cycles are demoted from INCLUDED."""
    manifest_file = tmp_path / "test_manifest.json"
    manifest_data = {
        "manifest_version": "1.0.0",
        "manifest_id": "MANIFEST-TEST",
        "created_at": "2026-09-06T12:00:00Z",
        "cohort_name": "Test Cohort",
        "protocol_version": "1.0.0",
        "description": "Test",
        "is_synthetic_manifest": False,
        "records": []
    }
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f)

    video_file = repo_root / "data" / "ground_truth" / "raw" / "freestyle" / "GT-FREE-001.mp4"
    ann_file = repo_root / "data" / "ground_truth" / "annotations" / "GT-FREE-001.json"

    with open(ann_file, "r", encoding="utf-8") as f:
        ann_data = json.load(f)

    # Reduce to only 2 cycles
    ann_data["cycle_annotations"] = ann_data["cycle_annotations"][:2]
    ann_data["sample_id"] = "GT-FREE-FEW-CYCLES"
    ann_data["exclusion_status"] = "INCLUDED"

    few_cycles_ann = tmp_path / "few_cycles.json"
    with open(few_cycles_ann, "w", encoding="utf-8") as f:
        json.dump(ann_data, f)

    ingestion = GroundTruthIngestionService(repo_root=repo_root)
    ok, rec, errs = ingestion.register_trial(manifest_file, video_file, few_cycles_ann, save=True)
    assert ok is True
    # Crucial safety check: status MUST NOT be INCLUDED
    assert rec.inclusion_status == InclusionStatus.EXCLUDED.value
    assert "Incomplete annotation" in rec.exclusion_reason


def test_ingestion_synthetic_sample_rejection(repo_root, tmp_path):
    """Verifies that synthetic fixtures are strictly rejected from official manifests."""
    manifest_file = tmp_path / "test_manifest.json"
    manifest_data = {
        "manifest_version": "1.0.0",
        "manifest_id": "MANIFEST-OFFICIAL",
        "created_at": "2026-09-06T12:00:00Z",
        "cohort_name": "Official Cohort",
        "protocol_version": "1.0.0",
        "description": "Test",
        "is_synthetic_manifest": False,
        "records": []
    }
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f)

    video_file = repo_root / "data" / "ground_truth" / "raw" / "freestyle" / "GT-FREE-001.mp4"
    ann_file = repo_root / "data" / "ground_truth" / "annotations" / "GT-FREE-001.json"

    with open(ann_file, "r", encoding="utf-8") as f:
        ann_data = json.load(f)

    ann_data["is_synthetic_fixture"] = True
    ann_data["sample_id"] = "GT-SYNTH-MOCK"

    synth_ann = tmp_path / "synth_mock.json"
    with open(synth_ann, "w", encoding="utf-8") as f:
        json.dump(ann_data, f)

    ingestion = GroundTruthIngestionService(repo_root=repo_root)
    ok, rec, errs = ingestion.register_trial(manifest_file, video_file, synth_ann, save=False)
    assert ok is False
    assert any("SYNTHETIC ISOLATION VIOLATION" in e for e in errs)


def test_data_leakage_manifest_splits(repo_root):
    """Verifies that DataLeakageValidator validates the official manifest split cleanly."""
    manifest_path = repo_root / "data" / "ground_truth" / "manifests" / "ground_truth_manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    is_valid, errors = DataLeakageValidator.validate_manifest_splits(manifest_data["records"])
    assert is_valid is True
    assert len(errors) == 0
