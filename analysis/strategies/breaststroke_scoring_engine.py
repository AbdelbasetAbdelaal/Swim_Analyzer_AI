"""
Breaststroke scoring engine.
P0-7 / P0-8: No fabricated default scores. overall_score=None when upstream data is insufficient.
"""
from typing import Any, Optional
from analysis.strategies.base_strategy import BaseScoringEngine
from models.data_models import PerformanceReport, ValidatedMetric
from core.logger import setup_logger

logger = setup_logger(__name__)

class BreaststrokeScoringEngine(BaseScoringEngine):
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

        glide_ratio = _val("glide_ratio")
        max_knee_bend = _val("max_knee_bend_deg")
        sr_value = _val("stroke_rate")

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
                feedback_summary="INSUFFICIENT_EVIDENCE: No complete breaststroke cycle detected. Scoring requires at least one full cycle.",
                errors=[]
            )

        score = 100.0
        feedback_lines = []

        if sr_value is not None:
            if sr_value > 55:
                score -= 10.0
                feedback_lines.append("Stroke rate too fast — losing glide efficiency. Slow down and hold the extension.")
            elif 0 < sr_value < 25:
                score -= 5.0
                feedback_lines.append("Stroke rate is very slow. Try to maintain a consistent rhythm.")
        else:
            logger.debug("Stroke rate unavailable; skipping rate penalty (P0-7).")

        if max_knee_bend is not None and 0 < max_knee_bend < 60:
            score -= 8.0
            feedback_lines.append(f"Insufficient knee bend for whip kick ({max_knee_bend:.1f}°). Drive heels toward glutes.")
        elif max_knee_bend is None:
            logger.debug("Knee bend unavailable; skipping knee penalty (P0-7).")

        if glide_ratio is not None and 0 < glide_ratio < 0.15:
            score -= 15.0
            feedback_lines.append("Missing distinct glide phase. Ensure full arm extension before starting the next outsweep.")
        elif glide_ratio is None:
            logger.debug("Glide ratio unavailable; skipping glide penalty (P0-7).")

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
