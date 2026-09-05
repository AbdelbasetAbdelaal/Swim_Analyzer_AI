"""
Structured logger for SwimAnalyzer AI.
Supports Production and Debug operating modes with domain category prefixes.
"""
import logging
import sys
from typing import Optional
from core.config import config


DEFAULT_CATEGORY_MAP = {
    "streamlit_app": "UI",
    "analysis_service": "ANALYSIS",
    "export_service": "EXPORT",
    "video_quality_assessor": "VQA",
    "pose_detector": "POSE",
    "video_utils": "VIDEO",
    "consistency_validator": "ANALYSIS",
    "reliability_engine": "ANALYSIS",
    "stroke_classifier": "ANALYSIS",
    "landmark_smoother": "POSE",
}


from datetime import datetime


def append_direct_log(msg: str, logger_name: str = "SwimAnalyzer", level: str = "INFO"):
    """Guaranteed direct file log appender to prevent Streamlit logger handler suppression."""
    try:
        log_file = config.base_dir / "logs" / "app.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
        formatted = f"{timestamp} - {logger_name} - {level} - {msg}\n"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(formatted)
            f.flush()
    except Exception:
        pass


class SwimLogger(logging.LoggerAdapter):
    """
    Domain-aware logger adapter providing category prefixes
    and debug-tracing guard logic based on central AppConfig.
    """

    def _get_default_category(self) -> str:
        mod_name = self.logger.name.split(".")[-1]
        return DEFAULT_CATEGORY_MAP.get(mod_name, "SYSTEM")

    def process(self, msg, kwargs):
        category = kwargs.pop("category", None)
        if not category:
            category = self._get_default_category()
        prefix = f"[{category.upper()}] " if category else ""
        return f"{prefix}{msg}", kwargs

    def debug_log(self, msg: str, category: Optional[str] = None):
        """
        Log detailed execution tracing (e.g. STEP messages).
        Emitted ONLY when config.debug_mode is True.
        """
        if config.debug_mode:
            cat = category or "DEBUG"
            self.info(msg, category=cat)

    def info_log(self, msg: str, category: Optional[str] = None):
        """Log important production lifecycle events."""
        cat = category or "INFO"
        self.info(msg, category=cat)

    def warn_log(self, msg: str, category: Optional[str] = None):
        """Log warnings."""
        cat = category or "WARNING"
        self.warning(msg, category=cat)

    def error_log(self, msg: str, category: Optional[str] = None):
        """Log errors."""
        cat = category or "ERROR"
        self.error(msg, category=cat)


class FlushingStreamHandler(logging.StreamHandler):
    """Console handler ensuring immediate output flushing."""
    def emit(self, record):
        super().emit(record)
        self.flush()


class FlushingFileHandler(logging.FileHandler):
    """File handler ensuring immediate disk file flushing."""
    def emit(self, record):
        super().emit(record)
        self.flush()


def setup_logger(name: str) -> SwimLogger:
    """
    Configure and return a SwimLogger instance.
    
    Args:
        name (str): The name of the logger (typically __name__).
        
    Returns:
        SwimLogger: Configured logger instance wrapper.
    """
    raw_logger = logging.getLogger(name)
    
    level_str = config.log_level.upper()
    level = getattr(logging, level_str, logging.INFO)
    raw_logger.setLevel(level)
    raw_logger.propagate = False
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Ensure central root logger writes to logs/app.log
    root_logger = logging.getLogger()
    has_root_file = any(isinstance(h, (logging.FileHandler, FlushingFileHandler)) for h in root_logger.handlers)
    if not has_root_file:
        try:
            log_dir = config.base_dir / "logs"
            log_dir.mkdir(exist_ok=True)
            root_fh = FlushingFileHandler(log_dir / "app.log", encoding="utf-8")
            root_fh.setFormatter(formatter)
            root_logger.addHandler(root_fh)
        except Exception:
            pass

    # Check existing handlers on specific logger
    has_stream = any(isinstance(h, (logging.StreamHandler, FlushingStreamHandler)) and not isinstance(h, (logging.FileHandler, FlushingFileHandler)) for h in raw_logger.handlers)
    has_file = any(isinstance(h, (logging.FileHandler, FlushingFileHandler)) for h in raw_logger.handlers)

    if not has_stream:
        stream_handler = FlushingStreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        raw_logger.addHandler(stream_handler)

    if not has_file:
        try:
            log_dir = config.base_dir / "logs"
            log_dir.mkdir(exist_ok=True)
            file_handler = FlushingFileHandler(log_dir / "app.log", encoding="utf-8")
            file_handler.setFormatter(formatter)
            raw_logger.addHandler(file_handler)
        except Exception:
            pass
        
    return SwimLogger(raw_logger, {})


def debug_log(msg: str, category: str = "DEBUG", logger_instance: Optional[SwimLogger] = None):
    """
    Standalone helper function for debug execution tracing.
    Only logs when config.debug_mode is True.
    """
    if config.debug_mode:
        if logger_instance:
            logger_instance.debug_log(msg, category=category)
        else:
            prefix = f"[{category.upper()}] " if category else ""
            logging.getLogger("SwimAnalyzer").info(f"{prefix}{msg}")


def info_log(msg: str, category: str = "INFO", logger_instance: Optional[SwimLogger] = None):
    """
    Standalone helper function for production logging.
    """
    if logger_instance:
        logger_instance.info_log(msg, category=category)
    else:
        prefix = f"[{category.upper()}] " if category else ""
        logging.getLogger("SwimAnalyzer").info(f"{prefix}{msg}")
