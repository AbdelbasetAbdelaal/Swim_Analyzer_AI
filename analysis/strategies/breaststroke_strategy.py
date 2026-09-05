from analysis.strategies.base_strategy import BaseStrokeStrategy
from analysis.strategies.breaststroke_stroke_analyzer import BreaststrokeStateMachine
from analysis.strategies.breaststroke_biomechanics_calculator import BreaststrokeBiomechanicsCalculator
from analysis.strategies.breaststroke_scoring_engine import BreaststrokeScoringEngine

class BreaststrokeStrategy(BaseStrokeStrategy):
    """Factory for breaststroke components."""
    
    def get_stroke_analyzer(self, fps: float):
        return BreaststrokeStateMachine(fps)
        
    def get_biomechanics_calculator(self):
        return BreaststrokeBiomechanicsCalculator
        
    def get_scoring_engine(self):
        return BreaststrokeScoringEngine()
