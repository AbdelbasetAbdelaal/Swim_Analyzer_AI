"""
Centralized timing utility API for Swim_Analyzer_AI.
Guarantees consistent timestamp calculations, duration derivation, and effective sampling rate calculations across frame strides.
"""

class TimingUtils:
    """
    Centralized utility for temporal calculations across video processing,
    biomechanics calculators, and reporting engines.
    """
    
    @staticmethod
    def calculate_effective_fps(source_fps: float, frame_stride: int) -> float:
        """Calculates the effective sampling rate from source FPS and frame stride."""
        if source_fps <= 0:
            return 30.0
        stride = max(1, int(frame_stride))
        return float(source_fps / stride)

    @staticmethod
    def frame_index_to_timestamp_ms(processed_frame_index: int, effective_fps: float) -> int:
        """Converts a processed frame index to a timestamp in milliseconds."""
        if effective_fps <= 0:
            return 0
        return int(round(processed_frame_index * (1000.0 / effective_fps)))

    @staticmethod
    def source_frame_to_timestamp_ms(source_frame_index: int, source_fps: float) -> int:
        """Converts a raw source video frame index to a timestamp in milliseconds."""
        if source_fps <= 0:
            return 0
        return int(round(source_frame_index * (1000.0 / source_fps)))

    @staticmethod
    def calculate_duration_seconds(total_frames: int, fps: float) -> float:
        """Calculates total duration in seconds from frame count and FPS."""
        if fps <= 0 or total_frames <= 0:
            return 0.0
        return float(total_frames / fps)

    @staticmethod
    def calculate_stroke_rate_spm(cycle_count: int, duration_seconds: float) -> float:
        """Calculates stroke rate in strokes per minute (spm)."""
        if duration_seconds <= 0 or cycle_count <= 0:
            return 0.0
        return float((cycle_count / duration_seconds) * 60.0)
