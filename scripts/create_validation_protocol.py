import json
from pathlib import Path

protocol_data = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "protocol_version": "1.0.0",
    "effective_date": "2026-09-05",
    "pose_engine": "MediaPipe_Tasks_API_Only",
    "empirical_ground_truth_available_in_repo": False,
    "global_policy": {
        "mathematical_correctness_implies_empirical_validation": False,
        "default_acceptance_criterion": "THRESHOLD NOT YET ESTABLISHED",
        "default_repeatability_criterion": "THRESHOLD NOT YET ESTABLISHED",
        "unvalidated_metric_status": "NOT_VALIDATED — INSUFFICIENT GROUND TRUTH"
    },
    "priority_metrics": [
        {
            "id": "stroke_rate",
            "name": "Stroke Rate",
            "implementation_file": "analysis/strategies/freestyle_stroke_analyzer.py",
            "implementation_symbol": "calculate_global_metrics / stroke_rate",
            "mathematical_formula": "SR = 60 * N_cycles / sum(T_cycle)",
            "required_landmarks": [11, 12, 15, 16],
            "coordinate_system": "Temporal frame stamps; normalized 2D image plane [0, 1]",
            "units": "spm",
            "required_fps_assumptions": ">= 30 fps (constant frame rate)",
            "required_camera_conditions": "Lateral sagittal orthogonal view, continuous cycle visibility",
            "applicable_strokes": ["Freestyle", "Backstroke", "Breaststroke", "Butterfly"],
            "expected_measurement_range": {
                "min": 20.0,
                "max": 75.0,
                "unit": "spm",
                "scientific_basis": "Craig & Pendergast (1979); Maglischo (2003); Born et al. (2022)"
            },
            "ground_truth_type_required": "High-speed video (>= 100 fps) frame-stamped event logging by two certified biomechanists",
            "ground_truth_acquisition_protocol": "Frame rater annotation of entry/catch frame with Kappa > 0.90 inter-rater agreement",
            "error_metrics": ["MAE", "RMSE", "MAPE", "Bland-Altman 95% LoA"],
            "acceptance_criterion": "THRESHOLD NOT YET ESTABLISHED",
            "repeatability_criterion": "THRESHOLD NOT YET ESTABLISHED",
            "conditions_marked_not_validated": [
                "Paired ground truth video timing labels are absent",
                "Fewer than 2 complete consecutive stroke cycles detected",
                "Landmark visibility < 0.40 for wrists across >= 20% frames",
                "Swimmer executing turns or underwater pushoff"
            ],
            "status": "NOT_VALIDATED — INSUFFICIENT GROUND TRUTH"
        },
        {
            "id": "avg_cycle_duration",
            "name": "Average Cycle Duration",
            "implementation_file": "analysis/strategies/freestyle_stroke_analyzer.py",
            "implementation_symbol": "avg_cycle_duration_ms",
            "mathematical_formula": "T_mean = (sum(T_cycle) / N_cycles) * 1000",
            "required_landmarks": [11, 12, 15, 16],
            "coordinate_system": "Temporal frame stamps",
            "units": "ms",
            "required_fps_assumptions": ">= 30 fps (constant frame rate)",
            "required_camera_conditions": "Lateral sagittal orthogonal view",
            "applicable_strokes": ["Freestyle", "Backstroke", "Breaststroke", "Butterfly"],
            "expected_measurement_range": {
                "min": 800.0,
                "max": 3000.0,
                "unit": "ms",
                "scientific_basis": "Craig & Pendergast (1979); Seifert et al. (2007)"
            },
            "ground_truth_type_required": "Synchronized high-speed video timecodes or swimming touchpad cycle chronometry",
            "ground_truth_acquisition_protocol": "Frame-accurate rater marking of stroke transition boundaries on reference video",
            "error_metrics": ["MAE", "RMSE", "Pearson_r"],
            "acceptance_criterion": "THRESHOLD NOT YET ESTABLISHED",
            "repeatability_criterion": "THRESHOLD NOT YET ESTABLISHED",
            "conditions_marked_not_validated": [
                "Paired ground truth cycle timecodes absent",
                "Fewer than 2 completed cycles detected",
                "Temporal jitter > 0.10 s due to dropped frames"
            ],
            "status": "NOT_VALIDATED — INSUFFICIENT GROUND TRUTH"
        },
        {
            "id": "stroke_length_dps_proxy",
            "name": "Stroke Length / DPS proxy",
            "implementation_file": "analysis/strategies/freestyle_biomechanics_calculator.py",
            "implementation_symbol": "calculate_global_metrics / stroke_length",
            "mathematical_formula": "SL_proxy = mean(abs(x_wrist(finish) - x_wrist(catch))) [relative_body_normalized]",
            "required_landmarks": [11, 12, 15, 16, 23, 24],
            "coordinate_system": "Normalized image coordinates [0, 1] uncalibrated; metric world coordinates if calibrated",
            "units": "body_lengths or meters",
            "required_fps_assumptions": ">= 30 fps",
            "required_camera_conditions": "Fixed stationary orthogonal camera with calibrated lane markers",
            "applicable_strokes": ["Freestyle", "Backstroke", "Breaststroke", "Butterfly"],
            "expected_measurement_range": {
                "min": 0.80,
                "max": 1.60,
                "unit": "body_lengths",
                "scientific_basis": "Smith et al. (2002); Born et al. (2022)"
            },
            "ground_truth_type_required": "Submerged/aerial calibrated motion capture tracking Center of Mass (COM), or speed-cable displacement transducer",
            "ground_truth_acquisition_protocol": "Whole-body kinematic segment model tracking COM translation across consecutive cycles",
            "error_metrics": ["MAE", "RMSE", "percentage_error"],
            "acceptance_criterion": "THRESHOLD NOT YET ESTABLISHED",
            "repeatability_criterion": "THRESHOLD NOT YET ESTABLISHED",
            "conditions_marked_not_validated": [
                "Absence of metric pool calibration or paired COM ground truth",
                "Camera panning without geometric homography compensation",
                "Presenting hand excursion proxy as true whole-body COM translation"
            ],
            "status": "NOT_VALIDATED — INSUFFICIENT GROUND TRUTH"
        },
        {
            "id": "elbow_angle",
            "name": "Elbow Angle",
            "implementation_file": "analysis/strategies/freestyle_biomechanics_calculator.py",
            "implementation_symbol": "_calculate_joint_angles / calculate_angle",
            "mathematical_formula": "arccos((u . v) / (|u| |v|)) where u = P_sh - P_elb, v = P_wri - P_elb",
            "required_landmarks": [11, 12, 13, 14, 15, 16],
            "coordinate_system": "2D normalized image coordinates [0, 1]^2",
            "units": "degrees",
            "required_fps_assumptions": ">= 30 fps",
            "required_camera_conditions": "True lateral sagittal view (< 15 deg out-of-plane deviation), clean optical interface",
            "applicable_strokes": ["Freestyle", "Backstroke", "Breaststroke", "Butterfly"],
            "expected_measurement_range": {
                "min": 40.0,
                "max": 180.0,
                "unit": "degrees",
                "scientific_basis": "Maglischo (2003); Psycharakis & Sanders (2008)"
            },
            "ground_truth_type_required": "Calibrated underwater multi-camera 3D optoelectronic motion capture or manual frame-by-frame goniometric digitization",
            "ground_truth_acquisition_protocol": "Manual digitization of lateral epicondyle, acromion, and ulnar styloid across 3 repeats",
            "error_metrics": ["MAE", "RMSE", "Bland-Altman 95% LoA", "ICC(2,1)"],
            "acceptance_criterion": "THRESHOLD NOT YET ESTABLISHED",
            "repeatability_criterion": "THRESHOLD NOT YET ESTABLISHED",
            "conditions_marked_not_validated": [
                "Paired 3D mocap or manual goniometric annotations absent",
                "Non-orthogonal camera angle (> 20 deg out-of-plane)",
                "Optical refraction distortion uncorrected",
                "Landmark visibility < 0.50"
            ],
            "status": "NOT_VALIDATED — INSUFFICIENT GROUND TRUTH"
        },
        {
            "id": "knee_angle",
            "name": "Knee Angle",
            "implementation_file": "analysis/strategies/freestyle_biomechanics_calculator.py",
            "implementation_symbol": "_calculate_joint_angles / calculate_angle",
            "mathematical_formula": "arccos((u . v) / (|u| |v|)) where u = P_hip - P_knee, v = P_ank - P_knee",
            "required_landmarks": [23, 24, 25, 26, 27, 28],
            "coordinate_system": "2D normalized image coordinates [0, 1]^2",
            "units": "degrees",
            "required_fps_assumptions": ">= 30 fps",
            "required_camera_conditions": "Lateral underwater sagittal view beneath surface turbulence",
            "applicable_strokes": ["Freestyle", "Backstroke", "Breaststroke", "Butterfly"],
            "expected_measurement_range": {
                "min": 30.0,
                "max": 180.0,
                "unit": "degrees",
                "scientific_basis": "Maglischo (2003)"
            },
            "ground_truth_type_required": "Underwater optoelectronic 3D motion capture or expert manual frame-by-frame digitization",
            "ground_truth_acquisition_protocol": "Multi-camera calibrated underwater tracking of trochanter, femoral epicondyle, and malleolus",
            "error_metrics": ["MAE", "RMSE", "ICC(2,1)"],
            "acceptance_criterion": "THRESHOLD NOT YET ESTABLISHED",
            "repeatability_criterion": "THRESHOLD NOT YET ESTABLISHED",
            "conditions_marked_not_validated": [
                "Absence of paired underwater motion capture or manual labels",
                "Heavy bubble curtain / aeration completely occluding knees or ankles",
                "Landmark visibility < 0.40"
            ],
            "status": "NOT_VALIDATED — INSUFFICIENT GROUND TRUTH"
        },
        {
            "id": "shoulder_angle",
            "name": "Shoulder Angle",
            "implementation_file": "analysis/strategies/freestyle_biomechanics_calculator.py",
            "implementation_symbol": "_calculate_joint_angles / calculate_angle",
            "mathematical_formula": "arccos((u . v) / (|u| |v|)) where u = P_hip - P_sh, v = P_elb - P_sh",
            "required_landmarks": [11, 12, 13, 14, 23, 24],
            "coordinate_system": "2D normalized image coordinates [0, 1]^2",
            "units": "degrees",
            "required_fps_assumptions": ">= 30 fps",
            "required_camera_conditions": "Lateral sagittal view",
            "applicable_strokes": ["Freestyle", "Backstroke", "Breaststroke", "Butterfly"],
            "expected_measurement_range": {
                "min": 30.0,
                "max": 180.0,
                "unit": "degrees",
                "scientific_basis": "Maglischo (2003)"
            },
            "ground_truth_type_required": "Calibrated 3D motion capture or manual frame-by-frame joint digitization",
            "ground_truth_acquisition_protocol": "3D tracking of trunk longitudinal vector vs. humerus segment vector",
            "error_metrics": ["MAE", "RMSE", "Bland-Altman 95% LoA"],
            "acceptance_criterion": "THRESHOLD NOT YET ESTABLISHED",
            "repeatability_criterion": "THRESHOLD NOT YET ESTABLISHED",
            "conditions_marked_not_validated": [
                "Ground truth motion capture data absent",
                "Arm abduction/adduction outside sagittal plane projected as false 2D flexion",
                "Landmark visibility < 0.40"
            ],
            "status": "NOT_VALIDATED — INSUFFICIENT GROUND TRUTH"
        },
        {
            "id": "body_roll",
            "name": "Body Roll",
            "implementation_file": "analysis/strategies/freestyle_biomechanics_calculator.py",
            "implementation_symbol": "body_roll (2D) / body_roll_3d (3D)",
            "mathematical_formula": "2D: abs(arctan2(dy_sh, dx_sh)); 3D: arcsin(n_x / sqrt(n_x^2 + n_y^2)) where n = (s x v_spine) / |s x v_spine|",
            "required_landmarks": [11, 12, 23, 24],
            "coordinate_system": "2D camera sensor plane or 3D camera-relative space with monocular pseudo-depth Z",
            "units": "degrees",
            "required_fps_assumptions": ">= 30 fps",
            "required_camera_conditions": "Frontal (head-on) or longitudinal tracking camera; lateral view requires accurate depth",
            "applicable_strokes": ["Freestyle", "Backstroke"],
            "expected_measurement_range": {
                "min": 25.0,
                "max": 65.0,
                "unit": "degrees",
                "scientific_basis": "Cappaert et al. (1995); Psycharakis & Sanders (2010); Gonjo et al. (2020)"
            },
            "ground_truth_type_required": "Calibrated synchronized waterproof 9-DOF IMUs affixed to thoracic spine/sacrum, or 3D underwater mocap",
            "ground_truth_acquisition_protocol": "Fused orientation quaternion from calibrated IMUs at >= 100 Hz aligned with anatomical axes",
            "error_metrics": ["Peak Roll Angle Error", "Waveform RMSD", "Waveform Cross-Correlation"],
            "acceptance_criterion": "THRESHOLD NOT YET ESTABLISHED",
            "repeatability_criterion": "THRESHOLD NOT YET ESTABLISHED",
            "conditions_marked_not_validated": [
                "Synchronized IMU or 3D mocap data absent",
                "Monocular MediaPipe Z depth scale distortion under water",
                "Swimmer yaw confounded with body roll"
            ],
            "status": "NOT_VALIDATED — INSUFFICIENT GROUND TRUTH"
        },
        {
            "id": "stroke_phase_timing",
            "name": "Stroke Phase Timing",
            "implementation_file": "analysis/strategies/freestyle_stroke_analyzer.py",
            "implementation_symbol": "stroke_phase / time_in_phases",
            "mathematical_formula": "Phase duration sum(dt_f) and percentage of cycle duration (dt_phase / T_cycle) * 100%",
            "required_landmarks": [11, 12, 15, 16, 23, 24],
            "coordinate_system": "Discrete categorical phase state machine over frame sequence",
            "units": "seconds, frames, percentage",
            "required_fps_assumptions": ">= 30 fps (preferably >= 50 fps)",
            "required_camera_conditions": "Lateral sagittal underwater and surface view capturing hand entry, pull-push, and exit",
            "applicable_strokes": ["Freestyle", "Backstroke", "Breaststroke", "Butterfly"],
            "expected_measurement_range": {
                "min": 10.0,
                "max": 60.0,
                "unit": "percent",
                "scientific_basis": "Chollet et al. (2000); Leblanc et al. (2005)"
            },
            "ground_truth_type_required": "Independent frame-by-frame manual phase labeling by at least two certified swimming biomechanists",
            "ground_truth_acquisition_protocol": "Double-blind annotation of phase transitions according to standardized biomechanical definitions (Kappa >= 0.85)",
            "error_metrics": ["Transition Frame Error", "Phase Duration MAE", "Precision", "Recall", "F1-Score at +-3 frames"],
            "acceptance_criterion": "THRESHOLD NOT YET ESTABLISHED",
            "repeatability_criterion": "THRESHOLD NOT YET ESTABLISHED",
            "conditions_marked_not_validated": [
                "Paired manual event ground truth labels absent",
                "Water splash prevents unambiguous identification of transitions",
                "Frame rate < 30 fps"
            ],
            "status": "NOT_VALIDATED — INSUFFICIENT GROUND TRUTH"
        }
    ]
}

target_path = Path("data/reference/scientific_validation_protocol.json")
target_path.parent.mkdir(parents=True, exist_ok=True)
with open(target_path, "w", encoding="utf-8") as f:
    json.dump(protocol_data, f, indent=2)

print(f"Created {target_path} successfully with {len(protocol_data['priority_metrics'])} priority metrics.")
