"""
Backstroke scoring engine.
P0-7 / P0-8: No fabricated default scores. overall_score=None when upstream data is insufficient.
"""
from typing import Any, Optional
from analysis.strategies.base_strategy import BaseScoringEngine
from models.data_models import PerformanceReport, ValidatedMetric
from core.logger import setup_logger

logger = setup_logger(__name__)

class BackstrokeScoringEngine(BaseScoringEngine):
    """Scoring engine for Backstroke analysis."""

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
        avg_body_roll = _val("average_body_roll")
        symmetry = _val("stroke_symmetry")

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
                feedback_summary="INSUFFICIENT_EVIDENCE: No complete backstroke cycle detected. Scoring requires at least one full cycle.",
                errors=[]
            )

        # Start from 100, apply only penaltiess that have evidence
        score = 100.0
        feedback_lines = []

        # Stroke rate: backstroke typically 40–60 spm
        if sr_value is not None:
            if sr_value > 65:
                score -= 8.0
                feedback_lines.append("Stroke rate is too fast. Focus on a longer, controlled pull.")
            elif 0 < sr_value < 30:
                score -= 5.0
                feedback_lines.append("Stroke rate is very slow. Maintain a consistent rhythm.")
        else:
            logger.debug("Stroke rate unavailable; skipping rate penalty (P0-7).")

        # Body roll: ideal backstroke body roll is 30–50°
        if avg_body_roll is not None:
            if avg_body_roll < 20 and avg_body_roll > 0:
                score -= 12.0
                feedback_lines.append(
                    f"Insufficient body roll ({avg_body_roll:.1f}°). Rotate shoulders 30–50° to generate power.")
            elif avg_body_roll > 60:
                score -= 8.0
                feedback_lines.append(
                    f"Excessive body roll ({avg_body_roll:.1f}°). Over-rotation reduces propulsion efficiency.")
        else:
            logger.debug("Body roll unavailable; skipping roll penalty (P0-7).")

        # Symmetry: ideal is close to 100
        if symmetry is not None and 0 < symmetry < 80:
            score -= 10.0
            feedback_lines.append(
                "Significant asymmetry between left and right arm pull. Aim for equal power on both sides.")
        elif symmetry is None:
            logger.debug("Symmetry unavailable; skipping symmetry penalty (P0-7).")

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
