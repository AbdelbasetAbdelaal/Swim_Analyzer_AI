from analysis.strategies.base_strategy import BaseStrokeStrategy
from analysis.strategies.butterfly_stroke_analyzer import ButterflyStateMachine
from analysis.strategies.butterfly_biomechanics_calculator import ButterflyBiomechanicsCalculator
from analysis.strategies.butterfly_scoring_engine import ButterflyScoringEngine

class ButterflyStrategy(BaseStrokeStrategy):
    """Factory for butterfly components."""
    
    def get_stroke_analyzer(self, fps: float):
        return ButterflyStateMachine(fps)
        
    def get_biomechanics_calculator(self):
        return ButterflyBiomechanicsCalculator
        
    def get_scoring_engine(self):
        return ButterflyScoringEngine()
