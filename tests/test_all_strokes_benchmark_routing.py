import pytest
from models.data_models import (
    AnalysisResult, StrokeSelection, StrokeType, PerformanceReport, ValidatedMetric
)
from models.athlete_profile import AthleteProfile
from analysis.benchmarks.benchmark_engine import BenchmarkEngine
from services.benchmark_service import BenchmarkService
from services.export_service import ExportService
from models.data_models import VideoMetadata

def test_benchmark_routing_freestyle():
    engine = BenchmarkEngine()
    result = AnalysisResult(video_path="test_video.mp4")
    result.stroke_type = "Freestyle"
    result.stroke_selection = StrokeSelection(selected_stroke=StrokeType.FREESTYLE, selection_source="USER")
    result.report = PerformanceReport(
        overall_score=85.0,
        stroke_rate=ValidatedMetric(value=54.0, valid=True)
    )
    
    bm_res = engine.evaluate_analysis(result)
    assert bm_res.stroke_type == "Freestyle"
    assert "Freestyle" in bm_res.dataset_name
    assert bm_res.dataset_id == "BM-FRE-2026"

def test_benchmark_routing_backstroke():
    engine = BenchmarkEngine()
    result = AnalysisResult(video_path="test_video.mp4")
    result.stroke_type = "Backstroke"
    result.stroke_selection = StrokeSelection(selected_stroke=StrokeType.BACKSTROKE, selection_source="USER")
    result.report = PerformanceReport(
        overall_score=88.0,
        stroke_rate=ValidatedMetric(value=46.0, valid=True)
    )
    
    bm_res = engine.evaluate_analysis(result)
    assert bm_res.stroke_type == "Backstroke"
    assert "Backstroke" in bm_res.dataset_name
    assert bm_res.dataset_id == "BM-BAC-2026"

def test_benchmark_routing_breaststroke():
    engine = BenchmarkEngine()
    result = AnalysisResult(video_path="test_video.mp4")
    result.stroke_type = "Breaststroke"
    result.stroke_selection = StrokeSelection(selected_stroke=StrokeType.BREASTSTROKE, selection_source="USER")
    result.report = PerformanceReport(
        overall_score=78.0,
        stroke_rate=ValidatedMetric(value=40.0, valid=True)
    )
    
    bm_res = engine.evaluate_analysis(result)
    assert bm_res.stroke_type == "Breaststroke"
    assert "Breaststroke" in bm_res.dataset_name
    assert bm_res.dataset_id == "BM-BRE-2026"

def test_benchmark_routing_butterfly():
    engine = BenchmarkEngine()
    result = AnalysisResult(video_path="test_video.mp4")
    result.stroke_type = "Butterfly"
    result.stroke_selection = StrokeSelection(selected_stroke=StrokeType.BUTTERFLY, selection_source="USER")
    result.report = PerformanceReport(
        overall_score=92.0,
        stroke_rate=ValidatedMetric(value=52.0, valid=True)
    )
    
    bm_res = engine.evaluate_analysis(result)
    assert bm_res.stroke_type == "Butterfly"
    assert "Butterfly" in bm_res.dataset_name
    assert bm_res.dataset_id == "BM-BUT-2026"

def test_benchmark_service_attaches_correct_stroke_dataset():
    service = BenchmarkService()
    for stroke_enum, stroke_str in [
        (StrokeType.FREESTYLE, "Freestyle"),
        (StrokeType.BACKSTROKE, "Backstroke"),
        (StrokeType.BREASTSTROKE, "Breaststroke"),
        (StrokeType.BUTTERFLY, "Butterfly")
    ]:
        result = AnalysisResult(video_path="dummy.mp4")
        result.stroke_type = stroke_str
        result.stroke_selection = StrokeSelection(selected_stroke=stroke_enum, selection_source="USER")
        result.report = PerformanceReport(
            overall_score=90.0,
            stroke_rate=ValidatedMetric(value=50.0, valid=True)
        )
        
        bm_res = service.evaluate_session(result)
        assert result.benchmark_result is not None
        assert result.benchmark_result.stroke_type == stroke_str
        assert stroke_str in result.benchmark_result.dataset_name

def test_export_service_includes_stroke_fields():
    import json
    result = AnalysisResult(video_path="dummy.mp4")
    result.stroke_type = "Butterfly"
    result.stroke_selection = StrokeSelection(selected_stroke=StrokeType.BUTTERFLY, selection_source="USER")
    result.report = PerformanceReport(overall_score=95.0)
    
    metadata = VideoMetadata(filename="dummy.mp4", swimming_style="Butterfly", stroke_detection=result.stroke_selection)
    
    report_path, meta_path, timeline_path = ExportService.export_to_json(result, metadata, "dummy.mp4")
    
    with open(report_path, "r") as f:
        data = json.load(f)
    assert data["stroke_type"] == "Butterfly"
    assert data["stroke_selection"]["selected_stroke"] == "Butterfly"
    assert data["stroke_selection"]["selection_source"] == "USER"
