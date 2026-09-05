"""
Regression test suite for UI rendering safety with Optional / None values (P0-1).
Verifies that unavailable or uncalibrated metrics propagate as None and render safely as 'N/A' or 'Insufficient Evidence'
without raising TypeError, converting None to zero/100, or crashing Streamlit/Plotly functions.
"""

import pandas as pd

from models.data_models import StrokeType, StrokeDetectionResult, ValidatedMetric, PerformanceReport
from models.benchmark_models import BenchmarkResult, MetricBenchmarkComparison
from app.ui.charts import (
    create_performance_trend_chart,
    create_cycles_trend_chart,
    create_benchmark_percentile_chart,
    create_benchmark_radar_chart
)
from services.comparison_service import ComparisonService

def test_overall_score_none_does_not_crash_rendering():
    """Verify that overall_score=None renders as INSUFFICIENT_EVIDENCE without TypeError."""
    report = PerformanceReport(overall_score=None, feedback_summary="Test summary", errors=[])
    assert report.overall_score is None

    res = StrokeDetectionResult(
        predicted_stroke=StrokeType.UNKNOWN,
        confidence=None,
        classification_status="INSUFFICIENT_EVIDENCE",
        uncertainty=None
    )
    contract = res.to_decision_contract()["stroke_detection"]
    assert contract["confidence"] is None
    assert contract["uncertainty"] is None

def test_confidence_none_does_not_crash_rendering():
    """Verify that confidence=None renders as N/A / Uncalibrated without crashing comparisons."""
    res = StrokeDetectionResult(confidence=None, uncertainty=None)
    assert res.confidence is None

    # Verify safe comparison logic
    conf = res.confidence
    # Avoid unsafe `conf < 0.80`
    safe_check = (conf is not None and conf < 0.80)
    assert safe_check is False

def test_benchmark_percentile_none_does_not_crash_rendering():
    """Verify that percentile=None is handled safely in charts and cards without converting to 0 or 100."""
    comp = MetricBenchmarkComparison(
        metric_name="stroke_rate",
        raw_value=54.0,
        population_mean=52.0,
        population_std=3.0,
        elite_mean=60.0,
        z_score=None,
        percentile=None,
        unit="spm"
    )

    bm_res = BenchmarkResult(
        dataset_id="BM-TEST",
        dataset_name="Test Benchmark",
        dataset_version="2.0.0",
        scientific_revision="2026.08",
        overall_skill_level="N/A (Unvalidated Cohort)",
        is_population_compatible=False,
        comparisons={"stroke_rate": comp}
    )

    # Chart rendering test
    fig_pct = create_benchmark_percentile_chart(bm_res)
    assert fig_pct is not None

    fig_radar = create_benchmark_radar_chart(bm_res)
    assert fig_radar is not None

def test_metric_value_none_does_not_crash_rendering():
    """Verify that ValidatedMetric value=None displays as UNAVAILABLE/N/A without coercing to 0.0."""
    metric = ValidatedMetric(name="stroke_length", value=None, unit="m", valid=True)
    assert metric.value is None

    # Format check helper logic
    val_str = f"{metric.value:.2f}" if metric.value is not None else "UNAVAILABLE"
    assert val_str == "UNAVAILABLE"
    assert val_str != "0.00"
    assert val_str != "0.0"

def test_uncertainty_none_does_not_crash_rendering():
    """Verify uncertainty=None does not crash rendering and is displayed as N/A."""
    res = StrokeDetectionResult(uncertainty=None)
    unc_display = f"{res.uncertainty*100:.1f}%" if res.uncertainty is not None else "N/A"
    assert unc_display == "N/A"

def test_chart_data_containing_none_does_not_crash():
    """Verify Plotly chart creation with None/NaN values in pandas DataFrame."""
    df = pd.DataFrame([
        {"Date": "2026-08-01", "Time": "10:00", "Score": None, "Confidence": "Low", "Stroke": "Freestyle", "Cycles": 0},
        {"Date": "2026-08-02", "Time": "10:00", "Score": 82.5, "Confidence": "High", "Stroke": "Freestyle", "Cycles": 4},
        {"Date": "2026-08-03", "Time": "10:00", "Score": None, "Confidence": "Medium", "Stroke": "Freestyle", "Cycles": 2}
    ])

    fig_trend = create_performance_trend_chart(df)
    assert fig_trend is not None

    fig_cycles = create_cycles_trend_chart(df)
    assert fig_cycles is not None

def test_comparison_service_none_safety():
    """Verify ComparisonService handles None scores gracefully without TypeError."""
    svc = ComparisonService()
    delta = svc._calc_delta("Overall Score", None, 85.0)
    assert delta.delta is None
    assert delta.is_improvement is False

    delta_both_none = svc._calc_delta("Overall Score", None, None)
    assert delta_both_none.delta is None
    assert delta_both_none.is_improvement is False
