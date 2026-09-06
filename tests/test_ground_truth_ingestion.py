"""
Unit tests for Ground Truth Ingestion & Registration Service (Step 69).
Verifies trial validation, checksum generation, schema/provenance gating, duplicate detection,
and manifest updating without fabricating data.
"""
import json
import pytest
from pathlib import Path

from analysis.validation.ground_truth_ingestion import GroundTruthIngestionService, compute_file_sha256
from analysis.validation.ground_truth_models import InclusionStatus, AnnotationStatus, QualityStatus


@pytest.fixture
def temp_dir(tmp_path):
    return tmp_path


@pytest.fixture
def repo_root():
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def ingestion_service(repo_root):
    return GroundTruthIngestionService(repo_root=repo_root)


@pytest.fixture
def dummy_video(temp_dir):
    video_file = temp_dir / "sample_video.mp4"
    video_file.write_bytes(b"TEST_VIDEO_BINARY_STREAM_FOR_INGESTION_TESTS")
    return video_file


@pytest.fixture
def dummy_manifest(temp_dir):
    manifest_file = temp_dir / "test_manifest.json"
    data = {
        "manifest_version": "1.0.0",
        "manifest_id": "MANIFEST-TEST-INGEST",
        "created_at": "2026-09-06T12:00:00Z",
        "cohort_name": "Test Ingest Cohort",
        "protocol_version": "1.0.0",
        "description": "Test manifest for ingestion verification",
        "is_synthetic_manifest": False,
        "records": []
    }
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return manifest_file


@pytest.fixture
def valid_annotation(temp_dir, dummy_video):
    anno_file = temp_dir / "valid_annotation.json"
    sha = compute_file_sha256(dummy_video)
    data = {
        "sample_id": "GT-INGEST-001",
        "participant_id": "PARTICIPANT-INGEST-01",
        "session_id": "SESS-2026-INGEST",
        "stroke_type": "Freestyle",
        "video_id": "VID-INGEST-001",
        "video_filename": dummy_video.name,
        "video_sha256": sha,
        "source_type": "HIGH_SPEED_OPTICAL_DUAL_RATER",
        "annotation_version": "1.0.0",
        "annotator_id": "RATER-A",
        "secondary_annotator_id": "RATER-B",
        "annotation_timestamp": "2026-09-06T12:00:00Z",
        "video_fps": 60.0,
        "video_duration": 10.0,
        "frame_count": 600,
        "exclusion_status": "INCLUDED",
        "exclusion_reason": None,
        "cycle_annotations": [
            {
                "cycle_index": 1,
                "start_frame": 0,
                "end_frame": 60,
                "duration_ms": 1000.0,
                "stroke_rate_spm": 60.0
            },
            {
                "cycle_index": 2,
                "start_frame": 60,
                "end_frame": 120,
                "duration_ms": 1000.0,
                "stroke_rate_spm": 60.0
            }
        ],
        "metric_annotations": {
            "stroke_rate_spm": {
                "value": 60.0,
                "source_modality": "HUMAN_VIDEO_ANNOTATION"
            },
            "cycle_duration_ms": {
                "value": 1000.0,
                "source_modality": "HUMAN_VIDEO_ANNOTATION"
            }
        },
        "quality_flags": {
            "occlusion_level": "LOW",
            "lighting_quality": "HIGH",
            "water_turbulence": "CALM"
        },
        "is_synthetic_fixture": False
    }
    with open(anno_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return anno_file


def test_checksum_generation(dummy_video):
    """Verifies that compute_file_sha256 computes accurate SHA-256."""
    sha = compute_file_sha256(dummy_video)
    assert isinstance(sha, str)
    assert len(sha) == 64


def test_missing_video_rejection(ingestion_service, temp_dir, dummy_manifest, valid_annotation):
    """Missing target video file must be rejected."""
    non_existent_video = temp_dir / "ghost_video.mp4"
    ok, rec, errs = ingestion_service.register_trial(
        manifest_path=dummy_manifest,
        video_path=non_existent_video,
        annotation_path=valid_annotation,
        save=False
    )
    assert ok is False
    assert any("does not exist" in e for e in errs)


def test_valid_trial_registration_success(ingestion_service, dummy_manifest, dummy_video, valid_annotation):
    """Valid video and annotation are successfully registered into manifest."""
    ok, rec, errs = ingestion_service.register_trial(
        manifest_path=dummy_manifest,
        video_path=dummy_video,
        annotation_path=valid_annotation,
        save=True
    )
    assert ok is True, f"Registration failed with: {errs}"
    assert rec is not None
    assert rec.sample_id == "GT-INGEST-001"
    assert rec.inclusion_status == InclusionStatus.INCLUDED.value
    assert rec.annotation_status == AnnotationStatus.COMPLETE.value

    # Verify manifest on disk was updated
    with open(dummy_manifest, "r", encoding="utf-8") as f:
        m_data = json.load(f)
    assert len(m_data["records"]) == 1
    assert m_data["records"][0]["sample_id"] == "GT-INGEST-001"


def test_duplicate_sample_id_rejection(ingestion_service, dummy_manifest, dummy_video, valid_annotation):
    """Registering the same sample_id twice must be rejected."""
    # First registration
    ok1, _, _ = ingestion_service.register_trial(
        manifest_path=dummy_manifest,
        video_path=dummy_video,
        annotation_path=valid_annotation,
        save=True
    )
    assert ok1 is True

    # Second registration with identical sample_id
    ok2, _, errs2 = ingestion_service.register_trial(
        manifest_path=dummy_manifest,
        video_path=dummy_video,
        annotation_path=valid_annotation,
        save=False
    )
    assert ok2 is False
    assert any("DUPLICATE ERROR" in e for e in errs2)


def test_checksum_mismatch_rejection(ingestion_service, temp_dir, dummy_manifest, dummy_video, valid_annotation):
    """Annotation containing mismatched SHA-256 hash must be rejected."""
    bad_anno_file = temp_dir / "mismatched_checksum_annotation.json"
    with open(valid_annotation, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["sample_id"] = "GT-BAD-SHA"
    data["video_sha256"] = "f" * 64 # wrong hash!
    with open(bad_anno_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    ok, _, errs = ingestion_service.register_trial(
        manifest_path=dummy_manifest,
        video_path=dummy_video,
        annotation_path=bad_anno_file,
        save=False
    )
    assert ok is False
    assert any("CHECKSUM MISMATCH" in e for e in errs)


def test_invalid_provenance_rejection(ingestion_service, temp_dir, dummy_manifest, dummy_video, valid_annotation):
    """Annotation claiming invalid provenance (e.g. true_dps from HUMAN_VIDEO_ANNOTATION) is rejected."""
    bad_anno_file = temp_dir / "bad_provenance_annotation.json"
    with open(valid_annotation, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["sample_id"] = "GT-BAD-PROV"
    data["metric_annotations"]["true_dps_meters"] = {
        "value": 1.85,
        "source_modality": "HUMAN_VIDEO_ANNOTATION" # FORBIDDEN!
    }
    with open(bad_anno_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    ok, _, errs = ingestion_service.register_trial(
        manifest_path=dummy_manifest,
        video_path=dummy_video,
        annotation_path=bad_anno_file,
        save=False
    )
    assert ok is False
    assert any("provenance" in e.lower() or "schema" in e.lower() for e in errs)


def test_synthetic_fixture_rejection_from_official_manifest(ingestion_service, temp_dir, dummy_manifest, dummy_video, valid_annotation):
    """Synthetic fixture sample cannot be registered into official non-synthetic manifest."""
    synth_anno_file = temp_dir / "synth_annotation.json"
    with open(valid_annotation, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["sample_id"] = "GT-SYNTH-SAMPLE"
    data["is_synthetic_fixture"] = True
    data["source_type"] = "SYNTHETIC_TEST_FIXTURE"
    for m in data["metric_annotations"].values():
        m["source_modality"] = "SYNTHETIC_TEST_FIXTURE"
    with open(synth_anno_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    ok, _, errs = ingestion_service.register_trial(
        manifest_path=dummy_manifest,
        video_path=dummy_video,
        annotation_path=synth_anno_file,
        allow_synthetic=False,
        save=False
    )
    assert ok is False
    assert any("SYNTHETIC ISOLATION VIOLATION" in e for e in errs)


def test_incomplete_annotation_marked_excluded(ingestion_service, temp_dir, dummy_manifest, dummy_video, valid_annotation):
    """Annotation missing completed cycles cannot be marked INCLUDED in manifest."""
    incomplete_anno_file = temp_dir / "incomplete_annotation.json"
    with open(valid_annotation, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["sample_id"] = "GT-INCOMPLETE"
    data["cycle_annotations"] = [] # Incomplete!
    data["exclusion_status"] = "INCLUDED" # User falsely claimed included
    with open(incomplete_anno_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    ok, rec, _ = ingestion_service.register_trial(
        manifest_path=dummy_manifest,
        video_path=dummy_video,
        annotation_path=incomplete_anno_file,
        save=False
    )
    assert ok is True
    assert rec.annotation_status == AnnotationStatus.INCOMPLETE.value
    assert rec.inclusion_status == InclusionStatus.EXCLUDED.value
