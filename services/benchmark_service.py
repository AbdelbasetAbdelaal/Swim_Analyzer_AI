from typing import Optional, Dict
from analysis.benchmarks.benchmark_engine import BenchmarkEngine
from models.benchmark_models import BenchmarkResult
from models.data_models import AnalysisResult
from models.athlete_profile import AthleteProfile
from core.logger import setup_logger

logger = setup_logger(__name__)

class BenchmarkService:
    """
    Service layer orchestrator for population benchmarking & scientific validation.
    Integrates seamlessly after Consistency Validation in the analysis pipeline.
    """
    def __init__(self):
        self.engine = BenchmarkEngine()

    def evaluate_session(self, analysis_result: AnalysisResult,
                         athlete_profile: Optional[AthleteProfile] = None) -> BenchmarkResult:
        """
        Evaluates session biomechanics against population reference benchmarks.
        Attaches benchmark_result to analysis_result.
        """
        try:
            benchmark_result = self.engine.evaluate_analysis(analysis_result, athlete_profile)
            analysis_result.benchmark_result = benchmark_result
            logger.info(f"Successfully evaluated benchmarks (Skill: {benchmark_result.overall_skill_level}, Dataset: {benchmark_result.dataset_name})")
            return benchmark_result
        except Exception:
            # Insufficient evidence is a valid BenchmarkResult from the engine.
            # Only unexpected runtime failures reach this branch and must remain visible.
            logger.exception("Error evaluating benchmarks")
            raise

    def get_percentile(self, metric_name: str, raw_value: float, stroke_type: str = "Freestyle",
                       age_group: str = "18-25", gender: str = "Male") -> float:
        return self.engine.get_percentile(metric_name, raw_value, stroke_type, age_group, gender)

    def compare_with_elite(self, metric_name: str, raw_value: float, stroke_type: str = "Freestyle",
                           age_group: str = "18-25", gender: str = "Male") -> Dict[str, float]:
        return self.engine.compare_with_elite(metric_name, raw_value, stroke_type, age_group, gender)
