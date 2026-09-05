import pytest
from models.athlete_profile import AthleteProfile
from models.analysis_session import AnalysisSession

def test_athlete_profile_requires_coach_id():
    with pytest.raises(TypeError) as excinfo:
        AthleteProfile(full_name="Test", age=20, gender="Male", height_cm=180, weight_kg=80, swimming_level="Pro", preferred_stroke="Free")
    assert "coach_id" in str(excinfo.value)

def test_analysis_session_requires_account_id():
    with pytest.raises(TypeError) as excinfo:
        AnalysisSession(
            athlete_id="user_123",
            analysis_timestamp="2026-08-01T12:00:00",
            original_video_filename="a.mp4",
            processed_video_filename="b.mp4",
            metadata_json_path="c.json",
            report_json_path="d.json",
            performance_score=80.0,
            scientific_confidence="High",
            completed_cycles=1,
            stroke_type="Freestyle",
            processing_time_seconds=10.0
        )
    assert "account_id" in str(excinfo.value)

def test_analysis_service_requires_coach_id_for_athlete_profile():
    from services.analysis_service import AnalysisService
    from unittest.mock import MagicMock

    svc = AnalysisService()
    dummy_result = MagicMock()
    dummy_result.frames = []
    dummy_result.vqa_result = None
    dummy_meta = MagicMock()
    dummy_meta.duration_seconds = 10.0
    dummy_meta.effective_fps = 30.0
    dummy_analyzer = MagicMock()
    dummy_analyzer.completed_cycles = 0
    dummy_analyzer.time_in_phases = {}
    dummy_analyzer.transitions = []
    dummy_calc = MagicMock()
    dummy_scoring = MagicMock()
    dummy_scoring.generate_report.return_value = MagicMock(overall_score=80.0, errors=[])
    dummy_calib = MagicMock()
    dummy_processor = MagicMock()
    dummy_processor.width = 640
    dummy_processor.height = 480

    # 1. Athlete ID provided without coach_id must raise ValueError
    with pytest.raises(ValueError) as excinfo:
        svc._finalize_metrics_and_export(
            dummy_result, dummy_meta, dummy_analyzer, dummy_calc, dummy_scoring,
            dummy_calib, dummy_processor, "test.mp4", "out.mp4",
            athlete_id="ath_123", coach_id=None
        )
    assert "coach_id is required" in str(excinfo.value)

def test_analysis_service_coach_athlete_tenant_isolation():
    from services.analysis_service import AnalysisService
    from services.athlete_service import AthleteService
    from unittest.mock import patch, MagicMock

    svc = AnalysisService()
    dummy_result = MagicMock()
    dummy_result.frames = []
    dummy_result.vqa_result = None
    dummy_meta = MagicMock()
    dummy_meta.duration_seconds = 10.0
    dummy_meta.effective_fps = 30.0
    dummy_analyzer = MagicMock()
    dummy_analyzer.completed_cycles = 0
    dummy_analyzer.time_in_phases = {}
    dummy_analyzer.transitions = []
    dummy_calc = MagicMock()
    dummy_scoring = MagicMock()
    dummy_scoring.generate_report.return_value = MagicMock(overall_score=80.0, errors=[])
    dummy_calib = MagicMock()
    dummy_processor = MagicMock()
    dummy_processor.width = 640
    dummy_processor.height = 480

    with patch.object(AthleteService, 'load_profile') as mock_load, \
         patch('services.export_service.ExportService.export_to_json', return_value=("", "", "")), \
         patch('utils.video_utils.VideoProcessor.validate_export', return_value=True):

        # Setup: Coach A owns athlete_1, but Coach B does not
        athlete_profile_a = AthleteProfile(
            athlete_id="ath_1",
            coach_id="coach_a",
            full_name="Alex Swimmer",
            age=20,
            gender="Male",
            height_cm=180.0,
            weight_kg=75.0,
            swimming_level="Elite",
            preferred_stroke="Freestyle"
        )
        mock_load.side_effect = lambda athlete_id, coach_id: (
            athlete_profile_a if (athlete_id == "ath_1" and coach_id == "coach_a") else None
        )

        # Coach A analyzing own athlete succeeds
        svc._finalize_metrics_and_export(
            dummy_result, dummy_meta, dummy_analyzer, dummy_calc, dummy_scoring,
            dummy_calib, dummy_processor, "test.mp4", "out.mp4",
            athlete_id="ath_1", coach_id="coach_a"
        )
        mock_load.assert_called_with(athlete_id="ath_1", coach_id="coach_a")

        # Coach B analyzing Coach A athlete gets None profile (no cross-tenant leakage)
        mock_load.reset_mock()
        svc._finalize_metrics_and_export(
            dummy_result, dummy_meta, dummy_analyzer, dummy_calc, dummy_scoring,
            dummy_calib, dummy_processor, "test.mp4", "out.mp4",
            athlete_id="ath_1", coach_id="coach_b"
        )
        mock_load.assert_called_with(athlete_id="ath_1", coach_id="coach_b")
