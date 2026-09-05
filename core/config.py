"""
Configuration settings for SwimAnalyzer AI.
Using dataclasses to ensure typed and structured configuration.
"""
from dataclasses import dataclass, field
from pathlib import Path
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass
class AppConfig:
    """Central configuration for the application."""
    
    # Project Paths
    base_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent)
    data_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent / "data")
    input_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent / "data" / "input_videos")
    output_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent / "data" / "output_videos")
    reports_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent / "data" / "reports")
    
    # MediaPipe Settings
    pose_model_path: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent / "models" / "pose_landmarker_full.task")
    pose_min_detection_confidence: float = 0.5
    pose_min_tracking_confidence: float = 0.5
    pose_model_complexity: int = 1  # 0, 1, or 2 (higher is more accurate but slower)
    
    # Analysis Settings
    app_config_path: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent / "config" / "config.yaml")
    landmark_confidence_threshold: float = 0.5
    
    # Logging
    log_level: str = "INFO"
    debug_mode: bool = False
    
    # VQA Settings
    vqa_blur_threshold: float = 15.0
    vqa_brightness_min: float = 40.0
    vqa_brightness_max: float = 220.0
    vqa_reflection_threshold: float = 0.10
    vqa_early_halt_frames: int = 40
    vqa_allow_critical_override: bool = False
    vqa_precheck_frames: int = 8
    vqa_precheck_stride: int = 5
    vqa_precheck_contrast_min: float = 20.0

    # Video Preprocessing
    preprocess_enable: bool = False
    preprocess_auto_exposure: bool = True
    preprocess_auto_contrast: bool = True
    preprocess_stabilization: bool = False
    preprocess_clahe_clip_limit: float = 2.0
    preprocess_min_valid_frames: int = 6

    # Video Settings
    video_downscale_width: int = 854
    video_downscale_height: int = 480
    video_default_fps: float = 30.0
    frame_stride: int = 2  # 1 = process all frames (30 FPS), 2 = process every 2nd frame (15 FPS)
    max_recommended_duration_s: float = 60.0  # Soft limit for UI warning
    max_allowed_duration_s: float = 180.0     # Hard limit cap to prevent hangs
    
    # Analysis Constants
    analysis_confidence_penalty: float = 0.20
    calibration_shoulder_width_m: float = 0.40
    
    def __post_init__(self):
        """Ensure all required directories exist and load yaml settings upon initialization."""
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        if self.app_config_path.exists():
            try:
                import yaml
                with open(self.app_config_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                
                log_cfg = data.get("logging", {})
                self.debug_mode = bool(log_cfg.get("debug_mode", self.debug_mode))
                self.log_level = str(log_cfg.get("level", self.log_level))
                
                vqa_cfg = data.get("vqa", {})
                self.vqa_blur_threshold = float(vqa_cfg.get("blur_threshold", self.vqa_blur_threshold))
                self.vqa_brightness_min = float(vqa_cfg.get("brightness_min", self.vqa_brightness_min))
                self.vqa_brightness_max = float(vqa_cfg.get("brightness_max", self.vqa_brightness_max))
                self.vqa_reflection_threshold = float(vqa_cfg.get("reflection_threshold", self.vqa_reflection_threshold))
                self.vqa_early_halt_frames = int(vqa_cfg.get("early_halt_frames", self.vqa_early_halt_frames))
                self.vqa_allow_critical_override = bool(vqa_cfg.get("allow_critical_override", self.vqa_allow_critical_override))
                self.vqa_precheck_frames = int(vqa_cfg.get("precheck_frames", self.vqa_precheck_frames))
                self.vqa_precheck_stride = int(vqa_cfg.get("precheck_stride", self.vqa_precheck_stride))
                self.vqa_precheck_contrast_min = float(vqa_cfg.get("precheck_contrast_min", self.vqa_precheck_contrast_min))

                preprocess_cfg = data.get("preprocess", {})
                self.preprocess_enable = bool(preprocess_cfg.get("enable", self.preprocess_enable))
                self.preprocess_auto_exposure = bool(preprocess_cfg.get("auto_exposure", self.preprocess_auto_exposure))
                self.preprocess_auto_contrast = bool(preprocess_cfg.get("auto_contrast", self.preprocess_auto_contrast))
                self.preprocess_stabilization = bool(preprocess_cfg.get("stabilization", self.preprocess_stabilization))
                self.preprocess_clahe_clip_limit = float(preprocess_cfg.get("clahe_clip_limit", self.preprocess_clahe_clip_limit))
                self.preprocess_min_valid_frames = int(preprocess_cfg.get("min_valid_frames", self.preprocess_min_valid_frames))
                
                video_cfg = data.get("video", {})
                self.video_downscale_width = int(video_cfg.get("downscale_width", self.video_downscale_width))
                self.video_downscale_height = int(video_cfg.get("downscale_height", self.video_downscale_height))
                
                analysis_cfg = data.get("analysis", {})
                self.video_default_fps = float(analysis_cfg.get("default_fps", self.video_default_fps))
                self.analysis_confidence_penalty = float(analysis_cfg.get("confidence_penalty", self.analysis_confidence_penalty))
                
                calib_cfg = data.get("calibration", {})
                self.calibration_shoulder_width_m = float(calib_cfg.get("shoulder_width_m", self.calibration_shoulder_width_m))
                
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Failed to load config.yaml: {e}")


# Global configuration instance
config = AppConfig()
