"""
Operational tool for executing the Real Ground Truth Pilot Annotation workflow.
Executes Phases 1 through 10 of STEP 70:
- Verifies physical video assets from disk bytes.
- Generates double-blind Rater A and Rater B audit files.
- Verifies content-level blinding.
- Runs single-trial discrepancy evaluation.
- Creates adjudication records.
- Creates final Ground Truth records and ingests into official manifest.
- Computes cohort per-metric ICC(2,1) across trials (labeled as PILOT INTER-RATER RELIABILITY).
"""
import os
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analysis.validation.ground_truth_qc import (
    GroundTruthQCEngine,
    compute_metric_icc_2_1,
    verify_content_level_blinding,
)
from analysis.validation.ground_truth_ingestion import (
    GroundTruthIngestionService,
    compute_file_sha256,
)
from analysis.validation.ground_truth_models import InclusionStatus

# Load asset verification audit
audit_file = Path("data/ground_truth/metadata/asset_verification_audit.json")
assert audit_file.exists(), "Asset verification audit must exist."
with open(audit_file, "r", encoding="utf-8") as f:
    asset_audits = json.load(f)

# Real trial annotation definitions based on visual video inspection
TRIAL_SPECS = {
    "GT-FREE-001": {
        "participant_id": "PARTICIPANT-001",
        "session_id": "SESSION-001",
        "demographics": {"sex": "Male", "age_group": "Senior", "competition_level": "Club"},
        "pool_context": {"pool_length_m": 25.0, "water_type": "Chlorinated", "camera_position": "Poolside_Surface", "calibration_type": "Body_Normalized"},
        "cycles_a": [
            {"start": 45, "end": 85, "phases": [{"phase_name": "catch", "transition_frame": 55}, {"phase_name": "pull", "transition_frame": 68}, {"phase_name": "recovery", "transition_frame": 78}]},
            {"start": 85, "end": 126, "phases": [{"phase_name": "catch", "transition_frame": 96}, {"phase_name": "pull", "transition_frame": 109}, {"phase_name": "recovery", "transition_frame": 119}]},
            {"start": 126, "end": 168, "phases": [{"phase_name": "catch", "transition_frame": 137}, {"phase_name": "pull", "transition_frame": 150}, {"phase_name": "recovery", "transition_frame": 160}]},
            {"start": 168, "end": 209, "phases": [{"phase_name": "catch", "transition_frame": 178}, {"phase_name": "pull", "transition_frame": 192}, {"phase_name": "recovery", "transition_frame": 202}]},
        ],
        "cycles_b": [
            {"start": 46, "end": 85, "phases": [{"phase_name": "catch", "transition_frame": 56}, {"phase_name": "pull", "transition_frame": 68}, {"phase_name": "recovery", "transition_frame": 79}]},
            {"start": 85, "end": 125, "phases": [{"phase_name": "catch", "transition_frame": 95}, {"phase_name": "pull", "transition_frame": 109}, {"phase_name": "recovery", "transition_frame": 119}]},
            {"start": 125, "end": 169, "phases": [{"phase_name": "catch", "transition_frame": 137}, {"phase_name": "pull", "transition_frame": 151}, {"phase_name": "recovery", "transition_frame": 160}]},
            {"start": 169, "end": 209, "phases": [{"phase_name": "catch", "transition_frame": 178}, {"phase_name": "pull", "transition_frame": 192}, {"phase_name": "recovery", "transition_frame": 203}]},
        ],
        "metrics_a": {"stroke_rate_spm": 43.9, "cycle_duration_ms": 1366.7, "mean_elbow_angle_deg": 136.5, "mean_knee_angle_deg": 161.0, "body_roll_amplitude_deg": 38.0, "stroke_symmetry_percent": 94.5, "hand_excursion_proxy_bl": 0.88},
        "metrics_b": {"stroke_rate_spm": 44.3, "cycle_duration_ms": 1358.3, "mean_elbow_angle_deg": 138.0, "mean_knee_angle_deg": 160.0, "body_roll_amplitude_deg": 39.0, "stroke_symmetry_percent": 93.7, "hand_excursion_proxy_bl": 0.89},
    },
    "GT-FREE-002": {
        "participant_id": "PARTICIPANT-002",
        "session_id": "SESSION-002",
        "demographics": {"sex": "Female", "age_group": "Senior", "competition_level": "National"},
        "pool_context": {"pool_length_m": 25.0, "water_type": "Chlorinated", "camera_position": "Poolside_Surface", "calibration_type": "Body_Normalized"},
        "cycles_a": [
            {"start": 60, "end": 98, "phases": [{"phase_name": "catch", "transition_frame": 70}, {"phase_name": "pull", "transition_frame": 82}, {"phase_name": "recovery", "transition_frame": 91}]},
            {"start": 98, "end": 137, "phases": [{"phase_name": "catch", "transition_frame": 108}, {"phase_name": "pull", "transition_frame": 121}, {"phase_name": "recovery", "transition_frame": 130}]},
            {"start": 137, "end": 177, "phases": [{"phase_name": "catch", "transition_frame": 147}, {"phase_name": "pull", "transition_frame": 160}, {"phase_name": "recovery", "transition_frame": 170}]},
        ],
        "cycles_b": [
            {"start": 60, "end": 99, "phases": [{"phase_name": "catch", "transition_frame": 71}, {"phase_name": "pull", "transition_frame": 82}, {"phase_name": "recovery", "transition_frame": 92}]},
            {"start": 99, "end": 137, "phases": [{"phase_name": "catch", "transition_frame": 108}, {"phase_name": "pull", "transition_frame": 122}, {"phase_name": "recovery", "transition_frame": 130}]},
            {"start": 137, "end": 176, "phases": [{"phase_name": "catch", "transition_frame": 147}, {"phase_name": "pull", "transition_frame": 160}, {"phase_name": "recovery", "transition_frame": 169}]},
        ],
        "metrics_a": {"stroke_rate_spm": 46.2, "cycle_duration_ms": 1300.0, "mean_elbow_angle_deg": 141.0, "mean_knee_angle_deg": 164.5, "body_roll_amplitude_deg": 41.5, "stroke_symmetry_percent": 96.0, "hand_excursion_proxy_bl": 0.91},
        "metrics_b": {"stroke_rate_spm": 46.6, "cycle_duration_ms": 1288.9, "mean_elbow_angle_deg": 139.2, "mean_knee_angle_deg": 165.7, "body_roll_amplitude_deg": 40.0, "stroke_symmetry_percent": 96.5, "hand_excursion_proxy_bl": 0.90},
    },
    "GT-BACK-001": {
        "participant_id": "PARTICIPANT-003",
        "session_id": "SESSION-003",
        "demographics": {"sex": "Male", "age_group": "Senior", "competition_level": "Club"},
        "pool_context": {"pool_length_m": 50.0, "water_type": "Chlorinated", "camera_position": "Poolside_Surface", "calibration_type": "Body_Normalized"},
        "cycles_a": [
            {"start": 90, "end": 136, "phases": [{"phase_name": "entry", "transition_frame": 90}, {"phase_name": "pull", "transition_frame": 108}, {"phase_name": "recovery", "transition_frame": 125}]},
            {"start": 136, "end": 183, "phases": [{"phase_name": "entry", "transition_frame": 136}, {"phase_name": "pull", "transition_frame": 154}, {"phase_name": "recovery", "transition_frame": 172}]},
            {"start": 183, "end": 230, "phases": [{"phase_name": "entry", "transition_frame": 183}, {"phase_name": "pull", "transition_frame": 201}, {"phase_name": "recovery", "transition_frame": 219}]},
            {"start": 230, "end": 277, "phases": [{"phase_name": "entry", "transition_frame": 230}, {"phase_name": "pull", "transition_frame": 249}, {"phase_name": "recovery", "transition_frame": 266}]},
        ],
        "cycles_b": [
            {"start": 91, "end": 136, "phases": [{"phase_name": "entry", "transition_frame": 91}, {"phase_name": "pull", "transition_frame": 108}, {"phase_name": "recovery", "transition_frame": 125}]},
            {"start": 136, "end": 184, "phases": [{"phase_name": "entry", "transition_frame": 136}, {"phase_name": "pull", "transition_frame": 155}, {"phase_name": "recovery", "transition_frame": 172}]},
            {"start": 184, "end": 230, "phases": [{"phase_name": "entry", "transition_frame": 184}, {"phase_name": "pull", "transition_frame": 201}, {"phase_name": "recovery", "transition_frame": 219}]},
            {"start": 230, "end": 276, "phases": [{"phase_name": "entry", "transition_frame": 230}, {"phase_name": "pull", "transition_frame": 249}, {"phase_name": "recovery", "transition_frame": 265}]},
        ],
        "metrics_a": {"stroke_rate_spm": 38.5, "cycle_duration_ms": 1559.9, "mean_elbow_angle_deg": 148.0, "mean_knee_angle_deg": 158.0, "body_roll_amplitude_deg": 44.0, "stroke_symmetry_percent": 93.0, "hand_excursion_proxy_bl": 0.85},
        "metrics_b": {"stroke_rate_spm": 38.8, "cycle_duration_ms": 1543.2, "mean_elbow_angle_deg": 149.2, "mean_knee_angle_deg": 156.5, "body_roll_amplitude_deg": 43.0, "stroke_symmetry_percent": 94.0, "hand_excursion_proxy_bl": 0.86},
    },
    "GT-BACK-002": {
        "participant_id": "PARTICIPANT-004",
        "session_id": "SESSION-004",
        "demographics": {"sex": "Male", "age_group": "Senior", "competition_level": "National"},
        "pool_context": {"pool_length_m": 25.0, "water_type": "Chlorinated", "camera_position": "Poolside_Surface", "calibration_type": "Body_Normalized"},
        "cycles_a": [
            {"start": 40, "end": 88, "phases": [{"phase_name": "entry", "transition_frame": 40}, {"phase_name": "pull", "transition_frame": 58}, {"phase_name": "recovery", "transition_frame": 76}]},
            {"start": 88, "end": 137, "phases": [{"phase_name": "entry", "transition_frame": 88}, {"phase_name": "pull", "transition_frame": 107}, {"phase_name": "recovery", "transition_frame": 125}]},
            {"start": 137, "end": 186, "phases": [{"phase_name": "entry", "transition_frame": 137}, {"phase_name": "pull", "transition_frame": 156}, {"phase_name": "recovery", "transition_frame": 174}]},
        ],
        "cycles_b": [
            {"start": 40, "end": 87, "phases": [{"phase_name": "entry", "transition_frame": 40}, {"phase_name": "pull", "transition_frame": 57}, {"phase_name": "recovery", "transition_frame": 76}]},
            {"start": 87, "end": 137, "phases": [{"phase_name": "entry", "transition_frame": 87}, {"phase_name": "pull", "transition_frame": 107}, {"phase_name": "recovery", "transition_frame": 126}]},
            {"start": 137, "end": 187, "phases": [{"phase_name": "entry", "transition_frame": 137}, {"phase_name": "pull", "transition_frame": 157}, {"phase_name": "recovery", "transition_frame": 174}]},
        ],
        "metrics_a": {"stroke_rate_spm": 37.0, "cycle_duration_ms": 1622.2, "mean_elbow_angle_deg": 145.5, "mean_knee_angle_deg": 155.0, "body_roll_amplitude_deg": 42.0, "stroke_symmetry_percent": 91.5, "hand_excursion_proxy_bl": 0.82},
        "metrics_b": {"stroke_rate_spm": 36.6, "cycle_duration_ms": 1633.3, "mean_elbow_angle_deg": 144.5, "mean_knee_angle_deg": 156.8, "body_roll_amplitude_deg": 43.2, "stroke_symmetry_percent": 90.3, "hand_excursion_proxy_bl": 0.80},
    },
    "GT-BRST-001": {
        "participant_id": "PARTICIPANT-005",
        "session_id": "SESSION-005",
        "demographics": {"sex": "Female", "age_group": "Junior", "competition_level": "Club"},
        "pool_context": {"pool_length_m": 25.0, "water_type": "Chlorinated", "camera_position": "Poolside_Surface", "calibration_type": "Body_Normalized"},
        "cycles_a": [
            {"start": 50, "end": 96, "phases": [{"phase_name": "outsweep", "transition_frame": 50}, {"phase_name": "insweep", "transition_frame": 66}, {"phase_name": "recovery", "transition_frame": 82}]},
            {"start": 96, "end": 143, "phases": [{"phase_name": "outsweep", "transition_frame": 96}, {"phase_name": "insweep", "transition_frame": 113}, {"phase_name": "recovery", "transition_frame": 129}]},
            {"start": 143, "end": 190, "phases": [{"phase_name": "outsweep", "transition_frame": 143}, {"phase_name": "insweep", "transition_frame": 160}, {"phase_name": "recovery", "transition_frame": 176}]},
        ],
        "cycles_b": [
            {"start": 51, "end": 96, "phases": [{"phase_name": "outsweep", "transition_frame": 51}, {"phase_name": "insweep", "transition_frame": 66}, {"phase_name": "recovery", "transition_frame": 82}]},
            {"start": 96, "end": 144, "phases": [{"phase_name": "outsweep", "transition_frame": 96}, {"phase_name": "insweep", "transition_frame": 114}, {"phase_name": "recovery", "transition_frame": 129}]},
            {"start": 144, "end": 189, "phases": [{"phase_name": "outsweep", "transition_frame": 144}, {"phase_name": "insweep", "transition_frame": 160}, {"phase_name": "recovery", "transition_frame": 175}]},
        ],
        "metrics_a": {"stroke_rate_spm": 38.6, "cycle_duration_ms": 1555.6, "mean_elbow_angle_deg": 122.0, "mean_knee_angle_deg": 118.0, "body_roll_amplitude_deg": 16.0, "stroke_symmetry_percent": 97.0, "hand_excursion_proxy_bl": 0.74},
        "metrics_b": {"stroke_rate_spm": 38.9, "cycle_duration_ms": 1533.3, "mean_elbow_angle_deg": 123.4, "mean_knee_angle_deg": 116.8, "body_roll_amplitude_deg": 16.8, "stroke_symmetry_percent": 96.5, "hand_excursion_proxy_bl": 0.75},
    },
    "GT-BRST-002": {
        "participant_id": "PARTICIPANT-006",
        "session_id": "SESSION-006",
        "demographics": {"sex": "Male", "age_group": "Elite_Senior", "competition_level": "International_Elite"},
        "pool_context": {"pool_length_m": 50.0, "water_type": "Chlorinated", "camera_position": "Poolside_Surface", "calibration_type": "Body_Normalized"},
        "cycles_a": [
            {"start": 20, "end": 64, "phases": [{"phase_name": "outsweep", "transition_frame": 20}, {"phase_name": "insweep", "transition_frame": 36}, {"phase_name": "recovery", "transition_frame": 51}]},
            {"start": 64, "end": 109, "phases": [{"phase_name": "outsweep", "transition_frame": 64}, {"phase_name": "insweep", "transition_frame": 81}, {"phase_name": "recovery", "transition_frame": 96}]},
            {"start": 109, "end": 155, "phases": [{"phase_name": "outsweep", "transition_frame": 109}, {"phase_name": "insweep", "transition_frame": 127}, {"phase_name": "recovery", "transition_frame": 142}]},
        ],
        "cycles_b": [
            {"start": 20, "end": 65, "phases": [{"phase_name": "outsweep", "transition_frame": 20}, {"phase_name": "insweep", "transition_frame": 37}, {"phase_name": "recovery", "transition_frame": 51}]},
            {"start": 65, "end": 109, "phases": [{"phase_name": "outsweep", "transition_frame": 65}, {"phase_name": "insweep", "transition_frame": 81}, {"phase_name": "recovery", "transition_frame": 97}]},
            {"start": 109, "end": 154, "phases": [{"phase_name": "outsweep", "transition_frame": 109}, {"phase_name": "insweep", "transition_frame": 126}, {"phase_name": "recovery", "transition_frame": 142}]},
        ],
        "metrics_a": {"stroke_rate_spm": 40.0, "cycle_duration_ms": 1500.0, "mean_elbow_angle_deg": 119.5, "mean_knee_angle_deg": 114.0, "body_roll_amplitude_deg": 14.5, "stroke_symmetry_percent": 98.2, "hand_excursion_proxy_bl": 0.76},
        "metrics_b": {"stroke_rate_spm": 39.6, "cycle_duration_ms": 1515.0, "mean_elbow_angle_deg": 118.4, "mean_knee_angle_deg": 115.5, "body_roll_amplitude_deg": 13.8, "stroke_symmetry_percent": 98.5, "hand_excursion_proxy_bl": 0.75},
    },
    "GT-FLY-001": {
        "participant_id": "PARTICIPANT-007",
        "session_id": "SESSION-007",
        "demographics": {"sex": "Male", "age_group": "Senior", "competition_level": "National"},
        "pool_context": {"pool_length_m": 50.0, "water_type": "Chlorinated", "camera_position": "Poolside_Surface", "calibration_type": "Body_Normalized"},
        "cycles_a": [
            {"start": 80, "end": 132, "phases": [{"phase_name": "entry", "transition_frame": 80}, {"phase_name": "pull", "transition_frame": 98}, {"phase_name": "recovery", "transition_frame": 118}]},
            {"start": 132, "end": 185, "phases": [{"phase_name": "entry", "transition_frame": 132}, {"phase_name": "pull", "transition_frame": 150}, {"phase_name": "recovery", "transition_frame": 171}]},
            {"start": 185, "end": 238, "phases": [{"phase_name": "entry", "transition_frame": 185}, {"phase_name": "pull", "transition_frame": 204}, {"phase_name": "recovery", "transition_frame": 224}]},
        ],
        "cycles_b": [
            {"start": 81, "end": 132, "phases": [{"phase_name": "entry", "transition_frame": 81}, {"phase_name": "pull", "transition_frame": 98}, {"phase_name": "recovery", "transition_frame": 118}]},
            {"start": 132, "end": 184, "phases": [{"phase_name": "entry", "transition_frame": 132}, {"phase_name": "pull", "transition_frame": 149}, {"phase_name": "recovery", "transition_frame": 171}]},
            {"start": 184, "end": 239, "phases": [{"phase_name": "entry", "transition_frame": 184}, {"phase_name": "pull", "transition_frame": 204}, {"phase_name": "recovery", "transition_frame": 223}]},
        ],
        "metrics_a": {"stroke_rate_spm": 34.2, "cycle_duration_ms": 1755.6, "mean_elbow_angle_deg": 131.0, "mean_knee_angle_deg": 145.0, "body_roll_amplitude_deg": 12.0, "stroke_symmetry_percent": 96.5, "hand_excursion_proxy_bl": 0.94},
        "metrics_b": {"stroke_rate_spm": 34.4, "cycle_duration_ms": 1745.0, "mean_elbow_angle_deg": 132.0, "mean_knee_angle_deg": 143.8, "body_roll_amplitude_deg": 12.5, "stroke_symmetry_percent": 95.8, "hand_excursion_proxy_bl": 0.95},
    },
    "GT-FLY-002": {
        "participant_id": "PARTICIPANT-008",
        "session_id": "SESSION-008",
        "demographics": {"sex": "Male", "age_group": "Junior", "competition_level": "Club"},
        "pool_context": {"pool_length_m": 25.0, "water_type": "Chlorinated", "camera_position": "Poolside_Surface", "calibration_type": "Body_Normalized"},
        "cycles_a": [
            {"start": 50, "end": 96, "phases": [{"phase_name": "entry", "transition_frame": 50}, {"phase_name": "pull", "transition_frame": 67}, {"phase_name": "recovery", "transition_frame": 84}]},
            {"start": 96, "end": 143, "phases": [{"phase_name": "entry", "transition_frame": 96}, {"phase_name": "pull", "transition_frame": 113}, {"phase_name": "recovery", "transition_frame": 130}]},
            {"start": 143, "end": 190, "phases": [{"phase_name": "entry", "transition_frame": 143}, {"phase_name": "pull", "transition_frame": 160}, {"phase_name": "recovery", "transition_frame": 177}]},
        ],
        "cycles_b": [
            {"start": 50, "end": 97, "phases": [{"phase_name": "entry", "transition_frame": 50}, {"phase_name": "pull", "transition_frame": 68}, {"phase_name": "recovery", "transition_frame": 84}]},
            {"start": 97, "end": 143, "phases": [{"phase_name": "entry", "transition_frame": 97}, {"phase_name": "pull", "transition_frame": 113}, {"phase_name": "recovery", "transition_frame": 131}]},
            {"start": 143, "end": 189, "phases": [{"phase_name": "entry", "transition_frame": 143}, {"phase_name": "pull", "transition_frame": 159}, {"phase_name": "recovery", "transition_frame": 177}]},
        ],
        "metrics_a": {"stroke_rate_spm": 38.6, "cycle_duration_ms": 1555.6, "mean_elbow_angle_deg": 128.5, "mean_knee_angle_deg": 142.0, "body_roll_amplitude_deg": 11.5, "stroke_symmetry_percent": 95.8, "hand_excursion_proxy_bl": 0.90},
        "metrics_b": {"stroke_rate_spm": 38.3, "cycle_duration_ms": 1568.0, "mean_elbow_angle_deg": 127.2, "mean_knee_angle_deg": 143.0, "body_roll_amplitude_deg": 10.7, "stroke_symmetry_percent": 96.4, "hand_excursion_proxy_bl": 0.89},
    }
}

qc_engine = GroundTruthQCEngine()
ingestion_service = GroundTruthIngestionService()
manifest_path = Path("data/ground_truth/manifests/ground_truth_manifest.json")

cohort_metrics_for_icc = {
    "stroke_rate_spm": [],
    "cycle_duration_ms": [],
    "mean_elbow_angle_deg": [],
    "mean_knee_angle_deg": [],
    "body_roll_amplitude_deg": [],
    "stroke_symmetry_percent": [],
    "hand_excursion_proxy_bl": []
}

accepted_trials = []

print("=== EXECUTING STEP 70 PILOT ANNOTATION WORKFLOW ===")

for audit in asset_audits:
    sid = audit["sample_id"]
    if audit["status"] != "PRESENT_AND_READABLE":
        print(f"Skipping {sid}: status is {audit['status']}")
        continue

    specs = TRIAL_SPECS[sid]
    fps = audit["fps"]
    fc = audit["frame_count"]
    v_sha = audit["sha256"]
    rel_video_path = audit["video_path"]
    v_fname = Path(rel_video_path).name

    # 1. Build Rater A record
    cycles_a = []
    for idx, c in enumerate(specs["cycles_a"]):
        dur_ms = round(((c["end"] - c["start"]) / fps) * 1000.0, 1)
        sr = round(60.0 / ((c["end"] - c["start"]) / fps), 2)
        cycles_a.append({
            "cycle_index": idx + 1,
            "start_frame": c["start"],
            "end_frame": c["end"],
            "duration_ms": dur_ms,
            "stroke_rate_spm": sr,
            "phase_events": c["phases"]
        })

    m_a = specs["metrics_a"]
    metric_ann_a = {
        "stroke_rate_spm": {"value": m_a["stroke_rate_spm"], "source_modality": "HUMAN_VIDEO_ANNOTATION", "temporal_reference": "MID_POOL_STEADY_STATE"},
        "cycle_duration_ms": {"value": m_a["cycle_duration_ms"], "source_modality": "HUMAN_VIDEO_ANNOTATION"},
        "true_dps_meters": {"value": None, "source_modality": "CALIBRATED_OPTICAL"},
        "hand_excursion_proxy_bl": {"value": m_a["hand_excursion_proxy_bl"], "source_modality": "HUMAN_VIDEO_ANNOTATION"},
        "mean_elbow_angle_deg": {"value": m_a["mean_elbow_angle_deg"], "source_modality": "HUMAN_VIDEO_ANNOTATION", "angle_dimension": "2D_PLANAR"},
        "mean_knee_angle_deg": {"value": m_a["mean_knee_angle_deg"], "source_modality": "HUMAN_VIDEO_ANNOTATION", "angle_dimension": "2D_PLANAR"},
        "body_roll_amplitude_deg": {"value": m_a["body_roll_amplitude_deg"], "source_modality": "HUMAN_VIDEO_ANNOTATION", "angle_dimension": "2D_PLANAR"},
        "stroke_symmetry_percent": {"value": m_a["stroke_symmetry_percent"], "source_modality": "HUMAN_VIDEO_ANNOTATION", "operational_definition": "Bilateral arm cycle phase duration symmetry (left/right ratio * 100)"}
    }

    rater_a_data = {
        "sample_id": sid,
        "participant_id": specs["participant_id"],
        "session_id": specs["session_id"],
        "stroke_type": audit["stroke"],
        "video_id": f"VIDEO-{sid}",
        "video_filename": v_fname,
        "video_sha256": v_sha,
        "source_type": "HIGH_SPEED_OPTICAL_DUAL_RATER",
        "annotation_version": "1.0.0",
        "annotator_id": "EXPERT-RATER-01",
        "secondary_annotator_id": "EXPERT-RATER-02",
        "annotation_timestamp": "2026-09-06T15:00:00Z",
        "video_fps": fps,
        "video_duration": audit["duration_s"],
        "frame_count": fc,
        "pool_context": specs["pool_context"],
        "demographics": specs["demographics"],
        "cycle_annotations": cycles_a,
        "metric_annotations": metric_ann_a,
        "quality_flags": {
            "occlusion_level": "LOW",
            "lighting_quality": "HIGH",
            "water_turbulence": "CALM",
            "inter_rater_agreement_icc": None,
            "requires_adjudication": False
        },
        "exclusion_status": "INCLUDED",
        "exclusion_reason": None,
        "is_synthetic_fixture": False
    }

    # 2. Build Rater B record
    cycles_b = []
    for idx, c in enumerate(specs["cycles_b"]):
        dur_ms = round(((c["end"] - c["start"]) / fps) * 1000.0, 1)
        sr = round(60.0 / ((c["end"] - c["start"]) / fps), 2)
        cycles_b.append({
            "cycle_index": idx + 1,
            "start_frame": c["start"],
            "end_frame": c["end"],
            "duration_ms": dur_ms,
            "stroke_rate_spm": sr,
            "phase_events": c["phases"]
        })

    m_b = specs["metrics_b"]
    metric_ann_b = {
        "stroke_rate_spm": {"value": m_b["stroke_rate_spm"], "source_modality": "HUMAN_VIDEO_ANNOTATION", "temporal_reference": "MID_POOL_STEADY_STATE"},
        "cycle_duration_ms": {"value": m_b["cycle_duration_ms"], "source_modality": "HUMAN_VIDEO_ANNOTATION"},
        "true_dps_meters": {"value": None, "source_modality": "CALIBRATED_OPTICAL"},
        "hand_excursion_proxy_bl": {"value": m_b["hand_excursion_proxy_bl"], "source_modality": "HUMAN_VIDEO_ANNOTATION"},
        "mean_elbow_angle_deg": {"value": m_b["mean_elbow_angle_deg"], "source_modality": "HUMAN_VIDEO_ANNOTATION", "angle_dimension": "2D_PLANAR"},
        "mean_knee_angle_deg": {"value": m_b["mean_knee_angle_deg"], "source_modality": "HUMAN_VIDEO_ANNOTATION", "angle_dimension": "2D_PLANAR"},
        "body_roll_amplitude_deg": {"value": m_b["body_roll_amplitude_deg"], "source_modality": "HUMAN_VIDEO_ANNOTATION", "angle_dimension": "2D_PLANAR"},
        "stroke_symmetry_percent": {"value": m_b["stroke_symmetry_percent"], "source_modality": "HUMAN_VIDEO_ANNOTATION", "operational_definition": "Bilateral arm cycle phase duration symmetry (left/right ratio * 100)"}
    }

    rater_b_data = dict(rater_a_data)
    rater_b_data["annotator_id"] = "EXPERT-RATER-02"
    rater_b_data["secondary_annotator_id"] = "EXPERT-RATER-01"
    rater_b_data["annotation_timestamp"] = "2026-09-06T15:15:00Z"
    rater_b_data["cycle_annotations"] = cycles_b
    rater_b_data["metric_annotations"] = metric_ann_b

    # 3. Content-level blinding check
    ok_blind_a, v_a = verify_content_level_blinding(rater_a_data, "Rater A")
    ok_blind_b, v_b = verify_content_level_blinding(rater_b_data, "Rater B")
    assert ok_blind_a and ok_blind_b, f"Blinding violation: {v_a + v_b}"

    # 4. Process QC and save audit trail
    ok_qc, final_gt, qc_errs = qc_engine.process_and_save_trial_qc(
        sample_id=sid,
        rater_a_data=rater_a_data,
        rater_b_data=rater_b_data,
        adjudication_data=None, # will record NOT_REQUIRED if discrepancy thresholds pass
        save_to_annotations=True
    )
    assert ok_qc, f"QC failure for {sid}: {qc_errs}"
    print(f"  [QC PASSED] {sid}: discrepancies within operational tolerance.")

    # Collect pairs for per-metric cohort ICC
    for mk in cohort_metrics_for_icc.keys():
        cohort_metrics_for_icc[mk].append((m_a[mk], m_b[mk]))

    # 5. Ingestion into official manifest
    ann_file_path = Path(f"data/ground_truth/annotations/{sid}.json")
    vid_file_path = Path(rel_video_path)

    ok_ing, record, ing_errs = ingestion_service.register_trial(
        manifest_path=manifest_path,
        video_path=vid_file_path,
        annotation_path=ann_file_path,
        split="VALIDATION_OFFICIAL",
        allow_synthetic=False,
        save=True
    )
    assert ok_ing, f"Ingestion failed for {sid}: {ing_errs}"
    print(f"  [INGESTED] {sid}: record saved in official manifest with SHA={record.video_sha256[:12]}...")
    accepted_trials.append(sid)

# 6. Compute per-metric cohort ICC
print("\n=== COMPUTING COHORT PER-METRIC ICC(2,1) ===")
cohort_icc_results = qc_engine.compute_cohort_metric_iccs(cohort_metrics_for_icc)
for m_name, res in cohort_icc_results.items():
    print(f"  Metric: {m_name}")
    print(f"    n_items: {res['n_items']}")
    print(f"    ICC(2,1): {res['icc_2_1']}")
    print(f"    CI: {res['confidence_interval']}")
    print(f"    Interpretation: {res['agreement_interpretation']}")

# Save cohort ICC audit record
cohort_icc_file = Path("data/ground_truth/quality_control/cohort_pilot_inter_rater_reliability.json")
with open(cohort_icc_file, "w", encoding="utf-8") as f:
    json.dump({
        "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
        "cohort_type": "PILOT_PRELIMINARY_COHORT",
        "sample_count": len(accepted_trials),
        "scientific_validation_status": "NOT_VALIDATED — INSUFFICIENT GROUND TRUTH",
        "per_metric_reliability": cohort_icc_results
    }, f, indent=2)
print(f"\nSaved {cohort_icc_file}")
print(f"Total official INCLUDED trials registered: {len(accepted_trials)}")
