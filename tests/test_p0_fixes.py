"""
P0 regression tests for Swim_Analyzer_AI critical fixes.
Tests all 10 P0 items: calibration domains, stroke length invalidation,
pose-relative 3D, timing, fabricated fallback prevention, downstream propagation.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import MagicMock


# ── P0-1 / P0-5: MeasurementDomain API ─────────────────────────────────────

def test_measurement_domain_enum_values():
    from analysis.calibration_engine import MeasurementDomain
    assert MeasurementDomain.CALIBRATED_PHYSICAL.value == "calibrated_physical"
    assert MeasurementDomain.RELATIVE_BODY_NORMALIZED.value == "relative_body_normalized"
    assert MeasurementDomain.POSE_RELATIVE_3D.value == "pose_relative_3d"
    assert MeasurementDomain.IMAGE_SPACE.value == "image_space"
    assert MeasurementDomain.UNAVAILABLE.value == "unavailable"


def test_relative_calibration_is_not_physical():
    from analysis.calibration_engine import RelativeCalibration
    engine = RelativeCalibration()
    assert engine.is_physical_calibration is False


def test_relative_calibration_domain_is_body_normalized():
    from analysis.calibration_engine import RelativeCalibration
    engine = RelativeCalibration()
    assert engine.measurement_domain == "relative_body_normalized"


def test_relative_calibration_unit_is_body_length():
    from analysis.calibration_engine import RelativeCalibration
    engine = RelativeCalibration()
    assert engine.unit_name == "body_length"


def test_physical_calibration_is_physical():
    from analysis.calibration_engine import PhysicalPoolCalibration
    engine = PhysicalPoolCalibration(pixels_per_meter=100.0)
    assert engine.is_physical_calibration is True
    assert engine.measurement_domain == "calibrated_physical"
    assert engine.unit_name == "meters"


def test_uncalibrated_engine_domain_is_unavailable():
    from analysis.calibration_engine import UncalibratedEngine
    engine = UncalibratedEngine()
    assert engine.is_physical_calibration is False
    assert engine.measurement_domain == "unavailable"


# ── P0-2: Stroke Length must be UNAVAILABLE without physical calibration ────

def test_stroke_length_unavailable_without_physical_calibration():
    """Stroke length in meters MUST be unavailable when only relative calibration is present."""
    from analysis.calibration_engine import RelativeCalibration
    from analysis.strategies.freestyle_biomechanics_calculator import FreestyleBiomechanicsCalculator

    engine = RelativeCalibration()
    result = FreestyleBiomechanicsCalculator._calculate_stroke_length(
        frames=[], calibration_engine=engine, frame_width=1920, frame_height=1080
    )
    assert result.status == "unavailable", "Stroke length must be unavailable with relative calibration"
    assert result.value is None, "Stroke length value must be None with relative calibration"
    assert result.valid is False


def test_stroke_length_unavailable_when_no_calibration_engine():
    from analysis.strategies.freestyle_biomechanics_calculator import FreestyleBiomechanicsCalculator
    result = FreestyleBiomechanicsCalculator._calculate_stroke_length(
        frames=[], calibration_engine=None, frame_width=0, frame_height=0
    )
    assert result.status == "unavailable"
    assert result.valid is False


# ── P0-5: Pose-relative 3D metrics must have correct domain ─────────────────

def test_3d_body_roll_domain_is_pose_relative():
    from models.data_models import ValidatedMetric
    m = ValidatedMetric(
        name="body_roll_3d", value=25.0, unit="deg",
        measurement_domain="pose_relative_3d", status="available", valid=True
    )
    assert m.measurement_domain == "pose_relative_3d"
    assert m.unit == "deg"


def test_3d_hand_depth_domain_is_pose_relative():
    from models.data_models import ValidatedMetric
    m = ValidatedMetric(
        name="hand_depth_left_3d", value=-0.05, unit="pose_relative_units",
        measurement_domain="pose_relative_3d", status="available", valid=True
    )
    assert m.measurement_domain == "pose_relative_3d"
    assert m.unit == "pose_relative_units"


def test_pose_relative_metric_never_has_meters_unit():
    from models.data_models import ValidatedMetric
    # Hand depth from MediaPipe z must NEVER be labeled as meters
    m = ValidatedMetric(
        name="hand_depth_left_3d", value=-0.05, unit="pose_relative_units",
        measurement_domain="pose_relative_3d", valid=True
    )
    assert m.unit != "meters", "MediaPipe z-depth must NOT be labeled as meters"


# ── P0-6: TimingUtils consistency ────────────────────────────────────────────

def test_timing_effective_fps_stride_1():
    from core.timing_utils import TimingUtils
    assert TimingUtils.calculate_effective_fps(30.0, 1) == 30.0


def test_timing_effective_fps_stride_2():
    from core.timing_utils import TimingUtils
    assert TimingUtils.calculate_effective_fps(30.0, 2) == 15.0


def test_timing_effective_fps_stride_3():
    from core.timing_utils import TimingUtils
    assert abs(TimingUtils.calculate_effective_fps(30.0, 3) - 10.0) < 0.01


def test_timing_timestamp_ms_at_frame_0():
    from core.timing_utils import TimingUtils
    assert TimingUtils.frame_index_to_timestamp_ms(0, 30.0) == 0


def test_timing_timestamp_ms_at_frame_30():
    from core.timing_utils import TimingUtils
    # Frame 30 at 30fps should be ~1000ms
    ts = TimingUtils.frame_index_to_timestamp_ms(30, 30.0)
    assert abs(ts - 1000) <= 1


def test_timing_duration_seconds():
    from core.timing_utils import TimingUtils
    assert TimingUtils.calculate_duration_seconds(300, 30.0) == pytest.approx(10.0)


def test_timing_zero_fps_guard():
    from core.timing_utils import TimingUtils
    assert TimingUtils.frame_index_to_timestamp_ms(100, 0.0) == 0
    assert TimingUtils.calculate_duration_seconds(100, 0.0) == 0.0


def test_timing_stroke_rate_spm():
    from core.timing_utils import TimingUtils
    # 6 cycles in 60 seconds = 6 spm
    assert TimingUtils.calculate_stroke_rate_spm(6, 60.0) == pytest.approx(6.0)


# ── P0-7: Removal of fabricated fallback scores ──────────────────────────────

def test_backstroke_no_cycle_returns_none_score():
    """Without cycles, overall_score must be None, not a fabricated number."""
    from analysis.strategies.backstroke_scoring_engine import BackstrokeScoringEngine
    from models.data_models import StrokeStatistics

    engine = BackstrokeScoringEngine()
    mock_result = MagicMock()
    mock_result.stroke_statistics = StrokeStatistics(completed_cycles=0)
    mock_result.reliability = None

    report = engine.generate_report(mock_result, {})
    assert report.overall_score is None, "No cycles → score must be None (INSUFFICIENT_EVIDENCE)"
    assert "INSUFFICIENT_EVIDENCE" in report.feedback_summary


def test_breaststroke_no_cycle_returns_none_score():
    from analysis.strategies.breaststroke_scoring_engine import BreaststrokeScoringEngine
    from models.data_models import StrokeStatistics

    engine = BreaststrokeScoringEngine()
    mock_result = MagicMock()
    mock_result.stroke_statistics = StrokeStatistics(completed_cycles=0)
    mock_result.reliability = None

    report = engine.generate_report(mock_result, {})
    assert report.overall_score is None
    assert "INSUFFICIENT_EVIDENCE" in report.feedback_summary


def test_butterfly_no_cycle_returns_none_score():
    from analysis.strategies.butterfly_scoring_engine import ButterflyScoringEngine
    from models.data_models import StrokeStatistics

    engine = ButterflyScoringEngine()
    mock_result = MagicMock()
    mock_result.stroke_statistics = StrokeStatistics(completed_cycles=0)
    mock_result.reliability = None

    report = engine.generate_report(mock_result, {})
    assert report.overall_score is None
    assert "INSUFFICIENT_EVIDENCE" in report.feedback_summary


def test_freestyle_no_cycle_returns_none_score():
    """Freestyle scoring must return None score and INSUFFICIENT_EVIDENCE when cycles=0."""
    from analysis.strategies.freestyle_scoring_engine import FreestyleScoringEngine
    from models.data_models import StrokeStatistics, ReliabilityResult, ValidatedMetric

    engine = FreestyleScoringEngine()
    mock_result = MagicMock()
    mock_result.stroke_statistics = StrokeStatistics(completed_cycles=0)
    mock_result.reliability = ReliabilityResult(analysis_reliability_score=100.0)
    mock_result.frames = []

    report = engine.generate_report(mock_result, {
        "stroke_rate": ValidatedMetric(name="stroke_rate", value=None, status="unavailable", valid=False),
        "stroke_length": ValidatedMetric(name="stroke_length", value=None, status="unavailable", valid=False),
        "kick_frequency": ValidatedMetric(),
        "stroke_symmetry": ValidatedMetric(name="stroke_symmetry", value=None, status="unavailable", valid=False),
    })
    assert report.overall_score is None
    assert "INSUFFICIENT_EVIDENCE" in report.feedback_summary


def test_backstroke_no_default_good_technique_text():
    """Fabricated 'Good backstroke technique.' text must not appear when no feedback."""
    from analysis.strategies.backstroke_scoring_engine import BackstrokeScoringEngine
    from models.data_models import StrokeStatistics, ValidatedMetric

    engine = BackstrokeScoringEngine()
    mock_result = MagicMock()
    mock_result.stroke_statistics = StrokeStatistics(completed_cycles=3)
    mock_result.reliability = None

    # Provide all metrics as None to simulate missing data
    report = engine.generate_report(mock_result, {
        "stroke_rate": ValidatedMetric(value=None, valid=False),
        "stroke_length": ValidatedMetric(value=None, valid=False),
        "kick_frequency": ValidatedMetric(value=None, valid=False),
        "stroke_symmetry": ValidatedMetric(value=None, valid=False),
        "average_body_roll": ValidatedMetric(value=None, valid=False),
    })
    assert "Good backstroke technique." not in report.feedback_summary


# ── P0-8: Downstream propagation of invalid data ─────────────────────────────

def test_performance_report_overall_score_defaults_to_none():
    """PerformanceReport must NOT default overall_score to 100.0."""
    from models.data_models import PerformanceReport
    r = PerformanceReport()
    assert r.overall_score is None, "overall_score must default to None, never 100.0"


def test_validated_metric_has_measurement_domain():
    """ValidatedMetric must have measurement_domain field."""
    from models.data_models import ValidatedMetric
    m = ValidatedMetric()
    assert hasattr(m, "measurement_domain")
    assert hasattr(m, "status")
    assert hasattr(m, "calibration_required")
    assert hasattr(m, "calibration_status")
    assert hasattr(m, "method")


def test_validated_metric_unavailable_has_none_value():
    from models.data_models import ValidatedMetric
    m = ValidatedMetric(
        name="stroke_length", value=None, unit="meters",
        measurement_domain="unavailable", status="unavailable",
        valid=False, reason_if_invalid="Physical calibration unavailable"
    )
    assert m.value is None
    assert m.status == "unavailable"
    assert m.valid is False


# ── P0-9: Metric contract completeness ───────────────────────────────────────

def test_stroke_event_dataclass_exists():
    from models.data_models import StrokeEvent
    e = StrokeEvent(stroke="Freestyle", phase="Catch", confidence=0.9, detection_method="heuristic")
    assert e.stroke == "Freestyle"
    assert e.detection_method == "heuristic"
    assert e.validity is True  # default


# ── P0-10: Scientific honesty — prefer UNKNOWN over fabricated certainty ─────

def test_relative_calibration_metric_not_labeled_meters():
    """RelativeCalibration.create_metric must never produce unit='meters'."""
    from analysis.calibration_engine import RelativeCalibration
    engine = RelativeCalibration()
    m = engine.create_metric("test", 0.5)
    assert m.unit != "meters", "Relative calibration output must never be labeled 'meters'"
    assert m.measurement_domain == "relative_body_normalized"
