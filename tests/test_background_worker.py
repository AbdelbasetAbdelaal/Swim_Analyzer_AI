"""
Unit tests for BackgroundAnalysisWorker.
"""
import time
from unittest.mock import MagicMock
from services.background_analysis_worker import BackgroundAnalysisWorker, JobStatus

def test_background_worker_lifecycle():
    mock_service = MagicMock()
    mock_service.process_video.return_value = {"status": "success", "session_id": "test-123"}

    mock_athlete = MagicMock()
    mock_athlete.name = "Test Swimmer"

    job_id = BackgroundAnalysisWorker.submit_job(
        video_path="dummy.mp4",
        athlete_profile=mock_athlete,
        coach_id="coach-1",
        stroke_type="Freestyle",
        analysis_service=mock_service
    )

    assert job_id is not None
    
    # Wait for thread to complete
    for _ in range(50):
        job = BackgroundAnalysisWorker.get_job(job_id)
        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
            break
        time.sleep(0.05)

    assert job.status == JobStatus.COMPLETED
    assert job.result == {"status": "success", "session_id": "test-123"}
    assert job.progress == 1.0
