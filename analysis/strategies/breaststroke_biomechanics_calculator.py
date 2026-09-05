"""
Breaststroke-specific biomechanics calculator.
Inherits all per-frame angle calculation from FreestyleBiomechanicsCalculator
and overrides calculate_global_metrics with breaststroke-specific logic.
"""
from typing import List, Any
from models.data_models import FrameData, ValidatedMetric
from analysis.strategies.freestyle_biomechanics_calculator import FreestyleBiomechanicsCalculator
from core.logger import setup_logger
import numpy as np

logger = setup_logger(__name__)

class BreaststrokeBiomechanicsCalculator(FreestyleBiomechanicsCalculator):
    """
    Extends FreestyleBiomechanicsCalculator with breaststroke-specific global metrics.
    Per-frame angle calculations (elbows, knees, body roll) are inherited.
    Overrides stroke_rate cycle boundary (Glide → Outsweep) and symmetry (Insweep phase).
    """

    @classmethod
    def _calculate_stroke_rate(cls, frames: List[FrameData], effective_fps: float) -> ValidatedMetric:
        """Breaststroke cycle = Glide → Outsweep."""
        cycle_count = 0
        prev_phase = None
        for f in frames:
            if f.is_valid:
                curr = f.stroke_phase
                if prev_phase == "Glide" and curr == "Outsweep":
                    cycle_count += 1
                if curr != "Unknown":
                    prev_phase = curr

        duration_minutes = (len(frames) / effective_fps) / 60.0
        if duration_minutes > 0 and cycle_count > 0:
            sr = float(cycle_count / duration_minutes)
            valid = 10 <= sr <= 60
            reason = "" if valid else f"Stroke rate {sr:.1f} spm is outside valid breaststroke range (10-60)."
            return ValidatedMetric(value=sr, valid=valid, is_estimated=cycle_count < 2, reason_if_invalid=reason)
        return ValidatedMetric(value=0.0, valid=False, is_estimated=False,
                               reason_if_invalid="No complete breaststroke cycle detected.")

    @classmethod
    def _evaluate_symmetry(cls, frames: List[FrameData]) -> ValidatedMetric:
        """Breaststroke symmetry: compare left vs right elbow angle during Insweep."""
        l_insweep = [f.angles.left_elbow.value for f in frames
                     if f.is_valid and f.stroke_phase == "Insweep"
                     and f.angles and f.angles.left_elbow and f.angles.left_elbow.valid]
        r_insweep = [f.angles.right_elbow.value for f in frames
                     if f.is_valid and f.stroke_phase == "Insweep"
                     and f.angles and f.angles.right_elbow and f.angles.right_elbow.valid]
        if l_insweep and r_insweep:
            diff = abs(np.mean(l_insweep) - np.mean(r_insweep))
            sym = max(0.0, 100.0 - diff)
            return ValidatedMetric(name="stroke_symmetry", value=sym, unit="percent", measurement_domain="calibrated_physical", status="available", valid=True)
        return ValidatedMetric(name="stroke_symmetry", value=None, unit="percent", measurement_domain="unavailable", status="unavailable", valid=False,
                               reason_if_invalid="No Insweep phase data for symmetry comparison.")

    @classmethod
    def calculate_global_metrics(cls, frames: List[FrameData], effective_fps: float,
                                 calibration_engine: Any = None, frame_width: int = 0,
                                 frame_height: int = 0) -> dict:
        metrics = {
            "stroke_rate": ValidatedMetric(),
            "stroke_length": ValidatedMetric(),
            "kick_frequency": ValidatedMetric(),
            "stroke_symmetry": ValidatedMetric(),
            "glide_ratio": ValidatedMetric(),
            "max_knee_bend_deg": ValidatedMetric(),
        }

        if not frames or effective_fps <= 0:
            return metrics

        try:
            # Reuse shared calculations
            metrics["stroke_rate"] = cls._calculate_stroke_rate(frames, effective_fps)
            metrics["stroke_length"] = cls._calculate_stroke_length(frames, calibration_engine, frame_width, frame_height)
            metrics["kick_frequency"] = cls._calculate_kick_frequency(frames, effective_fps)
            metrics["stroke_symmetry"] = cls._evaluate_symmetry(frames)

            # Breaststroke-specific: glide ratio
            total_frames = len(frames)
            glide_frames = sum(1 for f in frames if f.stroke_phase == "Glide")
            glide_ratio = glide_frames / total_frames if total_frames > 0 else 0.0
            metrics["glide_ratio"] = ValidatedMetric(
                name="glide_ratio",
                value=glide_ratio,
                unit="ratio",
                measurement_domain="relative_body_normalized",
                status="available",
                valid=True,
                confidence=1.0,
                reason_if_invalid=""
            )

            # Breaststroke-specific: max knee bend from joint angles
            knee_bends = []
            for f in frames:
                if f.is_valid and f.angles and f.angles.right_knee and f.angles.right_knee.valid:
                    # knee angle: 180 is fully straight, lower = more bent
                    bend = 180.0 - f.angles.right_knee.value
                    knee_bends.append(bend)

            max_bend = float(max(knee_bends)) if knee_bends else 0.0
            metrics["max_knee_bend_deg"] = ValidatedMetric(
                name="max_knee_bend_deg",
                value=max_bend if max_bend > 0 else None,
                unit="deg",
                measurement_domain="relative_body_normalized",
                status="available" if max_bend > 0 else "unavailable",
                valid=max_bend > 0,
                confidence=1.0,
                reason_if_invalid="" if max_bend > 0 else "No valid knee angle data found."
            )

            # Breaststroke 3D metrics
            rolls_3d = [f.angles.body_roll_3d.value for f in frames if f.is_valid and f.angles and f.angles.body_roll_3d and f.angles.body_roll_3d.valid]
            torsions = [f.angles.core_torsion_3d.value for f in frames if f.is_valid and f.angles and f.angles.core_torsion_3d and f.angles.core_torsion_3d.valid]

            if rolls_3d:
                metrics["body_roll_3d"] = ValidatedMetric(name="body_roll_3d", value=float(np.mean(rolls_3d)), unit="deg", measurement_domain="pose_relative_3d", status="available", valid=True)
            if torsions:
                metrics["core_torsion_3d"] = ValidatedMetric(name="core_torsion_3d", value=float(np.mean(torsions)), unit="deg", measurement_domain="pose_relative_3d", status="available", valid=True)

        except Exception as e:
            logger.error(f"Error calculating breaststroke global metrics: {e}")

        return metrics
