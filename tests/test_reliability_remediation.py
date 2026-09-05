"""
Tests for Measurement Reliability and Scientific Validation Decoupling (P1-6 & P1-7).
Verifies:
1. Reliability score weights sum to exactly 1.00 (0.30 + 0.25 + 0.20 + 0.15 + 0.10).
2. Frame coverage and pose validity are not double counted.
3. High tracking reliability does NOT claim scientific validation (scientific_validation_status remains NOT_VALIDATED).
4. Measurement reliability score and level are properly populated.
"""

import pytest
from analysis.reliability_engine import ReliabilityEngine
from models.data_models import (
    AnalysisResult, FrameData, JointAngles, ValidatedMetric,
    StrokeStatistics, PerformanceReport
)

class MockLandmark:
    def __init__(self, visibility=0.95):
        self.visibility = visibility

def make_frame(idx: int, is_valid=True):
    lms = [MockLandmark(0.95) for _ in range(33)]
    return FrameData(
        frame_index=idx,
        timestamp_ms=idx * 33,
        stroke_phase="Pull",
        phase_confidence=0.9,
        angles=JointAngles(),
        is_valid=is_valid,
        raw_landmarks=lms
    )

def test_decoupled_weights_and_no_double_counting():
    # 20 frames, all valid, 3 completed cycles, valid metrics
    frames = [make_frame(i, is_valid=True) for i in range(20)]
    ar = AnalysisResult()
    ar.frames = frames
    ar.stroke_statistics = StrokeStatistics(completed_cycles=3)
    ar.report = PerformanceReport(
        stroke_rate=ValidatedMetric(value=54.0, valid=True),
        stroke_length=ValidatedMetric(value=1.85, valid=True)
    )

    result = ReliabilityEngine.evaluate(ar)

    assert result.pose_tracking_coverage_pct == 100.0
    assert result.landmark_visibility_pct == 95.0
    assert result.cycle_quality_pct == 100.0
    assert result.temporal_stability_pct == 90.0
    assert result.measurement_stability_pct == 100.0

    # Calculated reliability:
    # 0.30*100 + 0.25*95 + 0.20*90 + 0.15*100 + 0.10*100 = 30 + 23.75 + 18 + 15 + 10 = 96.75 -> 96.8
    assert result.analysis_reliability_score == pytest.approx(96.8, abs=0.2)
    assert result.measurement_reliability_score == pytest.approx(96.8, abs=0.2)
    assert result.measurement_reliability_level == "High"

def test_scientific_validation_status_never_claimed_validated():
    # Even with 100% perfect tracking reliability, scientific_validation_status must NOT be "VALIDATED"
    frames = [make_frame(i, is_valid=True) for i in range(30)]
    ar = AnalysisResult()
    ar.frames = frames
    ar.stroke_statistics = StrokeStatistics(completed_cycles=4)
    ar.report = PerformanceReport(
        stroke_rate=ValidatedMetric(value=54.0, valid=True),
        stroke_length=ValidatedMetric(value=1.85, valid=True)
    )

    result = ReliabilityEngine.evaluate(ar)

    assert result.analysis_reliability_score > 80.0
    assert result.measurement_reliability_level == "High"
    # Must remain NOT_VALIDATED — INSUFFICIENT GROUND TRUTH
    assert "NOT_VALIDATED" in result.scientific_validation_status
    assert "INSUFFICIENT GROUND TRUTH" in result.scientific_validation_status
