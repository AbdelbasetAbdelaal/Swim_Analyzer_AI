from analysis.strategies.base_strategy import BaseStrokeStrategy
from analysis.strategies.backstroke_stroke_analyzer import BackstrokeStateMachine
from analysis.strategies.backstroke_biomechanics_calculator import BackstrokeBiomechanicsCalculator
from analysis.strategies.backstroke_scoring_engine import BackstrokeScoringEngine

class BackstrokeStrategy(BaseStrokeStrategy):
    """Factory for backstroke components."""
    
    def get_stroke_analyzer(self, fps: float):
        return BackstrokeStateMachine(fps)
        
    def get_biomechanics_calculator(self):
        return BackstrokeBiomechanicsCalculator
        
    def get_scoring_engine(self):
        return BackstrokeScoringEngine()
