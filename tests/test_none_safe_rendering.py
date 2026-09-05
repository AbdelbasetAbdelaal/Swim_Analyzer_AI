"""Regression coverage for presentation consumers of P0 unavailable values."""
import ast
from pathlib import Path

from analysis.benchmarks.benchmark_engine import BenchmarkEngine
from app.ui.charts import create_bell_curve_chart, create_benchmark_percentile_chart
from models.benchmark_models import BenchmarkResult, MetricBenchmarkComparison
from models.data_models import AnalysisResult, ConsistencyReport, PerformanceReport, ReliabilityResult, ValidatedMetric


class _Container:
    def __init__(self, sink):
        self.sink = sink

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def metric(self, *args, **kwargs):
        self.sink.append(args)

    def markdown(self, *args, **kwargs):
        self.sink.append(args)


class _StreamlitRecorder(_Container):
    def container(self, **kwargs):
        return _Container(self.sink)

    def columns(self, count):
        return [_Container(self.sink) for _ in range(count)]


def _load_executive_card():
    """Load only the rendering function, avoiding Streamlit's module-level app run."""
    source_path = Path(__file__).parents[1] / "app" / "ui" / "tabs" / "summary_tab.py"
    if not source_path.exists():
        source_path = Path(__file__).parents[1] / "app" / "streamlit_app.py"
    module = ast.parse(source_path.read_text(encoding="utf-8"))
    function = next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == "render_executive_summary_card")
    recorder = _StreamlitRecorder([])
    namespace = {"st": recorder}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(source_path), "exec"), namespace)
    return namespace["render_executive_summary_card"], recorder


def _result(score, metric_value=None, metric_status="unavailable", confidence="Low"):
    report = PerformanceReport(
        overall_score=score,
        status="insufficient_evidence" if score is None else "available",
        stroke_rate=ValidatedMetric(value=metric_value, valid=metric_value is not None, status=metric_status),
        stroke_length=ValidatedMetric(value=metric_value, valid=metric_value is not None, status=metric_status),
        stroke_symmetry=ValidatedMetric(value=metric_value, valid=metric_value is not None, status=metric_status),
    )
    return AnalysisResult(
        report=report,
        consistency=ConsistencyReport(overall_score=score, scientific_confidence=confidence),
        reliability=ReliabilityResult(analysis_reliability_score=35.0, analysis_confidence_score=40.0),
    )


def test_executive_card_renders_numeric_score():
    render, _ = _load_executive_card()
    render(_result(82.5, metric_value=54.0, metric_status="available", confidence="High"))


def test_executive_card_regression_none_score_and_metric_do_not_compare_to_float():
    """Reproduces the former `None > float` failure in the Top Strengths card."""
    render, recorder = _load_executive_card()
    render(_result(None, metric_value=None, metric_status="unavailable", confidence="Inconclusive"))
    assert any("INSUFFICIENT_EVIDENCE" in str(args) for args in recorder.sink)


def test_charts_render_insufficient_evidence_without_synthetic_percentile():
    comp = MetricBenchmarkComparison(
        metric_name="stroke_rate", raw_value=54.0, population_mean=None,
        population_std=None, z_score=None, percentile=None, elite_mean=None,
        elite_delta=None, skill_level=None, unit="spm",
    )
    result = BenchmarkResult(overall_skill_level="INSUFFICIENT_EVIDENCE", comparisons={"stroke_rate": comp})
    assert create_benchmark_percentile_chart(result).layout.annotations
    assert create_bell_curve_chart("stroke_rate", 54.0, None, None, None).layout.annotations


def test_benchmark_public_consumers_preserve_unavailable_values():
    engine = BenchmarkEngine()
    comparison = engine.compare_with_population("stroke_rate", None)
    elite = engine.compare_with_elite("stroke_rate", None)
    assert comparison["z_score"] is None
    assert comparison["percentile"] is None
    assert elite["delta"] is None
    assert elite["pct_of_elite"] is None


def test_low_confidence_result_remains_numeric_when_measured():
    render, recorder = _load_executive_card()
    render(_result(61.0, metric_value=42.0, metric_status="low_confidence", confidence="Low"))
    assert any("61.0/100" in str(args) for args in recorder.sink)
