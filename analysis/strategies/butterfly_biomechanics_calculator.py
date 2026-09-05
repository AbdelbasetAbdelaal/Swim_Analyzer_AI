"""
Butterfly-specific biomechanics calculator.
Inherits all per-frame angle calculation from FreestyleBiomechanicsCalculator
and overrides calculate_global_metrics with butterfly-specific logic.
"""
from typing import List, Any
import numpy as np
from models.data_models import FrameData, ValidatedMetric
from analysis.strategies.freestyle_biomechanics_calculator import FreestyleBiomechanicsCalculator
from core.logger import setup_logger

logger = setup_logger(__name__)

class ButterflyBiomechanicsCalculator(FreestyleBiomechanicsCalculator):
    """
    Extends FreestyleBiomechanicsCalculator with butterfly-specific global metrics.
    Per-frame angle calculations (elbows, knees, body roll) are inherited.
    Global metrics focus on hip undulation amplitude and bilateral arm symmetry.
    """

    @classmethod
    def _evaluate_symmetry(cls, frames: List[FrameData]) -> ValidatedMetric:
        """Butterfly symmetry: measures average Y-difference between left and right wrists.
        Both wrists should track together; large difference = asymmetric recovery."""
        diffs = []
        for f in frames:
            lm = f.raw_landmarks
            if f.is_valid and lm and len(lm) >= 17:
                try:
                    diff = abs(lm[15].y - lm[16].y)
                    diffs.append(diff)
                except Exception as e:
                    logger.debug("Failed to calculate wrist symmetry for frame: %s", e)
        if diffs:
            import numpy as np
            avg_diff = float(np.mean(diffs))
            # Convert to a 0-100 score (0 diff = 100, 0.3 diff = 0)
            sym_score = max(0.0, 100.0 - (avg_diff / 0.3) * 100.0)
            return ValidatedMetric(name="stroke_symmetry", value=sym_score, unit="percent", measurement_domain="calibrated_physical", status="available", valid=True)
        return ValidatedMetric(name="stroke_symmetry", value=None, unit="percent", measurement_domain="unavailable", status="unavailable", valid=False,
                               reason_if_invalid="No wrist landmark data for symmetry comparison.")

    @classmethod
    def calculate_global_metrics(cls, frames: List[FrameData], effective_fps: float,
                                 calibration_engine: Any = None, frame_width: int = 0,
                                 frame_height: int = 0) -> dict:
        metrics = {
            "stroke_rate": ValidatedMetric(),
            "stroke_length": ValidatedMetric(),
            "kick_frequency": ValidatedMetric(),
            "stroke_symmetry": ValidatedMetric(),
            "hip_undulation_amplitude": ValidatedMetric(),
            "avg_wrist_asymmetry": ValidatedMetric(),
        }

        if not frames or effective_fps <= 0:
            return metrics

        try:
            # Reuse shared calculations
            metrics["stroke_rate"] = cls._calculate_stroke_rate(frames, effective_fps)
            metrics["stroke_length"] = cls._calculate_stroke_length(frames, calibration_engine, frame_width, frame_height)
            metrics["kick_frequency"] = cls._calculate_kick_frequency(frames, effective_fps)
            metrics["stroke_symmetry"] = cls._evaluate_symmetry(frames)

            # Butterfly-specific: hip undulation amplitude (Y-range of midpoint hips)
            hip_y_values = []
            wrist_asymmetries = []

            for f in frames:
                lm = f.raw_landmarks
                if f.is_valid and lm and len(lm) >= 25:
                    try:
                        hip_y = (lm[23].y + lm[24].y) / 2
                        hip_y_values.append(hip_y)

                        wrist_diff = abs(lm[15].y - lm[16].y)
                        wrist_asymmetries.append(wrist_diff)
                    except Exception as e:
                        logger.debug("Failed to calculate undulation/asymmetry for frame: %s", e)

            undulation = float(max(hip_y_values) - min(hip_y_values)) if len(hip_y_values) > 10 else 0.0
            metrics["hip_undulation_amplitude"] = ValidatedMetric(
                name="hip_undulation_amplitude",
                value=undulation if undulation > 0 else None,
                unit="body_length",
                measurement_domain="relative_body_normalized",
                status="available" if undulation > 0 else "unavailable",
                valid=undulation > 0,
                confidence=1.0,
                reason_if_invalid="" if undulation > 0 else "Insufficient frames for undulation measurement."
            )

            avg_asym = float(np.mean(wrist_asymmetries)) if wrist_asymmetries else 0.0
            metrics["avg_wrist_asymmetry"] = ValidatedMetric(
                name="avg_wrist_asymmetry",
                value=avg_asym if wrist_asymmetries else None,
                unit="image_space",
                measurement_domain="image_space",
                status="available" if wrist_asymmetries else "unavailable",
                valid=len(wrist_asymmetries) > 0,
                confidence=1.0,
                reason_if_invalid="" if wrist_asymmetries else "No wrist landmark data"
            )

            # Butterfly 3D metrics
            rolls_3d = [f.angles.body_roll_3d.value for f in frames if f.is_valid and f.angles and f.angles.body_roll_3d and f.angles.body_roll_3d.valid]
            torsions = [f.angles.core_torsion_3d.value for f in frames if f.is_valid and f.angles and f.angles.core_torsion_3d and f.angles.core_torsion_3d.valid]

            if rolls_3d:
                metrics["body_roll_3d"] = ValidatedMetric(name="body_roll_3d", value=float(np.mean(rolls_3d)), unit="deg", measurement_domain="pose_relative_3d", status="available", valid=True)
            if torsions:
                metrics["core_torsion_3d"] = ValidatedMetric(name="core_torsion_3d", value=float(np.mean(torsions)), unit="deg", measurement_domain="pose_relative_3d", status="available", valid=True)

        except Exception as e:
            logger.error(f"Error calculating butterfly global metrics: {e}")

        return metrics
