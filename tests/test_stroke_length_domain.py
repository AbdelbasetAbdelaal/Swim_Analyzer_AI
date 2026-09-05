"""
Tests for Stroke Length Unit and Measurement Domain (P0-3).
Verifies:
1. Relative body length metric is rejected from meter benchmark comparison.
2. Z-score and percentile are None when domains are incompatible.
3. MetricBenchmarkComparison has comparison_status='incompatible_domain'.
4. Calibrated physical meters metric is accepted for meter benchmark comparison.
"""

import pytest
from analysis.benchmarks.benchmark_engine import BenchmarkEngine
from models.data_models import AnalysisResult, PerformanceReport, ValidatedMetric
from models.athlete_profile import AthleteProfile

def test_relative_stroke_length_rejected_against_meters_benchmark():
    engine = BenchmarkEngine()
    ar = AnalysisResult()
    ar.stroke_type = "Freestyle"
    # Uncalibrated relative metric in body_length
    ar.report = PerformanceReport(
        overall_score=85.0,
        stroke_length=ValidatedMetric(
            name="stroke_length",
            value=0.85,
            unit="body_length",
            measurement_domain="relative_body_normalized",
            valid=True
        )
    )
    prof = AthleteProfile(coach_id="c1", full_name="Swimmer", age=22, gender="Male", height_cm=180.0, weight_kg=75.0, swimming_level="Advanced", preferred_stroke="Freestyle")
    res = engine.evaluate_analysis(ar, prof)

    assert "stroke_length" in res.comparisons
    comp = res.comparisons["stroke_length"]

    assert comp.comparison_status == "incompatible_domain"
    assert comp.z_score is None
    assert comp.percentile is None
    assert comp.population_mean is None
    assert comp.unit == "body_length"
    assert "Cannot compare relative body length" in comp.reason

def test_calibrated_stroke_length_accepted_for_meters_benchmark():
    engine = BenchmarkEngine()
    ar = AnalysisResult()
    ar.stroke_type = "Freestyle"
    # Calibrated physical metric in meters
    ar.report = PerformanceReport(
        overall_score=85.0,
        stroke_length=ValidatedMetric(
            name="stroke_length",
            value=1.85,
            unit="m",
            measurement_domain="calibrated_physical",
            valid=True
        )
    )
    prof = AthleteProfile(coach_id="c1", full_name="Swimmer", age=22, gender="Male", height_cm=180.0, weight_kg=75.0, swimming_level="Advanced", preferred_stroke="Freestyle")
    res = engine.evaluate_analysis(ar, prof)

    assert "stroke_length" in res.comparisons
    comp = res.comparisons["stroke_length"]
    # Should not be flagged as incompatible domain
    assert comp.comparison_status != "incompatible_domain"
    assert comp.unit == "m"
