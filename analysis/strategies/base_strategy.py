from abc import ABC, abstractmethod
from typing import List, Tuple, Any
from models.data_models import FrameData, PerformanceReport

class BaseStrokeStateMachine(ABC):
    @abstractmethod
    def analyze_frame(self, landmarks: Any, frame_idx: int, timestamp_ms: int) -> Tuple[str, float]:
        pass


class BaseBiomechanicsCalculator(ABC):
    @classmethod
    @abstractmethod
    def calculate_global_metrics(cls, frames: List[FrameData], effective_fps: float, 
                                 calibration_engine: Any = None, frame_width: int = 0, 
                                 frame_height: int = 0) -> dict:
        pass


class BaseScoringEngine(ABC):
    @abstractmethod
    def generate_report(self, analysis_result: Any, global_metrics: dict) -> PerformanceReport:
        pass


class BaseStrokeStrategy(ABC):
    """Abstract Factory for stroke-specific components."""
    
    @abstractmethod
    def get_stroke_analyzer(self, fps: float) -> BaseStrokeStateMachine:
        pass
        
    @abstractmethod
    def get_biomechanics_calculator(self) -> type[BaseBiomechanicsCalculator]:
        pass
        
    @abstractmethod
    def get_scoring_engine(self) -> BaseScoringEngine:
        pass
