from models.data_models import StrokeType
from analysis.strategies.base_strategy import BaseStrokeStrategy
from analysis.strategies.freestyle_strategy import FreestyleStrategy
from analysis.strategies.backstroke_strategy import BackstrokeStrategy
from analysis.strategies.breaststroke_strategy import BreaststrokeStrategy
from analysis.strategies.butterfly_strategy import ButterflyStrategy

class StrokeStrategyFactory:
    """Creates the appropriate Stroke Strategy based on the identified stroke type."""
    
    @staticmethod
    def get_strategy(stroke_type: StrokeType) -> BaseStrokeStrategy:
        if stroke_type == StrokeType.FREESTYLE or stroke_type == StrokeType.AUTO_DETECT:
            return FreestyleStrategy()
        elif stroke_type == StrokeType.BACKSTROKE:
            return BackstrokeStrategy()
        elif stroke_type == StrokeType.BREASTSTROKE:
            return BreaststrokeStrategy()
        elif stroke_type == StrokeType.BUTTERFLY:
            return ButterflyStrategy()
        else:
            import logging
            logging.getLogger(__name__).warning(
                f"No strategy for {stroke_type.value}. Falling back to Freestyle.")
            return FreestyleStrategy()
