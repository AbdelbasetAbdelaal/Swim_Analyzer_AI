"""
Butterfly scoring engine.
P0-7 / P0-8: No fabricated default scores. overall_score=None when upstream data is insufficient.
"""
from typing import Any, Optional
from analysis.strategies.base_strategy import BaseScoringEngine
from models.data_models import PerformanceReport, ValidatedMetric
from core.logger import setup_logger

logger = setup_logger(__name__)

class ButterflyScoringEngine(BaseScoringEngine):
    def generate_report(self, analysis_result: Any, global_metrics: dict) -> PerformanceReport:

        def _metric(key) -> Optional[ValidatedMetric]:
            return global_metrics.get(key)

        def _val(key) -> Optional[float]:
            m = _metric(key)
            if m is None or not m.valid or m.value is None:
                return None
            return m.value

        stroke_rate_m = _metric("stroke_rate")
        stroke_length_m = _metric("stroke_length")

        sr_value = _val("stroke_rate")
        undulation = _val("hip_undulation_amplitude")
        asymmetry = _val("avg_wrist_asymmetry")

        # P0-8: Check upstream cycle count
        cycles = 0
        if analysis_result and analysis_result.stroke_statistics:
            cycles = analysis_result.stroke_statistics.completed_cycles

        if cycles == 0:
            return PerformanceReport(
                overall_score=None,
                stroke_rate=stroke_rate_m,
                stroke_length=stroke_length_m,
                kick_frequency=_metric("kick_frequency"),
                stroke_symmetry=_metric("stroke_symmetry"),
                feedback_summary="INSUFFICIENT_EVIDENCE: No complete butterfly cycle detected. Scoring requires at least one full cycle.",
                errors=[]
            )

        score = 100.0
        feedback_lines = []

        if sr_value is not None and sr_value > 60:
            score -= 10.0
            feedback_lines.append("Stroke rate too fast — you may be losing the two-beat kick rhythm.")
        elif sr_value is None:
            logger.debug("Stroke rate unavailable; skipping rate penalty (P0-7).")

        if undulation is not None and 0 < undulation < 0.1:
            score -= 12.0
            feedback_lines.append("Insufficient hip undulation. Initiate the dolphin kick from your chest and hips, not just your knees.")
        elif undulation is None:
            logger.debug("Hip undulation unavailable; skipping undulation penalty (P0-7).")

        if asymmetry is not None and asymmetry > 0.15:
            score -= 15.0
            feedback_lines.append("Significant arm asymmetry detected. Both arms should clear the water at the same time.")
        elif asymmetry is None:
            logger.debug("Wrist asymmetry unavailable; skipping asymmetry penalty (P0-7).")

        final_score = max(0.0, min(100.0, score))
        feedback = "\n".join(feedback_lines) if feedback_lines else "No critical technique issues detected this session."

        return PerformanceReport(
            overall_score=final_score,
            stroke_rate=stroke_rate_m,
            stroke_length=stroke_length_m,
            kick_frequency=_metric("kick_frequency"),
            stroke_symmetry=_metric("stroke_symmetry"),
            feedback_summary=feedback,
            errors=[]
        )
