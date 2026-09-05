"""
Tests for BenchmarkEngine integration with reference database.
Asserts that missing benchmarks return value is None and status == INSUFFICIENT_EVIDENCE.
"""

from analysis.benchmarks.benchmark_engine import BenchmarkEngine
from models.scientific_evidence_models import ValidationStatus

def test_benchmark_engine_no_fabricated_fallbacks():
    engine = BenchmarkEngine()

    # Query a non-existent stroke or unavailable cohort
    stats = engine._get_population_stats(
        stroke_type="NonExistentStroke",
        age_group="18-25",
        gender="Male",
        metric_name="unknown_metric"
    )

    assert stats.mean is None, "Missing benchmark mean MUST be None, never 70.0 or 0.0"
    assert stats.std is None
    assert stats.elite_mean is None
    assert stats.evidence.validation_status == ValidationStatus.INSUFFICIENT_EVIDENCE
