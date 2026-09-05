"""
Backstroke-specific biomechanics calculator.
Inherits all per-frame angle calculation from FreestyleBiomechanicsCalculator
and overrides calculate_global_metrics with backstroke-specific logic.
"""
from typing import List, Any
from models.data_models import FrameData, ValidatedMetric
from analysis.strategies.freestyle_biomechanics_calculator import FreestyleBiomechanicsCalculator
from core.logger import setup_logger

logger = setup_logger(__name__)

class BackstrokeBiomechanicsCalculator(FreestyleBiomechanicsCalculator):
    """
    Extends FreestyleBiomechanicsCalculator with backstroke-specific global metrics.
    Per-frame angle calculations are inherited (calculate_all_angles).
    Global metrics focus on body roll and bilateral symmetry.
    """

    @classmethod
    def calculate_global_metrics(cls, frames: List[FrameData], effective_fps: float,
                                 calibration_engine: Any = None, frame_width: int = 0,
                                 frame_height: int = 0) -> dict:
        metrics = {
            "stroke_rate": ValidatedMetric(),
            "stroke_length": ValidatedMetric(),
            "kick_frequency": ValidatedMetric(),
            "stroke_symmetry": ValidatedMetric(),
            "average_body_roll": ValidatedMetric(),
        }

        if not frames or effective_fps <= 0:
            return metrics

        try:
            # Reuse shared calculations
            metrics["stroke_rate"] = cls._calculate_stroke_rate(frames, effective_fps)
            metrics["stroke_length"] = cls._calculate_stroke_length(
                frames, calibration_engine, frame_width, frame_height)
            metrics["kick_frequency"] = cls._calculate_kick_frequency(frames, effective_fps)
            metrics["stroke_symmetry"] = cls._evaluate_symmetry(frames)

            # Backstroke-specific: average body roll angle
            body_rolls = [
                f.angles.body_roll.value
                for f in frames
                if f.is_valid and f.angles and f.angles.body_roll and f.angles.body_roll.valid
            ]
            avg_roll = float(sum(body_rolls) / len(body_rolls)) if body_rolls else 0.0
            metrics["average_body_roll"] = ValidatedMetric(
                value=avg_roll,
                valid=avg_roll > 0,
                confidence=1.0,
                reason_if_invalid="No valid body roll data found."
            )

            # Backstroke 3D metrics
            import numpy as np
            rolls_3d = [f.angles.body_roll_3d.value for f in frames if f.is_valid and f.angles and f.angles.body_roll_3d and f.angles.body_roll_3d.valid]
            torsions = [f.angles.core_torsion_3d.value for f in frames if f.is_valid and f.angles and f.angles.core_torsion_3d and f.angles.core_torsion_3d.valid]

            if rolls_3d:
                metrics["body_roll_3d"] = ValidatedMetric(name="body_roll_3d", value=float(np.mean(rolls_3d)), unit="deg", measurement_domain="pose_relative_3d", status="available", valid=True)
            if torsions:
                metrics["core_torsion_3d"] = ValidatedMetric(name="core_torsion_3d", value=float(np.mean(torsions)), unit="deg", measurement_domain="pose_relative_3d", status="available", valid=True)

        except Exception as e:
            logger.error(f"Error calculating backstroke global metrics: {e}")

        return metrics
