"""
Focused Scientific Baseline Tests for SwimAnalyzer AI Biomechanics Engine.
Step 64: Biomechanics Metric Audit.
"""
import pytest
import numpy as np
from pathlib import Path
import json

from analysis.strategies.freestyle_biomechanics_calculator import FreestyleBiomechanicsCalculator
from analysis.strategies.backstroke_biomechanics_calculator import BackstrokeBiomechanicsCalculator
from analysis.strategies.breaststroke_biomechanics_calculator import BreaststrokeBiomechanicsCalculator
from analysis.strategies.butterfly_biomechanics_calculator import ButterflyBiomechanicsCalculator
from models.data_models import FrameData, JointAngles, ValidatedMetric
from analysis.calibration_engine import RelativeCalibration, PhysicalPoolCalibration, UncalibratedEngine

class MockPoint:
    def __init__(self, x, y, z=0.0, visibility=1.0):
        self.x = x
        self.y = y
        self.z = z
        self.visibility = visibility


def test_freestyle_vector_angle_mathematics():
    """Verify 2D vector interior angle formula on known geometric ground truths."""
    calc = FreestyleBiomechanicsCalculator
    
    # Right angle (90 deg)
    p_a = MockPoint(0.0, 1.0)
    p_b = MockPoint(0.0, 0.0)
    p_c = MockPoint(1.0, 0.0)
    assert abs(calc.calculate_angle(p_a, p_b, p_c) - 90.0) < 1e-4

    # Straight line (180 deg)
    p_a = MockPoint(-1.0, 0.0)
    p_b = MockPoint(0.0, 0.0)
    p_c = MockPoint(1.0, 0.0)
    assert abs(calc.calculate_angle(p_a, p_b, p_c) - 180.0) < 1e-4

    # Acute 45 deg
    p_a = MockPoint(1.0, 1.0)
    p_b = MockPoint(0.0, 0.0)
    p_c = MockPoint(1.0, 0.0)
    assert abs(calc.calculate_angle(p_a, p_b, p_c) - 45.0) < 1e-4

    # Obtuse 135 deg
    p_a = MockPoint(-1.0, 1.0)
    p_b = MockPoint(0.0, 0.0)
    p_c = MockPoint(1.0, 0.0)
    assert abs(calc.calculate_angle(p_a, p_b, p_c) - 135.0) < 1e-4


def test_3d_spatial_metrics_vector_integrity():
    """Verify 3D cross-product body roll and dot-product core torsion calculations."""
    calc = FreestyleBiomechanicsCalculator
    angles = JointAngles()
    
    # Create 33 dummy landmarks with known shoulder and hip vectors
    landmarks = [MockPoint(0.5, 0.5, 0.0) for _ in range(33)]
    
    # Shoulders parallel to X-axis: Left at (0.4, 0.3, 0.0), Right at (0.6, 0.3, 0.0)
    landmarks[11] = MockPoint(0.4, 0.3, 0.0)
    landmarks[12] = MockPoint(0.6, 0.3, 0.0)
    
    # Hips parallel to X-axis: Left at (0.4, 0.6, 0.0), Right at (0.6, 0.6, 0.0)
    landmarks[23] = MockPoint(0.4, 0.6, 0.0)
    landmarks[24] = MockPoint(0.6, 0.6, 0.0)

    # Wrists
    landmarks[15] = MockPoint(0.4, 0.4, -0.1) # Left wrist deeper (Z = -0.1)
    landmarks[16] = MockPoint(0.6, 0.4, 0.1)  # Right wrist shallower (Z = +0.1)

    calc._calculate_3d_metrics(landmarks, angles)
    
    assert angles.body_roll_3d is not None
    assert angles.body_roll_3d.valid is True
    assert angles.body_roll_3d.measurement_domain == "pose_relative_3d"
    # Perfectly flat shoulders and hips relative to vertical -> 0 deg roll
    assert angles.body_roll_3d.value == 0.0

    # Parallel shoulder and hip vectors -> 0 deg core torsion
    assert angles.core_torsion_3d is not None
    assert angles.core_torsion_3d.valid is True
    assert angles.core_torsion_3d.value == 0.0

    # Hand depth offsets
    assert angles.hand_depth_left_3d is not None
    assert angles.hand_depth_left_3d.value == -0.1
    assert angles.hand_depth_right_3d is not None
    assert angles.hand_depth_right_3d.value == 0.1


def test_stroke_rate_cycle_gating():
    """Verify stroke rate returns unavailable / None when 0 complete cycles exist."""
    calc = FreestyleBiomechanicsCalculator
    
    # 30 frames with no recovery-entry cycle
    frames = [FrameData(frame_index=i, timestamp_ms=i*33, raw_landmarks=[], is_valid=True, stroke_phase="Pull") for i in range(30)]
    metric = calc._calculate_stroke_rate(frames, effective_fps=30.0)
    
    assert metric.valid is False
    assert metric.value is None
    assert metric.status == "unavailable"


def test_breaststroke_glide_ratio_and_knee_bend():
    """Verify breaststroke glide ratio and maximum knee bend metrics."""
    calc = BreaststrokeBiomechanicsCalculator
    
    frames = []
    for i in range(100):
        phase = "Glide" if i < 30 else "Outsweep"
        ja = JointAngles()
        # Set knee angle: 110 deg (bend = 180 - 110 = 70 deg)
        ja.right_knee = ValidatedMetric(value=110.0, valid=True)
        frames.append(FrameData(frame_index=i, timestamp_ms=i*33, raw_landmarks=[], is_valid=True, stroke_phase=phase, angles=ja))
        
    metrics = calc.calculate_global_metrics(frames, effective_fps=30.0)
    
    # Glide ratio should be 30 / 100 = 0.30
    assert "glide_ratio" in metrics
    assert metrics["glide_ratio"].valid is True
    assert abs(metrics["glide_ratio"].value - 0.30) < 1e-4

    # Max knee bend should be 70 deg
    assert "max_knee_bend_deg" in metrics
    assert metrics["max_knee_bend_deg"].valid is True
    assert abs(metrics["max_knee_bend_deg"].value - 70.0) < 1e-4


def test_butterfly_undulation_and_wrist_asymmetry():
    """Verify butterfly hip undulation amplitude and wrist asymmetry."""
    calc = ButterflyBiomechanicsCalculator
    
    frames = []
    for i in range(20):
        # Sine wave hip motion: Y ranges from 0.40 to 0.60 (amplitude = 0.20)
        hip_y = 0.50 + 0.10 * np.sin(i * np.pi / 5)
        lm = [MockPoint(0.5, 0.5) for _ in range(33)]
        lm[23] = MockPoint(0.4, hip_y)
        lm[24] = MockPoint(0.6, hip_y)
        lm[15] = MockPoint(0.4, 0.30) # Left wrist
        lm[16] = MockPoint(0.6, 0.35) # Right wrist (diff = 0.05)
        frames.append(FrameData(frame_index=i, timestamp_ms=i*33, raw_landmarks=lm, is_valid=True, stroke_phase="Pull"))

    metrics = calc.calculate_global_metrics(frames, effective_fps=30.0)
    
    assert "hip_undulation_amplitude" in metrics
    assert metrics["hip_undulation_amplitude"].valid is True
    assert abs(metrics["hip_undulation_amplitude"].value - 0.20) < 0.02

    assert "avg_wrist_asymmetry" in metrics
    assert metrics["avg_wrist_asymmetry"].valid is True
    assert abs(metrics["avg_wrist_asymmetry"].value - 0.05) < 1e-4


def test_baseline_json_schema_and_metrics_count():
    """Verify that the machine-readable baseline JSON exists and contains all 41 audited metrics."""
    json_path = Path("data/reference/biomechanics_metric_baseline.json")
    assert json_path.exists(), "biomechanics_metric_baseline.json must exist"
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    assert data["total_metrics_audited"] == 41
    assert len(data["metrics"]) == 41
    assert data["pose_backend"] == "MediaPipe_Tasks_API_Only"
    
    classifications = {m["name"]: m["classification"] for m in data["metrics"]}
    assert classifications["stroke_rate"] == "VALID"
    assert classifications["left_elbow"] == "VALID_WITH_LIMITATIONS"
    assert classifications["body_roll_3d"] == "VALID_WITH_LIMITATIONS"
    assert classifications["temporal_stability_pct"] == "NEEDS_VALIDATION"
    assert classifications["butterfly_symmetry_normalization_factor"] == "UNVERIFIED"
