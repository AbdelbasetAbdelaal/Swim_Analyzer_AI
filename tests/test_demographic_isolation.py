"""
Tests for Benchmark Demographic and Cohort Isolation (P0-5).
Verifies:
1. Youth athletes (U10, U13, U17) never fall back to adult benchmarks without explicit youth evidence.
2. Cross-sex fallback is rejected (Male does not fall back to Female, Female does not fall back to Male).
3. Unvalidated cohort results in validation_status='unvalidated_cohort' and overall_skill_level='N/A (Unvalidated Cohort)'.
4. Percentile, z_score, and elite_delta are None for unvalidated cohorts.
"""

import pytest
from analysis.benchmarks.benchmark_engine import BenchmarkEngine
from models.data_models import AnalysisResult, PerformanceReport, ValidatedMetric
from models.athlete_profile import AthleteProfile
from models.scientific_evidence_models import ValidationStatus

def test_youth_athlete_never_receives_adult_benchmarks():
    engine = BenchmarkEngine()
    ar = AnalysisResult()
    ar.stroke_type = "Freestyle"
    ar.report = PerformanceReport(
        overall_score=80.0,
        stroke_rate=ValidatedMetric(value=50.0, valid=True)
    )
    # 9-year-old youth athlete (U10)
    youth_prof = AthleteProfile(
        coach_id="c1", full_name="Junior", age=9, gender="Male",
        height_cm=135.0, weight_kg=30.0, swimming_level="Intermediate", preferred_stroke="Freestyle"
    )
    res = engine.evaluate_analysis(ar, youth_prof)

    assert res.is_population_compatible is False
    assert res.validation_status == "unvalidated_cohort"
    assert res.overall_skill_level == "N/A (Unvalidated Cohort)"

    sr_comp = res.comparisons.get("stroke_rate")
    assert sr_comp is not None
    assert sr_comp.z_score is None
    assert sr_comp.percentile is None
    assert sr_comp.population_mean is None

def test_cross_sex_fallback_rejected():
    engine = BenchmarkEngine()
    # Query Backstroke for Female when backstroke.yaml only has Male
    stats = engine._get_population_stats("Backstroke", "18-25", "Female", "stroke_rate")
    # Female should NOT receive Male's benchmark (mean=48.0)
    assert stats.mean is None
    assert stats.evidence.validation_status == ValidationStatus.INSUFFICIENT_EVIDENCE

def test_unvalidated_cohort_suppresses_statistical_metrics():
    engine = BenchmarkEngine()
    ar = AnalysisResult()
    ar.stroke_type = "Breaststroke"
    ar.report = PerformanceReport(
        overall_score=75.0,
        stroke_rate=ValidatedMetric(value=42.0, valid=True)
    )
    # Masters athlete (Age 55) where no Masters cohort exists
    masters_prof = AthleteProfile(
        coach_id="c1", full_name="Veteran", age=55, gender="Male",
        height_cm=175.0, weight_kg=78.0, swimming_level="Advanced", preferred_stroke="Breaststroke"
    )
    res = engine.evaluate_analysis(ar, masters_prof)

    assert res.is_population_compatible is False
    assert res.validation_status == "unvalidated_cohort"
    assert res.overall_skill_level == "N/A (Unvalidated Cohort)"

    sr_comp = res.comparisons.get("stroke_rate")
    assert sr_comp is not None
    assert sr_comp.z_score is None
    assert sr_comp.percentile is None
    assert sr_comp.elite_delta is None
