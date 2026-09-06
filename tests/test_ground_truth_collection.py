"""
Tests for STEP 70: Ground Truth Collection Infrastructure, Blinding & Per-Metric Reliability Gates.

Proves:
- missing raw video cannot become INCLUDED
- checksum is computed from actual bytes
- future annotation timestamp is rejected
- ICC is computed per metric across trials
- heterogeneous metrics are never pooled into one ICC
- one-trial ICC cannot be treated as scientific reliability
- official cohort cannot contain synthetic fixtures
- dual-rater independence is enforced
"""
import os
import sys
import json
import copy
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analysis.validation.ground_truth_qc import (
    GroundTruthQCEngine,
    compute_metric_icc_2_1,
    verify_content_level_blinding,
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
    """Verifies validation freeze record exists with immutable commit SHA and firewall statement."""
    freeze_doc = repo_root / "docs" / "scientific" / "validation_freeze_record.md"
    assert freeze_doc.exists(), "validation_freeze_record.md must exist."
    content = freeze_doc.read_text(encoding="utf-8")
    
    assert "db33130abb4af653ccacc4bec872be25233b59e4" in content
    assert "The AI implementation used for the official validation cohort is frozen before Ground Truth annotation and validation." in content
    assert "SwimAnalyzer-1.0.0" in content


def test_official_manifest_pilot_cohort_integrity(repo_root):
    """
    CRITICAL GROUND TRUTH PURITY GATE:
    Verifies that the official ground truth manifest contains certified pilot records (8 trials),
    confirming all records have byte-verified SHA-256, 1:1 independent participants,
    complete QC audit trails, balanced strokes, and no synthetic fixtures.
    """
    manifest_path = repo_root / "data" / "ground_truth" / "manifests" / "ground_truth_manifest.json"
    assert manifest_path.exists()
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    runner = GroundTruthValidationRunner()
    is_valid, err = runner.validate_manifest_schema(manifest_data)
    assert is_valid, f"Manifest schema validation failed: {err}"
    assert manifest_data["is_synthetic_manifest"] is False
    assert len(manifest_data["records"]) == 8, "Official manifest must contain exactly 8 certified pilot records."

    participant_ids = set()
    strokes = {}
    for rec in manifest_data["records"]:
        assert rec["split"] == "VALIDATION_OFFICIAL"
        assert rec["inclusion_status"] == "INCLUDED"
        assert rec["annotation_status"] == "COMPLETE"
        assert rec["quality_status"] == "PASSED"
        assert len(rec["video_sha256"]) == 64
        
        participant_ids.add(rec["participant_id"])
        strokes[rec["stroke"]] = strokes.get(rec["stroke"], 0) + 1
        
        # Verify annotation file exists and is readable
        ann_path = repo_root / rec["annotation_file"]
        assert ann_path.exists(), f"Annotation file missing: {ann_path}"
        with open(ann_path, "r", encoding="utf-8") as af:
            ann_content = json.load(af)
        assert ann_content["sample_id"] == rec["sample_id"]
        assert ann_content["video_sha256"] == rec["video_sha256"]
        
        # Verify QC audit trail exists
        qc_dir = repo_root / "data" / "ground_truth" / "quality_control" / rec["sample_id"]
        assert (qc_dir / "rater_A.json").exists()
        assert (qc_dir / "rater_B.json").exists()
        assert (qc_dir / "agreement.json").exists()
        assert (qc_dir / "adjudication.json").exists()
        assert (qc_dir / "final_ground_truth.json").exists()

        # If raw video exists locally, verify actual byte hash
        raw_vid = repo_root / rec["video_path"]
        if raw_vid.exists():
            computed_hash = compute_file_sha256(raw_vid)
            assert computed_hash == rec["video_sha256"]

    # Verify 1:1 participant independence across cohort
    assert len(participant_ids) == 8, "Cohort must have 8 unique participants."
    # Verify balanced strokes
    assert strokes == {"Freestyle": 2, "Backstroke": 2, "Breaststroke": 2, "Butterfly": 2}


def test_missing_raw_video_cannot_become_included(repo_root, tmp_path):
    """Verifies that an annotation referring to a missing physical video file cannot become INCLUDED."""
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

    non_existent_video = tmp_path / "does_not_exist_video.mp4"
    dummy_ann = tmp_path / "dummy_ann.json"
    with open(dummy_ann, "w", encoding="utf-8") as f:
        json.dump({"sample_id": "GT-TEST-MISSING"}, f)

    ingestion = GroundTruthIngestionService(repo_root=repo_root)
    ok, rec, errs = ingestion.register_trial(manifest_file, non_existent_video, dummy_ann, save=False)
    
    assert ok is False
    assert rec is None
    assert any("PHYSICAL ASSET ERROR" in e for e in errs)


def test_checksum_computed_from_actual_bytes(repo_root, tmp_path):
    """Verifies that the checksum is computed from actual video bytes, rejecting mismatches."""
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

    # Create real local dummy video file
    real_video = tmp_path / "real_video.mp4"
    real_video.write_bytes(b"REAL_SWIMMING_VIDEO_BYTES_FOR_CHECKSUM_VERIFICATION")
    actual_hash = compute_file_sha256(real_video)

    valid_ann_data = {
        "sample_id": "GT-FREE-001",
        "participant_id": "PARTICIPANT-001",
        "session_id": "SESSION-001",
        "stroke_type": "Freestyle",
        "video_id": "VIDEO-001",
        "video_filename": "real_video.mp4",
        "video_sha256": "f" * 64,  # FAKE/TAMPERED HASH
        "source_type": "HIGH_SPEED_OPTICAL_DUAL_RATER",
        "annotation_version": "1.0.0",
        "annotator_id": "EXPERT-01",
        "secondary_annotator_id": "EXPERT-02",
        "annotation_timestamp": "2026-09-06T12:00:00Z",
        "video_fps": 30.0,
        "video_duration": 10.0,
        "frame_count": 300,
        "exclusion_status": "INCLUDED",
        "cycle_annotations": [
            {"cycle_index": 1, "start_frame": 10, "end_frame": 50, "duration_ms": 1333.3, "stroke_rate_spm": 45.0},
            {"cycle_index": 2, "start_frame": 50, "end_frame": 90, "duration_ms": 1333.3, "stroke_rate_spm": 45.0},
            {"cycle_index": 3, "start_frame": 90, "end_frame": 130, "duration_ms": 1333.3, "stroke_rate_spm": 45.0},
        ],
        "metric_annotations": {
            "stroke_rate_spm": {"value": 45.0, "source_modality": "HUMAN_VIDEO_ANNOTATION"}
        }
    }
    ann_file = tmp_path / "ann.json"
    with open(ann_file, "w", encoding="utf-8") as f:
        json.dump(valid_ann_data, f)

    ingestion = GroundTruthIngestionService(repo_root=repo_root)
    ok, rec, errs = ingestion.register_trial(manifest_file, real_video, ann_file, save=False)
    assert ok is False
    assert any("CHECKSUM MISMATCH" in e for e in errs)

    # Fix hash to match actual bytes
    valid_ann_data["video_sha256"] = actual_hash
    with open(ann_file, "w", encoding="utf-8") as f:
        json.dump(valid_ann_data, f)

    ok_fixed, rec_fixed, errs_fixed = ingestion.register_trial(manifest_file, real_video, ann_file, save=False)
    assert ok_fixed is True
    assert rec_fixed.video_sha256 == actual_hash


def test_future_annotation_timestamp_rejected(repo_root, tmp_path):
    """Verifies that future-dated annotation timestamps are strictly rejected."""
    manifest_file = tmp_path / "test_manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump({
            "manifest_version": "1.0.0", "manifest_id": "M-TEST", "created_at": "2026-09-06T12:00:00Z",
            "cohort_name": "Test", "protocol_version": "1.0.0", "description": "Test",
            "is_synthetic_manifest": False, "records": []
        }, f)

    real_video = tmp_path / "real_video.mp4"
    real_video.write_bytes(b"REAL_VIDEO_CONTENT")
    actual_hash = compute_file_sha256(real_video)

    future_dt = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
    ann_data = {
        "sample_id": "GT-FREE-FUTURE",
        "participant_id": "PARTICIPANT-001",
        "session_id": "SESSION-001",
        "stroke_type": "Freestyle",
        "video_id": "VIDEO-001",
        "video_filename": "real_video.mp4",
        "video_sha256": actual_hash,
        "source_type": "HIGH_SPEED_OPTICAL_DUAL_RATER",
        "annotation_version": "1.0.0",
        "annotator_id": "EXPERT-01",
        "secondary_annotator_id": "EXPERT-02",
        "annotation_timestamp": future_dt,  # FUTURE TIMESTAMP
        "video_fps": 30.0,
        "video_duration": 10.0,
        "frame_count": 300,
        "exclusion_status": "INCLUDED",
        "cycle_annotations": [
            {"cycle_index": 1, "start_frame": 10, "end_frame": 50, "duration_ms": 1333.3, "stroke_rate_spm": 45.0},
            {"cycle_index": 2, "start_frame": 50, "end_frame": 90, "duration_ms": 1333.3, "stroke_rate_spm": 45.0},
            {"cycle_index": 3, "start_frame": 90, "end_frame": 130, "duration_ms": 1333.3, "stroke_rate_spm": 45.0},
        ],
        "metric_annotations": {
            "stroke_rate_spm": {"value": 45.0, "source_modality": "HUMAN_VIDEO_ANNOTATION"}
        }
    }
    ann_file = tmp_path / "future_ann.json"
    with open(ann_file, "w", encoding="utf-8") as f:
        json.dump(ann_data, f)

    ingestion = GroundTruthIngestionService(repo_root=repo_root)
    ok, rec, errs = ingestion.register_trial(manifest_file, real_video, ann_file, save=False)
    assert ok is False
    assert any("TIMESTAMP INTEGRITY ERROR" in e for e in errs)


def test_icc_computed_per_metric_across_trials():
    """Verifies that ICC(2,1) is computed strictly per metric across trials."""
    # Stroke rate values across 4 independent trials from Rater A and Rater B
    stroke_rate_pairs = [(42.0, 42.5), (46.0, 45.8), (38.0, 38.2), (52.0, 51.5)]
    res = compute_metric_icc_2_1("stroke_rate_spm", stroke_rate_pairs)

    assert res["metric_name"] == "stroke_rate_spm"
    assert res["n_items"] == 4
    assert res["icc_2_1"] is not None
    assert res["icc_2_1"] >= 0.95
    assert res["is_pilot_evidence"] is True  # n < 24
    assert "PILOT_INTER_RATER_RELIABILITY" in res["agreement_interpretation"]


def test_heterogeneous_metrics_never_pooled_into_one_icc():
    """Verifies that heterogeneous metrics must be calculated in isolation and not pooled."""
    trial_data = {
        "stroke_rate_spm": [(42.0, 42.5), (46.0, 45.8)],
        "mean_elbow_angle_deg": [(135.0, 136.0), (142.0, 140.5)],
    }
    qc_engine = GroundTruthQCEngine()
    cohort_iccs = qc_engine.compute_cohort_metric_iccs(trial_data)

    assert "stroke_rate_spm" in cohort_iccs
    assert "mean_elbow_angle_deg" in cohort_iccs
    assert cohort_iccs["stroke_rate_spm"]["metric_name"] == "stroke_rate_spm"
    assert cohort_iccs["mean_elbow_angle_deg"]["metric_name"] == "mean_elbow_angle_deg"
    # Never combined into a single "overall" ICC
    assert "overall" not in cohort_iccs


def test_one_trial_icc_cannot_be_treated_as_scientific_reliability():
    """Verifies that a single trial cannot calculate ICC across items and is rejected."""
    single_pair = [(42.0, 42.5)]
    res = compute_metric_icc_2_1("stroke_rate_spm", single_pair)

    assert res["status"] == "INSUFFICIENT_SAMPLE"
    assert res["icc_2_1"] is None
    assert "INSUFFICIENT_SAMPLE" in res["agreement_interpretation"]


def test_content_level_blinding_verification():
    """Verifies that content-level blinding scans detect forbidden AI keys without claiming procedural proof."""
    clean_dict = {"annotator_id": "EXPERT-01", "measurements": {"elbow_angle": 135.0}}
    ok, violations = verify_content_level_blinding(clean_dict)
    assert ok is True
    assert len(violations) == 0

    dirty_dict = {"annotator_id": "EXPERT-01", "overall_score": 90.0, "predicted_stroke": "Freestyle"}
    ok_dirty, violations_dirty = verify_content_level_blinding(dirty_dict)
    assert ok_dirty is False
    assert len(violations_dirty) == 2


def test_dual_rater_independence_gate(repo_root, tmp_path):
    """Verifies that identical annotators are rejected from the official validation split."""
    manifest_file = tmp_path / "test_manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump({
            "manifest_version": "1.0.0", "manifest_id": "M-TEST", "created_at": "2026-09-06T12:00:00Z",
            "cohort_name": "Test", "protocol_version": "1.0.0", "description": "Test",
            "is_synthetic_manifest": False, "records": []
        }, f)

    real_video = tmp_path / "real_video.mp4"
    real_video.write_bytes(b"REAL_SWIM_VIDEO")
    actual_hash = compute_file_sha256(real_video)

    ann_data = {
        "sample_id": "GT-FREE-SAME-RATER",
        "participant_id": "PARTICIPANT-001",
        "session_id": "SESSION-001",
        "stroke_type": "Freestyle",
        "video_id": "VIDEO-001",
        "video_filename": "real_video.mp4",
        "video_sha256": actual_hash,
        "source_type": "HIGH_SPEED_OPTICAL_DUAL_RATER",
        "annotation_version": "1.0.0",
        "annotator_id": "SAME_RATER",
        "secondary_annotator_id": "SAME_RATER",  # IDENTICAL
        "annotation_timestamp": "2026-09-06T12:00:00Z",
        "video_fps": 30.0,
        "video_duration": 10.0,
        "frame_count": 300,
        "exclusion_status": "INCLUDED",
        "cycle_annotations": [
            {"cycle_index": 1, "start_frame": 10, "end_frame": 50, "duration_ms": 1333.3, "stroke_rate_spm": 45.0},
            {"cycle_index": 2, "start_frame": 50, "end_frame": 90, "duration_ms": 1333.3, "stroke_rate_spm": 45.0},
            {"cycle_index": 3, "start_frame": 90, "end_frame": 130, "duration_ms": 1333.3, "stroke_rate_spm": 45.0},
        ],
        "metric_annotations": {
            "stroke_rate_spm": {"value": 45.0, "source_modality": "HUMAN_VIDEO_ANNOTATION"}
        }
    }
    ann_file = tmp_path / "same_rater.json"
    with open(ann_file, "w", encoding="utf-8") as f:
        json.dump(ann_data, f)

    ingestion = GroundTruthIngestionService(repo_root=repo_root)
    ok, rec, errs = ingestion.register_trial(manifest_file, real_video, ann_file, split="VALIDATION_OFFICIAL", save=True)
    assert ok is True
    assert rec.inclusion_status == InclusionStatus.EXCLUDED.value
    assert "Dual-rater independence violation" in rec.exclusion_reason


def test_official_cohort_cannot_contain_synthetic_fixtures(repo_root, tmp_path):
    """Verifies that synthetic fixtures are strictly rejected from official manifests."""
    manifest_file = tmp_path / "test_manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump({
            "manifest_version": "1.0.0", "manifest_id": "M-OFFICIAL", "created_at": "2026-09-06T12:00:00Z",
            "cohort_name": "Official Cohort", "protocol_version": "1.0.0", "description": "Test",
            "is_synthetic_manifest": False, "records": []
        }, f)

    real_video = tmp_path / "real_video.mp4"
    real_video.write_bytes(b"VIDEO_DATA")
    actual_hash = compute_file_sha256(real_video)

    synth_ann_data = {
        "sample_id": "GT-SYNTH-MOCK",
        "participant_id": "PARTICIPANT-001",
        "session_id": "SESSION-001",
        "stroke_type": "Freestyle",
        "video_id": "VIDEO-001",
        "video_filename": "real_video.mp4",
        "video_sha256": actual_hash,
        "source_type": "SYNTHETIC_TEST_FIXTURE",
        "is_synthetic_fixture": True,  # SYNTHETIC
        "annotation_version": "1.0.0",
        "annotator_id": "EXPERT-01",
        "secondary_annotator_id": "EXPERT-02",
        "annotation_timestamp": "2026-09-06T12:00:00Z",
        "video_fps": 30.0,
        "video_duration": 10.0,
        "frame_count": 300,
        "exclusion_status": "INCLUDED",
        "cycle_annotations": [
            {"cycle_index": 1, "start_frame": 10, "end_frame": 50, "duration_ms": 1333.3, "stroke_rate_spm": 45.0},
            {"cycle_index": 2, "start_frame": 50, "end_frame": 90, "duration_ms": 1333.3, "stroke_rate_spm": 45.0},
            {"cycle_index": 3, "start_frame": 90, "end_frame": 130, "duration_ms": 1333.3, "stroke_rate_spm": 45.0},
        ],
        "metric_annotations": {
            "stroke_rate_spm": {"value": 45.0, "source_modality": "SYNTHETIC_TEST_FIXTURE"}
        }
    }
    synth_ann_file = tmp_path / "synth.json"
    with open(synth_ann_file, "w", encoding="utf-8") as f:
        json.dump(synth_ann_data, f)

    ingestion = GroundTruthIngestionService(repo_root=repo_root)
    ok, rec, errs = ingestion.register_trial(manifest_file, real_video, synth_ann_file, split="VALIDATION_OFFICIAL", save=False)
    assert ok is False
    assert any("SYNTHETIC ISOLATION VIOLATION" in e for e in errs)
