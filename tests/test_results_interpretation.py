"""
Tests for Results Interpretation and Scientific Trustworthiness UI (P0-16).
Verifies:
1. Single component perfect score yields technique_assessment == 'INSUFFICIENT EVIDENCE', never 'Excellent'.
2. Two components yield evidence_sufficiency == 'LIMITED' and technique_assessment == 'LIMITED EVIDENCE'.
3. Three or more components yield evidence_sufficiency == 'SUFFICIENT' and standard assessment.
4. High symmetry alone does not mislead into 'Excellent'.
5. Perfect analysis reliability (100.0) does not imply scientific validation.
6. Perfect internal consistency (100.0) does not imply scientific validation.
7. Unvalidated population cohort returns None for percentile and Z-score.
8. Youth cohort never falls back to adult benchmarks.
9. Validated cohort evaluates normally with genuine Z-score and percentile.
10. Cross-gender fallback is strictly rejected.
11. Zero completed cycles yields overall_score is None and evidence_sufficiency == 'INSUFFICIENT'.
12. ExportService and PDF generation preserve evidence-aware interpretation and do not claim unverified excellence.
"""

import os
import json
import pytest
from pathlib import Path
from models.data_models import (
    AnalysisResult, FrameData, JointAngles, ValidatedMetric,
    StrokeStatistics, ReliabilityResult, ConsistencyReport,
    PerformanceReport, VideoMetadata
)
from models.athlete_profile import AthleteProfile
from analysis.strategies.freestyle_scoring_engine import FreestyleScoringEngine
from analysis.strategies.backstroke_scoring_engine import BackstrokeScoringEngine
from analysis.strategies.breaststroke_scoring_engine import BreaststrokeScoringEngine
from analysis.strategies.butterfly_scoring_engine import ButterflyScoringEngine
from analysis.benchmarks.benchmark_engine import BenchmarkEngine
from services.export_service import ExportService
from services.pdf_report_service import PDFReportService


def make_frame(idx: int, phase: str, left_elbow=None, right_elbow=None,
               left_shoulder=None, right_shoulder=None,
               left_knee=None, right_knee=None, valid=True):
    angles = JointAngles(
        left_elbow=ValidatedMetric(value=left_elbow, valid=valid and (left_elbow is not None)) if left_elbow is not None else None,
        right_elbow=ValidatedMetric(value=right_elbow, valid=valid and (right_elbow is not None)) if right_elbow is not None else None,
        left_shoulder=ValidatedMetric(value=left_shoulder, valid=valid and (left_shoulder is not None)) if left_shoulder is not None else None,
        right_shoulder=ValidatedMetric(value=right_shoulder, valid=valid and (right_shoulder is not None)) if right_shoulder is not None else None,
        left_knee=ValidatedMetric(value=left_knee, valid=valid and (left_knee is not None)) if left_knee is not None else None,
        right_knee=ValidatedMetric(value=right_knee, valid=valid and (right_knee is not None)) if right_knee is not None else None,
    )
    return FrameData(frame_index=idx, timestamp_ms=idx * 33, stroke_phase=phase, angles=angles, is_valid=valid, raw_landmarks=[])


def make_analysis(frames, cycles=3, reliability=90.0, consistency=90.0, stroke_type="Freestyle"):
    res = AnalysisResult()
    res.stroke_type = stroke_type
    res.frames = frames
    res.stroke_statistics = StrokeStatistics(completed_cycles=cycles, average_phase_confidence=0.85)
    res.reliability = ReliabilityResult(
        analysis_reliability_score=reliability,
        analysis_reliability_level="High" if reliability >= 80 else "Medium",
        pose_tracking_coverage_pct=95.0,
        temporal_stability_pct=90.0,
        landmark_visibility_pct=88.0,
        cycle_quality_pct=92.0,
        measurement_stability_pct=91.0
    )
    res.consistency = ConsistencyReport(
        overall_score=consistency,
        validation_status="Passed" if consistency >= 80 else "Warning",
        scientific_confidence="High" if consistency >= 80 else "Medium"
    )
    return res


def test_single_component_does_not_yield_excellent():
    """1. Single available component scoring 100 yields INSUFFICIENT EVIDENCE, never Excellent."""
    engine = FreestyleScoringEngine()
    # Frames have no valid angles, only global stroke symmetry is valid
    frames = [
        make_frame(0, "Pull"),
        make_frame(1, "Recovery")
    ]
    ar = make_analysis(frames, cycles=2, reliability=85.0)
    global_metrics = {
        "stroke_symmetry": ValidatedMetric(value=100.0, valid=True)
    }
    report = engine.generate_report(ar, global_metrics)

    assert report.overall_score == 100.0
    assert report.evidence_sufficiency == "INSUFFICIENT"
    assert report.technique_assessment == "INSUFFICIENT EVIDENCE"
    assert "Stroke Symmetry" in report.available_components
    assert len(report.available_components) == 1
    assert report.technique_assessment != "Excellent"


def test_two_components_yields_limited_evidence():
    """2. Two components scoring 100 yields LIMITED and LIMITED EVIDENCE."""
    engine = FreestyleScoringEngine()
    # Pull elbow angles provided (1 component), plus global symmetry (1 component) = 2 components
    frames = [
        make_frame(0, "Pull", left_elbow=105.0, right_elbow=105.0),
        make_frame(1, "Pull", left_elbow=105.0, right_elbow=105.0),
    ]
    ar = make_analysis(frames, cycles=2, reliability=85.0)
    global_metrics = {
        "stroke_symmetry": ValidatedMetric(value=100.0, valid=True)
    }
    report = engine.generate_report(ar, global_metrics)

    assert report.overall_score == 100.0
    assert report.evidence_sufficiency == "LIMITED"
    assert report.technique_assessment == "LIMITED EVIDENCE"
    assert len(report.available_components) == 2


def test_sufficient_components_yields_standard_assessment():
    """3. Three or more components scoring high yields SUFFICIENT and standard assessment."""
    engine = FreestyleScoringEngine()
    # Pull elbow, recovery shoulder, and symmetry = 3 components
    frames = [
        make_frame(0, "Pull", left_elbow=105.0, right_elbow=105.0),
        make_frame(1, "Recovery", left_shoulder=160.0, right_shoulder=160.0),
    ]
    ar = make_analysis(frames, cycles=2, reliability=85.0)
    global_metrics = {
        "stroke_symmetry": ValidatedMetric(value=95.0, valid=True)
    }
    report = engine.generate_report(ar, global_metrics)

    assert report.evidence_sufficiency == "SUFFICIENT"
    assert report.technique_assessment == "Excellent"
    assert len(report.available_components) >= 3


def test_high_symmetry_alone_does_not_mislead():
    """4. High symmetry alone with missing angles does not produce Excellent and warns in feedback."""
    engine = FreestyleScoringEngine()
    frames = [make_frame(0, "Pull")]
    ar = make_analysis(frames, cycles=2, reliability=85.0)
    global_metrics = {
        "stroke_symmetry": ValidatedMetric(value=98.0, valid=True)
    }
    report = engine.generate_report(ar, global_metrics)

    assert report.technique_assessment == "INSUFFICIENT EVIDENCE"
    assert "insufficient" in report.feedback_summary.lower() or "caution" in report.feedback_summary.lower()


def test_perfect_reliability_does_not_imply_scientific_validation():
    """5. Reliability 100.0 does NOT change empirical validation status (NOT_VALIDATED — INSUFFICIENT GROUND TRUTH)."""
    engine = FreestyleScoringEngine()
    frames = [make_frame(0, "Pull")]
    ar = make_analysis(frames, cycles=3, reliability=100.0)
    report = engine.generate_report(ar, {})

    # Ground truth validation is strictly not validated regardless of reliability score
    assert ar.reliability.analysis_reliability_score == 100.0
    assert ar.reliability.scientific_validation_status == "NOT_VALIDATED — INSUFFICIENT GROUND TRUTH"


def test_perfect_consistency_does_not_imply_scientific_validation():
    """6. Internal consistency 100.0 does NOT change empirical validation status."""
    engine = FreestyleScoringEngine()
    frames = [make_frame(0, "Pull")]
    ar = make_analysis(frames, cycles=3, reliability=70.0, consistency=100.0)
    report = engine.generate_report(ar, {})

    assert ar.consistency.overall_score == 100.0
    assert ar.reliability.scientific_validation_status == "NOT_VALIDATED — INSUFFICIENT GROUND TRUTH"


def test_unvalidated_population_cohort_returns_na():
    """7. Benchmark for unsupported cohort returns None for percentile and Z-score."""
    engine = BenchmarkEngine()
    ar = AnalysisResult()
    ar.stroke_type = "Freestyle"
    ar.report = PerformanceReport(
        overall_score=80.0,
        stroke_rate=ValidatedMetric(value=50.0, valid=True)
    )
    # 8-year-old child (U10) - no population data in freestyle.yaml
    child_profile = AthleteProfile(
        coach_id="c1", full_name="Toddler", age=8, gender="Male",
        height_cm=125.0, weight_kg=25.0, swimming_level="Beginner", preferred_stroke="Freestyle"
    )
    res = engine.evaluate_analysis(ar, child_profile)

    assert res.is_population_compatible is False
    assert res.validation_status == "unvalidated_cohort"
    assert res.overall_skill_level == "N/A (Unvalidated Cohort)"
    sr_comp = res.comparisons.get("stroke_rate")
    assert sr_comp is not None
    assert sr_comp.z_score is None
    assert sr_comp.percentile is None


def test_youth_cohort_never_falls_back_to_adult():
    """8. Youth swimmer (age 12) looking up Freestyle returns None, never adult 18-25 benchmark."""
    engine = BenchmarkEngine()
    ar = AnalysisResult()
    ar.stroke_type = "Freestyle"
    ar.report = PerformanceReport(
        overall_score=80.0,
        stroke_rate=ValidatedMetric(value=50.0, valid=True)
    )
    youth_profile = AthleteProfile(
        coach_id="c1", full_name="Junior", age=12, gender="Male",
        height_cm=150.0, weight_kg=40.0, swimming_level="Intermediate", preferred_stroke="Freestyle"
    )
    res = engine.evaluate_analysis(ar, youth_profile)

    assert res.is_population_compatible is False
    sr_comp = res.comparisons.get("stroke_rate")
    assert sr_comp.population_mean is None
    assert sr_comp.z_score is None
    assert sr_comp.percentile is None


def test_validated_cohort_evaluates_normally():
    """9. Explicitly supported population cohort evaluates normally with genuine Z-score and percentile."""
    engine = BenchmarkEngine()
    stats = engine._get_population_stats("Freestyle", "Mixed", "Male", "stroke_rate")
    assert stats.mean == 54.0
    assert stats.std is not None
    z = engine.calculate_z_score(54.0, stats.mean, stats.std)
    assert z is not None
    assert abs(z - 0.0) < 0.01
    pct = engine.calculate_percentile(z, stats.higher_is_better)
    assert pct is not None
    assert abs(pct - 50.0) < 1.0


def test_cross_gender_fallback_rejected():
    """10. Male looking up Female-only cohort or vice versa returns None."""
    engine = BenchmarkEngine()
    # Backstroke has Mixed Male but NO Mixed Female
    stats = engine._get_population_stats("Backstroke", "Mixed", "Female", "stroke_rate")
    assert stats.mean is None
    assert stats.std is None


def test_zero_cycles_yields_insufficient_evidence():
    """11. Zero completed cycles yields overall_score is None and INSUFFICIENT EVIDENCE."""
    engine = FreestyleScoringEngine()
    frames = [
        make_frame(0, "Pull", left_elbow=105.0, right_elbow=105.0),
        make_frame(1, "Recovery", left_shoulder=160.0, right_shoulder=160.0),
    ]
    # 0 completed cycles
    ar = make_analysis(frames, cycles=0, reliability=85.0)
    report = engine.generate_report(ar, {})

    assert report.overall_score is None
    assert report.evidence_sufficiency == "INSUFFICIENT"
    assert report.technique_assessment == "INSUFFICIENT EVIDENCE"


def test_pdf_and_export_interpretation_consistency(tmp_path):
    """12. ExportService and PDF generation serialize evidence fields and do not claim unverified excellence."""
    engine = FreestyleScoringEngine()
    frames = [make_frame(0, "Pull")]
    ar = make_analysis(frames, cycles=2, reliability=75.0)
    global_metrics = {"stroke_symmetry": ValidatedMetric(value=100.0, valid=True)}
    ar.report = engine.generate_report(ar, global_metrics)

    # Test ExportService
    meta = VideoMetadata(filename="test_video.mp4", confidence_statistics={"average_confidence": 0.8})
    
    rep_path, meta_path, time_path = ExportService.export_to_json(ar, meta, "test_video.mp4")
    assert rep_path and os.path.exists(rep_path)
    with open(rep_path, "r") as f:
        data = json.load(f)

    assert "reliability" in data
    assert data["reliability"]["analysis_reliability_score"] == 75.0
    assert data["reliability"]["scientific_validation_status"] == "NOT_VALIDATED — INSUFFICIENT GROUND TRUTH"
    assert "report" in data
    assert data["report"]["evidence_sufficiency"] == "INSUFFICIENT"
    assert data["report"]["technique_assessment"] == "INSUFFICIENT EVIDENCE"
    assert "Stroke Symmetry" in data["report"]["available_components"]

    # Test PDF Generation
    pdf_service = PDFReportService(output_dir=str(tmp_path))
    pdf_path = pdf_service.generate_session_analysis_pdf(ar)
    assert pdf_path and os.path.exists(pdf_path)
