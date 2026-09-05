from analysis.strategies.base_strategy import BaseStrokeStrategy, BaseStrokeStateMachine, BaseBiomechanicsCalculator, BaseScoringEngine
from analysis.strategies.freestyle_stroke_analyzer import FreestyleStrokeStateMachine
from analysis.strategies.freestyle_biomechanics_calculator import FreestyleBiomechanicsCalculator
from analysis.strategies.freestyle_scoring_engine import FreestyleScoringEngine

class FreestyleStrategy(BaseStrokeStrategy):
    """Factory for Freestyle-specific biomechanical analysis."""
    
    def get_stroke_analyzer(self, fps: float) -> BaseStrokeStateMachine:
        return FreestyleStrokeStateMachine(fps=fps)
        
    def get_biomechanics_calculator(self) -> type[BaseBiomechanicsCalculator]:
        return FreestyleBiomechanicsCalculator
        
    def get_scoring_engine(self) -> BaseScoringEngine:
        return FreestyleScoringEngine()
