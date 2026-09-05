import json
from pathlib import Path

schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "SwimAnalyzer Ground Truth Annotation Schema",
    "description": "Formal schema for validating empirical Ground Truth datasets collected for SwimAnalyzer AI validation",
    "type": "object",
    "required": [
        "schema_version",
        "trial_metadata",
        "annotation_metadata",
        "cycle_ground_truth",
        "aggregate_ground_truth"
    ],
    "properties": {
        "schema_version": {
            "type": "string",
            "enum": ["1.0.0"]
        },
        "trial_metadata": {
            "type": "object",
            "required": [
                "video_file",
                "video_sha256",
                "stroke",
                "swimmer_id",
                "swimmer_sex",
                "swimmer_level",
                "camera_view",
                "camera_position",
                "nominal_fps",
                "actual_fps",
                "resolution",
                "calibration_type"
            ],
            "properties": {
                "video_file": {"type": "string"},
                "video_sha256": {"type": "string"},
                "stroke": {
                    "type": "string",
                    "enum": ["Freestyle", "Backstroke", "Breaststroke", "Butterfly"]
                },
                "swimmer_id": {"type": "string"},
                "swimmer_sex": {"type": "string", "enum": ["Male", "Female"]},
                "swimmer_level": {"type": "string", "enum": ["Elite", "National", "Club", "Recreational"]},
                "camera_view": {"type": "string", "enum": ["Sagittal_Lateral", "Frontal_HeadOn", "Transverse_Overhead", "Diagonal"]},
                "camera_position": {"type": "string", "enum": ["Submerged_Window", "Submerged_Housing", "Poolside_Surface", "Poolside_Elevated"]},
                "nominal_fps": {"type": "number", "minimum": 30.0},
                "actual_fps": {"type": "number", "minimum": 30.0},
                "resolution": {"type": "string"},
                "calibration_type": {"type": "string", "enum": ["Metric_Physical_Pool", "Body_Normalized", "Uncalibrated"]}
            }
        },
        "annotation_metadata": {
            "type": "object",
            "required": [
                "rater_count",
                "rater_ids",
                "measurement_method",
                "inter_rater_agreement"
            ],
            "properties": {
                "rater_count": {"type": "integer", "minimum": 1},
                "rater_ids": {"type": "array", "items": {"type": "string"}},
                "measurement_method": {"type": "string"},
                "inter_rater_agreement": {
                    "type": "object",
                    "properties": {
                        "cohens_kappa": {"type": "number"},
                        "icc_2_1": {"type": "number"},
                        "adjudication_required": {"type": "boolean"},
                        "adjudication_notes": {"type": "string"}
                    }
                }
            }
        },
        "cycle_ground_truth": {
            "type": "array",
            "minItems": 2,
            "items": {
                "type": "object",
                "required": [
                    "cycle_index",
                    "start_frame",
                    "end_frame",
                    "duration_ms",
                    "stroke_rate_spm",
                    "phase_events"
                ],
                "properties": {
                    "cycle_index": {"type": "integer"},
                    "start_frame": {"type": "integer"},
                    "end_frame": {"type": "integer"},
                    "duration_ms": {"type": "number"},
                    "stroke_rate_spm": {"type": "number"},
                    "phase_events": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["phase_name", "transition_frame"],
                            "properties": {
                                "phase_name": {"type": "string"},
                                "transition_frame": {"type": "integer"},
                                "timestamp_ms": {"type": "number"}
                            }
                        }
                    }
                }
            }
        },
        "frame_level_angles": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["frame_index"],
                "properties": {
                    "frame_index": {"type": "integer"},
                    "left_elbow_deg": {"type": "number"},
                    "right_elbow_deg": {"type": "number"},
                    "left_knee_deg": {"type": "number"},
                    "right_knee_deg": {"type": "number"},
                    "left_shoulder_deg": {"type": "number"},
                    "right_shoulder_deg": {"type": "number"},
                    "body_roll_2d_deg": {"type": "number"},
                    "body_roll_3d_imu_deg": {"type": "number"}
                }
            }
        },
        "aggregate_ground_truth": {
            "type": "object",
            "required": [
                "mean_stroke_rate_spm",
                "mean_cycle_duration_ms",
                "completed_cycles_count"
            ],
            "properties": {
                "mean_stroke_rate_spm": {"type": "number"},
                "mean_cycle_duration_ms": {"type": "number"},
                "completed_cycles_count": {"type": "integer"},
                "hand_excursion_proxy_bl": {"type": ["number", "null"]},
                "true_dps_meters": {"type": ["number", "null"]},
                "peak_body_roll_deg": {"type": ["number", "null"]},
                "mean_elbow_angle_deg": {"type": ["number", "null"]},
                "mean_knee_angle_deg": {"type": ["number", "null"]},
                "phase_percentages": {
                    "type": "object",
                    "additionalProperties": {"type": "number"}
                }
            }
        }
    }
}

out_path = Path("data/reference/ground_truth_dataset_schema.json")
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(schema, f, indent=2)

print(f"Created {out_path} successfully.")
