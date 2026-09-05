from typing import Tuple
from core.logger import setup_logger

logger = setup_logger(__name__)

class StatisticalValidator:
    """
    Validates statistical integrity, unit conversions, and sample size requirements.
    Rejects values that are statistically impossible or improperly formatted.
    """

    @staticmethod
    def validate_statistics(mean: float, std: float, sample_size: int) -> bool:
        """
        Ensures mean, standard deviation, and sample size are mathematically possible and robust.
        """
        if sample_size < 5:
            logger.warning(f"Rejected: Sample size {sample_size} is too small for benchmark aggregation.")
            return False
        if std < 0:
            logger.warning("Rejected: Negative standard deviation is mathematically impossible.")
            return False
        # Basic sanity bounds check can be added here
        return True

    @staticmethod
    def convert_unit(value: float, original_unit: str, target_unit: str) -> Tuple[float, str, str]:
        """
        Scientifically auditable unit conversion layer.
        Returns (converted_value, target_unit, conversion_formula).
        """
        orig = (original_unit or "").lower().strip()
        targ = (target_unit or "").lower().strip()

        if orig == targ:
            return (value, target_unit, "1:1 Exact Match (No conversion required)")

        # Frequency conversions: Hz to spm / cycles per minute
        if orig in ["hz", "cycles/sec", "strokes/sec"] and targ in ["spm", "cycles/min", "strokes/min"]:
            converted = value * 60.0
            formula = f"{value} {original_unit} * 60 = {converted} {target_unit}"
            return (round(converted, 2), target_unit, formula)

        if orig in ["spm", "cycles/min", "strokes/min"] and targ in ["hz", "cycles/sec"]:
            converted = value / 60.0
            formula = f"{value} {original_unit} / 60 = {converted:.4f} {target_unit}"
            return (round(converted, 4), target_unit, formula)

        # Distance conversions: meters
        if orig == "m" and targ == "m":
            return (value, target_unit, "1:1 Exact Match")

        # Angle conversions: degrees
        if orig in ["deg", "degrees", "°"] and targ in ["deg", "degrees"]:
            return (value, target_unit, "1:1 Exact Match")

        logger.warning(f"Unsupported or complex unit conversion from {original_unit} to {target_unit}")
        return (value, original_unit, "Direct Pass-through (Unconverted)")
