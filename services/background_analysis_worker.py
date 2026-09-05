"""
Background Analysis Worker for SwimAnalyzer AI.
Executes long-running video analysis asynchronously without blocking UI interactions.
"""
import threading
import uuid
import time
from typing import Dict, Any, Optional, Callable
from enum import Enum
from core.logger import setup_logger

logger = setup_logger(__name__)

class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class BackgroundAnalysisJob:
    """Represents a single asynchronous video analysis job."""
    def __init__(self, job_id: str, video_path: str, athlete_profile: Any, coach_id: str, stroke_type: Any):
        self.job_id = job_id
        self.video_path = video_path
        self.athlete_profile = athlete_profile
        self.coach_id = coach_id
        self.stroke_type = stroke_type
        self.status = JobStatus.PENDING
        self.progress = 0.0
        self.progress_message = "Queued"
        self.result: Optional[Any] = None
        self.error: Optional[str] = None
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

class BackgroundAnalysisWorker:
    """Manages thread execution of background video analysis jobs."""
    
    _active_jobs: Dict[str, BackgroundAnalysisJob] = {}
    _lock = threading.Lock()

    @classmethod
    def submit_job(cls, video_path: str, athlete_profile: Any, coach_id: str, stroke_type: Any, analysis_service: Any) -> str:
        """Submits a new video analysis job to run in a background daemon thread."""
        job_id = str(uuid.uuid4())
        job = BackgroundAnalysisJob(job_id, video_path, athlete_profile, coach_id, stroke_type)
        
        with cls._lock:
            cls._active_jobs[job_id] = job

        def _worker_runner():
            job.status = JobStatus.RUNNING
            job.start_time = time.time()
            job.progress_message = "Initializing analysis models..."
            
            def _progress_cb(pct: float, msg: str):
                job.progress = pct
                job.progress_message = msg

            try:
                result = analysis_service.process_video(
                    video_path=video_path,
                    athlete_profile=athlete_profile,
                    coach_id=coach_id,
                    stroke_type_input=stroke_type,
                    progress_callback=_progress_cb
                )
                job.result = result
                job.status = JobStatus.COMPLETED
                job.progress = 1.0
                job.progress_message = "Analysis complete!"
            except Exception as e:
                logger.exception(f"Background job {job_id} failed: {e}")
                job.status = JobStatus.FAILED
                job.error = str(e)
            finally:
                job.end_time = time.time()

        thread = threading.Thread(target=_worker_runner, daemon=True)
        thread.start()
        logger.info(f"Submitted background analysis job {job_id} for athlete {athlete_profile.name if athlete_profile else 'Guest'}")
        return job_id

    @classmethod
    def get_job(cls, job_id: str) -> Optional[BackgroundAnalysisJob]:
        """Retrieves job state safely."""
        with cls._lock:
            return cls._active_jobs.get(job_id)
