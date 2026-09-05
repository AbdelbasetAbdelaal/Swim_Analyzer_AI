import pytest
from pathlib import Path
from models.data_models import (
    AnalysisResult, StrokeSelection, StrokeType, PerformanceReport, ValidatedMetric, VideoMetadata
)
from services.analysis_service import AnalysisService
from services.export_service import ExportService
from services.benchmark_service import BenchmarkService

def test_session_isolation_between_consecutive_runs():
    """Verify that analyzing Video A (Freestyle) and Video B (Butterfly) maintains strict artifact and state isolation."""
    export_service = ExportService()
    benchmark_service = BenchmarkService()

    # Session 1: Video A / Freestyle
    res_a = AnalysisResult(video_path="video_a.mp4")
    res_a.stroke_type = "Freestyle"
    res_a.stroke_selection = StrokeSelection(selected_stroke=StrokeType.FREESTYLE, selection_source="USER")
    res_a.report = PerformanceReport(overall_score=82.0, stroke_rate=ValidatedMetric(value=54.0, valid=True))
    benchmark_service.evaluate_session(res_a)
    
    meta_a = VideoMetadata(filename="video_a.mp4", swimming_style="Freestyle", stroke_detection=res_a.stroke_selection)
    rep_a, m_path_a, _ = export_service.export_to_json(res_a, meta_a, "video_a.mp4")

    # Session 2: Video B / Butterfly
    res_b = AnalysisResult(video_path="video_b.mp4")
    res_b.stroke_type = "Butterfly"
    res_b.stroke_selection = StrokeSelection(selected_stroke=StrokeType.BUTTERFLY, selection_source="USER")
    res_b.report = PerformanceReport(overall_score=89.0, stroke_rate=ValidatedMetric(value=52.0, valid=True))
    benchmark_service.evaluate_session(res_b)
    
    meta_b = VideoMetadata(filename="video_b.mp4", swimming_style="Butterfly", stroke_detection=res_b.stroke_selection)
    rep_b, m_path_b, _ = export_service.export_to_json(res_b, meta_b, "video_b.mp4")

    # Verify Strict Isolation
    assert rep_a != rep_b
    assert m_path_a != m_path_b
    assert res_a.benchmark_result.dataset_id == "BM-FRE-2026"
    assert res_b.benchmark_result.dataset_id == "BM-BUT-2026"
    assert res_a.stroke_type == "Freestyle"
    assert res_b.stroke_type == "Butterfly"

def test_vqa_warning_state_in_results():
    """Verify that Poor VQA state is deterministically marked in analysis result."""
    from models.data_models import VQAResult
    from analysis.consistency_validator import AnalysisConsistencyValidator
    
    res = AnalysisResult(video_path="poor_video.mp4")
    res.stroke_type = "Freestyle"
    res.stroke_selection = StrokeSelection(selected_stroke=StrokeType.FREESTYLE, selection_source="USER")
    res.vqa_result = VQAResult(
        overall_score=48,
        analysis_confidence="Low",
        quality_class="Poor",
        passed=True,
        warning_message="Video quality is poor."
    )
    res.report = PerformanceReport(overall_score=75.0)

    report = AnalysisConsistencyValidator.validate(res)

    assert report.validation_status in ["Warning", "Inconclusive"]
    assert report.scientific_confidence in ["Low", "Medium", "Inconclusive"]
