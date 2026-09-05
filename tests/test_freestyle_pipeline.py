import pytest
import cv2
import numpy as np
from pathlib import Path

from services.analysis_service import AnalysisService
from models.data_models import StrokeDetectionResult, StrokeType

@pytest.fixture
def mock_video():
    """Creates a 5-second synthetic video (color gradient, no swimmer) for stability testing."""
    test_video_path = "test_stability_video.mp4"
    width, height = 854, 480
    fps = 30
    duration = 5
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(test_video_path, fourcc, fps, (width, height))

    for i in range(fps * duration):
        frame = np.full((height, width, 3), (100, 150, (i * 5) % 255), dtype=np.uint8)
        out.write(frame)

    out.release()
    yield test_video_path

    import gc
    gc.collect()
    if Path(test_video_path).exists():
        try:
            Path(test_video_path).unlink()
        except Exception:
            pass


def test_freestyle_pipeline_stability(mock_video):
    """
    Test that the pipeline processes a synthetic video without crashing.

    Since the synthetic video contains no swimmer, MediaPipe produces zero valid frames.
    The pipeline must:
    - Not raise any exception
    - Return an AnalysisResult (never None)
    - Set vqa_result.quality_class == 'Critical' (insufficient frames policy)
    - Return report=None (zero-fallback: no data -> no fabricated score)
    - Return empty output paths ("") per the early-halt insufficient-frames policy

    Per the zero-fallback scientific policy: report=None is CORRECT when no valid
    pose frames are detected. This test validates that behavior, not that a report
    is generated from a no-data video.
    """
    service = AnalysisService()
    stroke_det = StrokeDetectionResult(
        predicted_stroke=StrokeType.FREESTYLE,
        selected_stroke=StrokeType.FREESTYLE,
        confidence=1.0,
        manual_override=False,
        predictions={}
    )

    output_video_path, json_report, metadata_path, result = service.process_video(
        input_video_path=mock_video,
        effective_fps=30.0,
        visualization_mode="Developer Mode",
        stroke_detection=stroke_det
    )

    # Pipeline must never crash — result is always returned
    assert result is not None
    assert result.video_path == mock_video

    # Synthetic video: zero valid frames -> insufficient evidence path
    # VQA must be set to Critical
    assert result.vqa_result is not None
    assert result.vqa_result.quality_class == "Critical"

    # Zero-fallback policy: report must be None when no valid frames were detected
    # (not fabricated from zero-data)
    assert result.report is None, (
        f"Expected report=None for a no-pose video (zero-fallback policy), "
        f"got overall_score={result.report.overall_score if result.report else 'N/A'}"
    )

    # Early-halt policy: output paths are empty strings, not broken file paths
    assert output_video_path == ""
    assert json_report == ""
    assert metadata_path == ""
