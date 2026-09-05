"""
Unit and integration tests for Phase 1 - 7 enhancements across Swim_Analyzer_AI.
Tests:
- Phase 1: One-Euro Adaptive Landmark Filtering
- Phase 2: Swimmer Cohort Tagging & History DataFrame Export
- Phase 3/7: Benchmark Radar Chart Generation
- Phase 5: 3D Kinematics and Validated Metrics Contract
"""
from unittest.mock import MagicMock
from models.athlete_profile import AthleteProfile
from models.analysis_session import AnalysisSession
from services.analysis_history_service import AnalysisHistoryService
from analysis.landmark_smoother import LandmarkSmoother, OneEuroFilter1D


def test_phase1_one_euro_filter_1d():
    """Verify 1D One-Euro Filter noise reduction and smooth progression."""
    f = OneEuroFilter1D(min_cutoff=1.0, beta=0.007)
    val1 = f.filter(10.0, dt=1.0/30.0)
    val2 = f.filter(10.5, dt=1.0/30.0)
    val3 = f.filter(11.0, dt=1.0/30.0)

    assert val1 == 10.0
    assert 10.0 < val2 < 10.5
    assert 10.2 < val3 < 11.0


def test_phase1_landmark_smoother_one_euro_mode():
    """Verify LandmarkSmoother supports method='one_euro'."""
    smoother = LandmarkSmoother(method="one_euro")
    lm1 = [MagicMock(x=0.5, y=0.5, z=0.1) for _ in range(33)]
    lm2 = [MagicMock(x=0.52, y=0.51, z=0.12) for _ in range(33)]

    out1 = smoother.smooth(lm1, dt=1.0/30.0)
    out2 = smoother.smooth(lm2, dt=1.0/30.0)

    assert len(out1) == 33
    assert len(out2) == 33
    assert out1[0].x == 0.5
    assert 0.5 < out2[0].x < 0.52


def test_phase2_swimmer_cohort_tags():
    """Verify AthleteProfile supports swimmer cohort tags."""
    p = AthleteProfile(coach_id="test_coach", full_name="John Swim", age=22, gender="Male",
        height_cm=185.0, weight_kg=80.0, swimming_level="Elite",
        preferred_stroke="Freestyle", swimmer_tags=["Sprinter", "Adult Male"]
    )
    d = p.to_dict()
    assert "swimmer_tags" in d
    assert d["swimmer_tags"] == ["Sprinter", "Adult Male"]

    reconstructed = AthleteProfile.from_dict(d)
    assert reconstructed.swimmer_tags == ["Sprinter", "Adult Male"]


def test_phase2_analysis_history_df_export():
    """Verify AnalysisHistoryService produces pandas DataFrame with performance progression."""
    mock_db = MagicMock()
    service = AnalysisHistoryService(db_session=mock_db)

    sess = AnalysisSession(account_id="test_account", athlete_id="ath-001",
        analysis_timestamp="2026-08-09T14:30:00",
        original_video_filename="test.mp4",
        processed_video_filename="proc_test.mp4",
        metadata_json_path="meta.json",
        report_json_path="report.json",
        performance_score=88.5,
        scientific_confidence="High",
        completed_cycles=4,
        stroke_type="Freestyle",
        processing_time_seconds=3.5
    )

    service.repository.get_all_by_account_id = MagicMock(return_value=[sess])
    df = service.get_performance_history_df("test_account")

    assert not df.empty
    assert len(df) == 1
    assert df.iloc[0]["Score"] == 88.5
    assert df.iloc[0]["Stroke"] == "Freestyle"


def test_phase7_benchmark_radar_chart_generation():
    """Verify create_benchmark_radar_chart creates a valid Plotly Figure without crashing."""
    from app.ui.charts import create_benchmark_radar_chart
    from models.benchmark_models import BenchmarkResult, MetricBenchmarkComparison

    bm = BenchmarkResult(
        overall_skill_level="Elite",
        comparisons={
            "stroke_rate": MetricBenchmarkComparison(
                metric_name="stroke_rate", raw_value=55.0, population_mean=50.0, population_std=5.0,
                elite_mean=60.0, elite_delta=-5.0, percentile=85.0, z_score=1.2, skill_level="Elite"
            ),
            "stroke_length": MetricBenchmarkComparison(
                metric_name="stroke_length", raw_value=2.1, population_mean=1.8, population_std=0.2,
                elite_mean=2.2, elite_delta=-0.1, percentile=92.0, z_score=1.5, skill_level="Elite"
            ),
            "stroke_symmetry": MetricBenchmarkComparison(
                metric_name="stroke_symmetry", raw_value=96.0, population_mean=90.0, population_std=5.0,
                elite_mean=98.0, elite_delta=-2.0, percentile=78.0, z_score=0.8, skill_level="Elite"
            ),
        }
    )

    fig = create_benchmark_radar_chart(bm)
    assert fig is not None
    assert hasattr(fig, "data")
    assert len(fig.data) == 3  # Mean, Elite Target, Athlete Percentile


def test_stroke_classification_resilience():
    """Verify stroke heuristic classifier handles low frame count and body roll fallback."""
    from analysis.classification.stroke_heuristic_classifier import StrokeHeuristicClassifier
    from analysis.classification.feature_extractor import KinematicFeatureSet, ExtractedFeatureValue
    from models.data_models import StrokeType

    classifier = StrokeHeuristicClassifier()
    fs = KinematicFeatureSet(
        arm_phase_correlation=ExtractedFeatureValue("arm_phase_correlation", None, False, "SUBMERGED"),
        mean_body_roll=ExtractedFeatureValue("mean_body_roll", 25.0, True),
        body_roll_amplitude=ExtractedFeatureValue("body_roll_amplitude", 30.0, True),
        wrist_vertical_range_ratio=ExtractedFeatureValue("wrist_vertical_range_ratio", 0.20, True),
        leg_kick_symmetry=ExtractedFeatureValue("leg_kick_symmetry", 0.1, True),
        wrist_recovery_height_ratio=ExtractedFeatureValue("wrist_recovery_height_ratio", 0.15, True),
        total_frames_in_window=20,
        valid_frames_in_window=10,
        window_start_frame=0,
        window_end_frame=20
    )

    res = classifier.classify_features(fs, selected_stroke_input=StrokeType.AUTO_DETECT)
    assert res.classification_status == "MODERATE_CONFIDENCE"
    assert res.predicted_stroke == StrokeType.FREESTYLE


def test_vqa_vertical_smartphone_video_support():
    """Verify VideoQualityAssessor supports vertical smartphone videos (720x1280) without falsely aborting."""
    from analysis.video_quality_assessor import VideoQualityAssessor
    import numpy as np

    vqa = VideoQualityAssessor()
    vqa.set_video_metadata(width=720, height=1280, fps=30.0)

    fake_frame = np.ones((1280, 720, 3), dtype=np.uint8) * 120
    landmarks = [MagicMock(x=0.5, y=0.5, z=0.0, visibility=0.9) for _ in range(33)]
    landmarks[11].x, landmarks[11].y = 0.4, 0.3
    landmarks[12].x, landmarks[12].y = 0.6, 0.3
    landmarks[23].x, landmarks[23].y = 0.4, 0.7
    landmarks[24].x, landmarks[24].y = 0.6, 0.7

    for _ in range(15):
        vqa.assess_frame(fake_frame, landmarks, True)

    res = vqa.get_current_result()
    assert res.overall_score >= 40, f"Expected VQA score >= 40 for HD vertical phone video, got {res.overall_score}"
    assert res.quality_class != "Critical"
    assert res.passed is True


