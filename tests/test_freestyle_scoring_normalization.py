"""
Tests for Freestyle Scoring Normalization (P0-2).
Verifies that:
1. All components present and perfect -> 100.0
2. Missing symmetry -> normalized over remaining weights
3. Missing pull phase -> normalized over remaining weights
4. Only one component available with perfect score -> 100.0
5. Zero available components -> None
6. Downstream cycle check (0 cycles) -> None
7. Low reliability (< 40) -> None
8. Score clamping between 0 and 100
"""

import pytest
from analysis.strategies.freestyle_scoring_engine import FreestyleScoringEngine
from models.data_models import (
    AnalysisResult, FrameData, JointAngles, ValidatedMetric,
    StrokeStatistics, ReliabilityResult
)

def make_frame(idx: int, phase: str, left_elbow=100.0, right_elbow=100.0,
               left_shoulder=160.0, right_shoulder=160.0,
               left_knee=165.0, right_knee=165.0, valid=True):
    angles = JointAngles(
        left_elbow=ValidatedMetric(value=left_elbow, valid=valid if left_elbow is not None else False) if left_elbow is not None else None,
        right_elbow=ValidatedMetric(value=right_elbow, valid=valid if right_elbow is not None else False) if right_elbow is not None else None,
        left_shoulder=ValidatedMetric(value=left_shoulder, valid=valid if left_shoulder is not None else False) if left_shoulder is not None else None,
        right_shoulder=ValidatedMetric(value=right_shoulder, valid=valid if right_shoulder is not None else False) if right_shoulder is not None else None,
        left_knee=ValidatedMetric(value=left_knee, valid=valid if left_knee is not None else False) if left_knee is not None else None,
        right_knee=ValidatedMetric(value=right_knee, valid=valid if right_knee is not None else False) if right_knee is not None else None
    )
    return FrameData(frame_index=idx, timestamp_ms=idx * 33, stroke_phase=phase, angles=angles, is_valid=valid, raw_landmarks=[])

def make_analysis(frames, cycles=3, reliability=90.0):
    res = AnalysisResult()
    res.frames = frames
    res.stroke_statistics = StrokeStatistics(completed_cycles=cycles)
    res.reliability = ReliabilityResult(analysis_reliability_score=reliability)
    return res

def test_all_components_present_and_perfect():
    engine = FreestyleScoringEngine()
    frames = [
        make_frame(0, "Pull", left_elbow=105.0, right_elbow=105.0, left_shoulder=160.0, right_shoulder=160.0, left_knee=165.0, right_knee=165.0),
        make_frame(1, "Recovery", left_elbow=105.0, right_elbow=105.0, left_shoulder=160.0, right_shoulder=160.0, left_knee=165.0, right_knee=165.0),
    ]
    ar = make_analysis(frames, cycles=2, reliability=85.0)
    global_metrics = {
        "stroke_symmetry": ValidatedMetric(value=100.0, valid=True)
    }
    report = engine.generate_report(ar, global_metrics)
    assert report.overall_score == 100.0
    assert len(report.errors) == 0

def test_missing_symmetry_normalized_over_remaining():
    engine = FreestyleScoringEngine()
    frames = [
        make_frame(0, "Pull", left_elbow=105.0, right_elbow=105.0, left_shoulder=160.0, right_shoulder=160.0, left_knee=165.0, right_knee=165.0),
        make_frame(1, "Recovery", left_elbow=105.0, right_elbow=105.0, left_shoulder=160.0, right_shoulder=160.0, left_knee=165.0, right_knee=165.0),
    ]
    ar = make_analysis(frames, cycles=2, reliability=85.0)
    # Symmetry is missing / invalid
    global_metrics = {
        "stroke_symmetry": ValidatedMetric(value=None, valid=False)
    }
    report = engine.generate_report(ar, global_metrics)
    # Remaining weights: elbow (0.25), shoulder (0.20), knee (0.15) -> all perfect -> normalized to 100.0
    assert report.overall_score == 100.0

def test_missing_pull_phase_normalized_over_remaining():
    engine = FreestyleScoringEngine()
    # Frames only in Recovery (no Pull phase)
    frames = [
        make_frame(0, "Recovery", left_elbow=None, right_elbow=None, left_shoulder=160.0, right_shoulder=160.0, left_knee=165.0, right_knee=165.0),
        make_frame(1, "Recovery", left_elbow=None, right_elbow=None, left_shoulder=160.0, right_shoulder=160.0, left_knee=165.0, right_knee=165.0),
    ]
    ar = make_analysis(frames, cycles=2, reliability=85.0)
    global_metrics = {
        "stroke_symmetry": ValidatedMetric(value=100.0, valid=True)
    }
    report = engine.generate_report(ar, global_metrics)
    # Missing pull elbow -> omitted from denominator, normalized score should still be 100.0
    assert report.overall_score == 100.0

def test_only_one_component_available_perfect():
    engine = FreestyleScoringEngine()
    # No valid angles at all in frames
    frames = [
        make_frame(0, "Unknown", left_elbow=None, right_elbow=None, left_shoulder=None, right_shoulder=None, left_knee=None, right_knee=None),
    ]
    ar = make_analysis(frames, cycles=2, reliability=85.0)
    # Only symmetry is valid and 100.0
    global_metrics = {
        "stroke_symmetry": ValidatedMetric(value=100.0, valid=True)
    }
    report = engine.generate_report(ar, global_metrics)
    # Sole available component (symmetry=100) must yield 100.0, not 20.0!
    assert report.overall_score == 100.0

def test_zero_available_components_returns_none():
    engine = FreestyleScoringEngine()
    frames = [
        make_frame(0, "Unknown", left_elbow=None, right_elbow=None, left_shoulder=None, right_shoulder=None, left_knee=None, right_knee=None),
    ]
    ar = make_analysis(frames, cycles=2, reliability=85.0)
    global_metrics = {
        "stroke_symmetry": ValidatedMetric(value=None, valid=False)
    }
    report = engine.generate_report(ar, global_metrics)
    assert report.overall_score is None
    assert "METRIC_UNAVAILABLE" in report.feedback_summary

def test_downstream_cycle_check_zero_cycles():
    engine = FreestyleScoringEngine()
    frames = [
        make_frame(0, "Pull", left_elbow=105.0, right_elbow=105.0),
    ]
    # 0 completed cycles
    ar = make_analysis(frames, cycles=0, reliability=85.0)
    global_metrics = {
        "stroke_symmetry": ValidatedMetric(value=100.0, valid=True)
    }
    report = engine.generate_report(ar, global_metrics)
    assert report.overall_score is None
    assert "INSUFFICIENT_EVIDENCE" in report.feedback_summary

def test_low_reliability_returns_none():
    engine = FreestyleScoringEngine()
    frames = [
        make_frame(0, "Pull", left_elbow=105.0, right_elbow=105.0),
    ]
    # Reliability below 40 threshold
    ar = make_analysis(frames, cycles=2, reliability=35.0)
    global_metrics = {
        "stroke_symmetry": ValidatedMetric(value=100.0, valid=True)
    }
    report = engine.generate_report(ar, global_metrics)
    assert report.overall_score is None
    assert "INSUFFICIENT_EVIDENCE" in report.feedback_summary

def test_score_clamping_between_0_and_100():
    engine = FreestyleScoringEngine()
    # All components with severe penalties
    frames = [
        make_frame(0, "Pull", left_elbow=50.0, right_elbow=50.0, left_shoulder=100.0, right_shoulder=100.0, left_knee=90.0, right_knee=90.0),
    ]
    ar = make_analysis(frames, cycles=2, reliability=85.0)
    global_metrics = {
        "stroke_symmetry": ValidatedMetric(value=0.0, valid=True)
    }
    report = engine.generate_report(ar, global_metrics)
    assert report.overall_score is not None
    assert 0.0 <= report.overall_score <= 100.0
