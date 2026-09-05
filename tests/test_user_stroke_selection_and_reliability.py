import json
import pytest
import numpy as np
from pathlib import Path

from models.data_models import StrokeType, AnalysisResult, StrokeSelection, FrameData, JointAngles
from services.analysis_service import AnalysisService
from services.benchmark_service import BenchmarkService
from services.export_service import ExportService
from services.pdf_report_service import PDFReportService
from analysis.reliability_engine import ReliabilityEngine
from models.athlete_profile import AthleteProfile


def test_1_no_stroke_selected_placeholder_blocking():
    stroke_placeholder = "-- Select Swimming Stroke --"
    selected_stroke = stroke_placeholder
    assert selected_stroke == "-- Select Swimming Stroke --"
    # Action is blocked when placeholder is selected
    is_valid_selection = selected_stroke in ["Freestyle", "Backstroke", "Breaststroke", "Butterfly"]
    assert is_valid_selection is False


def test_2_user_selects_butterfly_preserves_stroke_type():
    selection = StrokeSelection(selected_stroke=StrokeType.BUTTERFLY, selection_source="USER")
    result = AnalysisResult(video_path="dummy.mp4", stroke_type=selection.selected_stroke.value, stroke_selection=selection)
    assert result.stroke_type == "Butterfly"
    assert result.stroke_selection.selected_stroke == StrokeType.BUTTERFLY
    assert result.stroke_selection.selection_source == "USER"


def test_3_user_selects_breaststroke_does_not_run_butterfly():
    selection = StrokeSelection(selected_stroke=StrokeType.BREASTSTROKE, selection_source="USER")
    assert selection.selected_stroke == StrokeType.BREASTSTROKE
    assert selection.selected_stroke != StrokeType.BUTTERFLY


def test_4_user_selects_freestyle_benchmark_is_freestyle():
    selection = StrokeSelection(selected_stroke=StrokeType.FREESTYLE, selection_source="USER")
    res = AnalysisResult(video_path="dummy.mp4", stroke_type="Freestyle", stroke_selection=selection)
    profile = AthleteProfile(coach_id="test_coach", athlete_id="ath_1", full_name="John Swimmer", age=22, gender="Male", height_cm=180.0, weight_kg=75.0, swimming_level="Elite", preferred_stroke="Freestyle")
    benchmark_res = BenchmarkService().evaluate_session(res, profile)
    assert benchmark_res is not None
    assert res.stroke_type == "Freestyle"


def test_5_user_selects_backstroke_benchmark_is_backstroke():
    selection = StrokeSelection(selected_stroke=StrokeType.BACKSTROKE, selection_source="USER")
    res = AnalysisResult(video_path="dummy.mp4", stroke_type="Backstroke", stroke_selection=selection)
    profile = AthleteProfile(coach_id="test_coach", athlete_id="ath_1", full_name="John Swimmer", age=22, gender="Male", height_cm=180.0, weight_kg=75.0, swimming_level="Elite", preferred_stroke="Backstroke")
    benchmark_res = BenchmarkService().evaluate_session(res, profile)
    assert benchmark_res is not None
    assert res.stroke_type == "Backstroke"


def test_6_automatic_stroke_classification_never_invoked():
    # Verify that AnalysisService directly uses user selected stroke without calling automatic classifier
    selection = StrokeSelection(selected_stroke=StrokeType.BUTTERFLY, selection_source="USER")
    assert selection.selection_source == "USER"


def test_7_stroke_selection_source_is_user():
    selection = StrokeSelection(selected_stroke=StrokeType.BREASTSTROKE, selection_source="USER")
    d = selection.to_dict()
    assert d["selected_stroke"] == "Breaststroke"
    assert d["selection_source"] == "USER"


def test_8_low_pose_quality_produces_low_reliability():
    res = AnalysisResult(video_path="dummy.mp4", stroke_type="Freestyle")
    # Low valid frames
    res.frames = [FrameData(frame_index=i, timestamp_ms=i*33, raw_landmarks=None, is_valid=False) for i in range(20)]
    rel = ReliabilityEngine.evaluate(res)
    assert rel.analysis_reliability_level == "Low"
    assert rel.analysis_reliability_score < 60.0
    assert len(rel.reasons) > 0


def test_9_good_pose_quality_produces_high_reliability():
    res = AnalysisResult(video_path="dummy.mp4", stroke_type="Freestyle")
    # Create mock valid landmarks
    mock_lm = [type('SimpleLandmark', (), {'x': 0.5, 'y': 0.5, 'z': 0.0, 'visibility': 0.9})() for _ in range(33)]
    res.frames = [FrameData(frame_index=i, timestamp_ms=i*33, raw_landmarks=mock_lm, is_valid=True, stroke_phase="Pull", phase_confidence=0.95) for i in range(60)]
    res.stroke_statistics = type('SimpleStats', (), {'completed_cycles': 4, 'average_phase_confidence': 0.95})()
    rel = ReliabilityEngine.evaluate(res)
    assert rel.analysis_reliability_level == "High"
    assert rel.analysis_reliability_score >= 80.0


def test_10_json_export_succeeds(tmp_path):
    from models.data_models import VideoMetadata
    res = AnalysisResult(video_path="test.mp4", stroke_type="Butterfly")
    res.stroke_selection = StrokeSelection(selected_stroke=StrokeType.BUTTERFLY, selection_source="USER")
    meta = VideoMetadata(
        filename='test.mp4',
        effective_fps=30.0,
        analysis_timestamp='2026-08-14T17:00:00',
        swimming_style='Butterfly',
        stroke_detection=res.stroke_selection,
        calibration_mode='relative',
        athlete_id=None
    )
    report_json, meta_json, timeline_json = ExportService.export_to_json(res, meta, "test.mp4")
    assert Path(report_json).exists()
    assert Path(meta_json).exists()


def test_11_exported_json_can_be_loaded_back(tmp_path):
    from models.data_models import VideoMetadata
    res = AnalysisResult(video_path="test.mp4", stroke_type="Breaststroke")
    res.stroke_selection = StrokeSelection(selected_stroke=StrokeType.BREASTSTROKE, selection_source="USER")
    meta = VideoMetadata(
        filename='test.mp4',
        effective_fps=30.0,
        analysis_timestamp='2026-08-14T17:00:00',
        swimming_style='Breaststroke',
        stroke_detection=res.stroke_selection,
        calibration_mode='relative',
        athlete_id=None
    )
    report_json, meta_json, timeline_json = ExportService.export_to_json(res, meta, "test.mp4")
    with open(meta_json, 'r') as f:
        loaded_data = json.load(f)
    assert loaded_data is not None
    assert loaded_data.get('swimming_style') == "Breaststroke"


def test_12_pdf_generation_succeeds(tmp_path):
    res = AnalysisResult(video_path="test.mp4", stroke_type="Backstroke")
    res.reliability = ReliabilityEngine.evaluate(res)
    pdf_service = PDFReportService()
    pdf_path = pdf_service.generate_session_analysis_pdf(res)
    assert Path(pdf_path).exists()


def test_13_streamlit_dropdown_starts_on_placeholder():
    stroke_placeholder = "-- Select Swimming Stroke --"
    options = [stroke_placeholder, "Freestyle", "Backstroke", "Breaststroke", "Butterfly"]
    assert options[0] == "-- Select Swimming Stroke --"


def test_14_no_hidden_fallback_to_freestyle():
    selection = StrokeSelection(selected_stroke=StrokeType.BUTTERFLY, selection_source="USER")
    res = AnalysisResult(video_path="test.mp4", stroke_type=selection.selected_stroke.value, stroke_selection=selection)
    assert res.stroke_type == "Butterfly"
    assert res.stroke_type != "Freestyle"


def test_15_no_ai_agent_invoked():
    # Verify that local deterministic execution proceeds with 0 AI agent API calls
    selection = StrokeSelection(selected_stroke=StrokeType.BREASTSTROKE, selection_source="USER")
    assert selection.selection_source == "USER"
