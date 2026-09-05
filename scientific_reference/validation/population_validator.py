from typing import Tuple, Optional
from models.scientific_evidence_models import PopulationMatchingStatus
from core.logger import setup_logger

logger = setup_logger(__name__)

class PopulationValidator:
    """
    Validates demographic and skill level compatibility.
    Prevents demographic leakage (e.g. applying adult statistics to youth).
    """
    
    @staticmethod
    def evaluate_population_match(study_pop: str, target_pop: str,
                                 study_age_range: Tuple[Optional[int], Optional[int]],
                                 target_age_range: Tuple[Optional[int], Optional[int]]) -> PopulationMatchingStatus:
        """
        Compares study demographic cohort against target benchmark population.
        Strictly flags POPULATION_MISMATCH if adult data is extrapolated to youth or masters.
        """
        spop = (study_pop or "").lower()
        tpop = (target_pop or "").lower()

        s_min, s_max = study_age_range
        t_min, t_max = target_age_range

        if t_min is not None and s_min is not None:
            if t_min < 14 and s_min >= 18:
                return PopulationMatchingStatus.POPULATION_MISMATCH # Adult to Junior extrapolation guard!
            if t_min >= 35 and s_max is not None and s_max <= 25:
                return PopulationMatchingStatus.POPULATION_MISMATCH # Adult to Masters extrapolation guard!

        if spop == tpop:
            return PopulationMatchingStatus.EXACT_MATCH
        elif "competitive" in spop and "competitive" in tpop:
            return PopulationMatchingStatus.COMPATIBLE
        elif "elite" in spop and "national" in tpop:
            return PopulationMatchingStatus.PARTIAL_MATCH
        else:
            return PopulationMatchingStatus.POPULATION_MISMATCH
