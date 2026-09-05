"""
Regression tests for the BenchmarkService -> BenchmarkEngine API contract.
"""

import pytest
from services.benchmark_service import BenchmarkService
from analysis.benchmarks.benchmark_engine import BenchmarkEngine
from models.benchmark_models import BenchmarkResult
from models.data_models import AnalysisResult, PerformanceReport, ValidatedMetric, StrokeDetectionResult, StrokeType
from models.athlete_profile import AthleteProfile
from models.scientific_evidence_models import ValidationStatus


def test_benchmark_service_evaluate_session_api_compatibility():
    """Verify BenchmarkService calls BenchmarkEngine without AttributeError."""
    service = BenchmarkService()

    analysis_result = AnalysisResult(video_path="dummy.mp4")
    # stroke_detection lives on VideoMetadata, NOT AnalysisResult.
    # The engine uses getattr(..., None) so this is fine.
    analysis_result.report = PerformanceReport(
        overall_score=85.0,
        stroke_rate=ValidatedMetric(name="stroke_rate", value=55.0, valid=True, unit="spm"),
        stroke_length=ValidatedMetric(name="stroke_length", value=None, valid=False, unit="m"),
    )

    athlete = AthleteProfile(coach_id="test_coach", full_name="Test Athlete",
        age=22,
        gender="Male",
        height_cm=180.0,
        weight_kg=75.0,
        swimming_level="Elite",
        preferred_stroke="Freestyle",
    )

    res = service.evaluate_session(analysis_result, athlete)

    assert res is not None
    assert res.stroke_type == "Freestyle"   # default when no stroke_detection
    assert res.age_group == "18-25"
    assert res.gender == "Male"
    # stroke_rate has a valid value, must appear in comparisons
    assert "stroke_rate" in res.comparisons

    # stroke_length value is None — zero-fallback policy: must NOT appear or raw_value must be None
    if "stroke_length" in res.comparisons:
        assert res.comparisons["stroke_length"].raw_value is None


def test_benchmark_service_uses_the_public_evaluate_analysis_api(monkeypatch):
    """The service must call the engine's real public evaluation method."""
    engine = BenchmarkEngine()
    service = BenchmarkService()
    service.engine = engine
    called = []

    def evaluate_analysis(result, athlete_profile=None):
        called.append((result, athlete_profile))
        return BenchmarkResult(stroke_type="Freestyle")

    monkeypatch.setattr(engine, "evaluate_analysis", evaluate_analysis)
    analysis_result = AnalysisResult(video_path="dummy.mp4")

    result = service.evaluate_session(analysis_result)

    assert called == [(analysis_result, None)]
    assert result is analysis_result.benchmark_result
    assert not hasattr(engine, "evaluate_full_analysis")


def test_benchmark_engine_evaluate_analysis_returns_a_valid_result():
    """A valid analysis reaches the actual engine evaluation API."""
    engine = BenchmarkEngine()

    analysis_result = AnalysisResult(video_path="dummy.mp4")
    analysis_result.report = PerformanceReport(
        overall_score=90.0,
        stroke_rate=ValidatedMetric(name="stroke_rate", value=60.0, valid=True, unit="spm"),
    )

    res = engine.evaluate_analysis(analysis_result)
    assert res is not None
    assert res.stroke_type == "Freestyle"
    assert "stroke_rate" in res.comparisons


def test_benchmark_engine_no_stroke_detection_no_error():
    """Verify that missing stroke_detection attribute does NOT raise AttributeError."""
    engine = BenchmarkEngine()
    ar = AnalysisResult(video_path="dummy.mp4")
    # Intentionally no stroke_detection attribute set
    try:
        res = engine.evaluate_analysis(ar)
        assert res is not None
        assert res.stroke_type == "Freestyle"
    except AttributeError as e:
        pytest.fail(f"AttributeError raised: {e}")


def test_benchmark_result_none_metric_stays_none():
    """Verify zero-fallback: ValidatedMetric with value=None does NOT produce a comparison."""
    engine = BenchmarkEngine()
    ar = AnalysisResult(video_path="dummy.mp4")
    ar.report = PerformanceReport(
        overall_score=None,
        stroke_rate=ValidatedMetric(name="stroke_rate", value=None, valid=False),
        stroke_length=ValidatedMetric(name="stroke_length", value=None, valid=False),
    )
    res = engine.evaluate_analysis(ar)
    # None metrics must NOT generate comparisons with fabricated fallback values
    for name, comp in res.comparisons.items():
        assert comp.raw_value is not None, f"Expected no comparison for {name} with None value, but got one."


def test_missing_dataset_returns_insufficient_evidence_without_freestyle_fallback():
    engine = BenchmarkEngine()
    ar = AnalysisResult(video_path="dummy.mp4")
    ar.stroke_detection = StrokeDetectionResult(selected_stroke=StrokeType.UNKNOWN)
    ar.report = PerformanceReport(stroke_rate=ValidatedMetric(name="stroke_rate", value=55.0))

    result = engine.evaluate_analysis(ar)

    assert result.stroke_type == StrokeType.UNKNOWN.value
    assert result.validation_status == "insufficient_evidence"
    assert result.comparisons == {}


def test_missing_statistics_remain_unavailable_without_numeric_fallback(tmp_path):
    (tmp_path / "freestyle.yaml").write_text(
        "stroke: Freestyle\npopulations:\n  '18-25':\n    Male:\n      stroke_rate:\n        unit: spm\n",
        encoding="utf-8",
    )
    engine = BenchmarkEngine(tmp_path)

    stats = engine._get_population_stats("Freestyle", "18-25", "Male", "stroke_rate")

    assert stats.mean is None
    assert stats.std is None
    assert stats.elite_mean is None
    assert stats.evidence.validation_status == ValidationStatus.INSUFFICIENT_EVIDENCE
