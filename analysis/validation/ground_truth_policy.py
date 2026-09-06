"""
Validation policy and decision logic for Ground Truth comparison.
Enforces the Scientific Safety Policy: No manufactured thresholds, no unsupported validation claims.
"""
from enum import Enum
from typing import Optional, Dict, Any


class ValidationStatus(str, Enum):
    VALIDATED = "VALIDATED"
    VALIDATED_WITH_LIMITATIONS = "VALIDATED_WITH_LIMITATIONS"
    NOT_VALIDATED = "NOT_VALIDATED"
    INSUFFICIENT_SAMPLE = "INSUFFICIENT_SAMPLE"
    INCONCLUSIVE = "INCONCLUSIVE"
    NOT_VALIDATED_INSUFFICIENT_GROUND_TRUTH = "NOT_VALIDATED — INSUFFICIENT GROUND TRUTH"


class ThresholdStatus(str, Enum):
    TBD_REQUIRES_DOMAIN_JUSTIFICATION = "TBD — REQUIRES DOMAIN JUSTIFICATION"
    ESTABLISHED = "ESTABLISHED"


class GroundTruthValidationPolicy:
    """
    Policy governing how statistical metrics are translated to validation statuses.
    Ensures that in the absence of peer-reviewed, accredited domain thresholds,
    statuses are marked appropriately without inflating validity.
    """

    MIN_SAMPLES_FOR_PRELIMINARY_EVAL: int = 10
    MIN_SAMPLES_FOR_OFFICIAL_VALIDATION: int = 30

    @classmethod
    def evaluate_metric_status(
        cls,
        metric_name: str,
        valid_count: int,
        mae: Optional[float],
        rmse: Optional[float],
        bias: Optional[float],
        custom_thresholds: Optional[Dict[str, Any]] = None,
    ) -> tuple[str, str, str]:
        """
        Evaluates the validation status for a metric.
        
        Returns:
            (status: str, threshold_status: str, notes: str)
        """
        # Rule 1: Insufficient samples
        if valid_count == 0:
            return (
                ValidationStatus.NOT_VALIDATED_INSUFFICIENT_GROUND_TRUTH.value,
                ThresholdStatus.TBD_REQUIRES_DOMAIN_JUSTIFICATION.value,
                "No paired Ground Truth observations available."
            )
        
        if valid_count < cls.MIN_SAMPLES_FOR_PRELIMINARY_EVAL:
            return (
                ValidationStatus.INSUFFICIENT_SAMPLE.value,
                ThresholdStatus.TBD_REQUIRES_DOMAIN_JUSTIFICATION.value,
                f"Sample size (n={valid_count}) is below minimum statistical requirement (n={cls.MIN_SAMPLES_FOR_PRELIMINARY_EVAL})."
            )

        # Rule 2: If no custom validated thresholds exist, maintain strict scientific gate
        if not custom_thresholds:
            return (
                ValidationStatus.NOT_VALIDATED_INSUFFICIENT_GROUND_TRUTH.value,
                ThresholdStatus.TBD_REQUIRES_DOMAIN_JUSTIFICATION.value,
                f"Evaluated on n={valid_count} paired samples; numerical acceptance thresholds are TBD — REQUIRES DOMAIN JUSTIFICATION."
            )

        # Rule 3: Custom domain-approved thresholds provided (for future formal trials)
        max_mae = custom_thresholds.get("max_mae")
        max_rmse = custom_thresholds.get("max_rmse")
        max_bias = custom_thresholds.get("max_bias")

        if max_mae is not None and mae is not None and mae > max_mae:
            return (
                ValidationStatus.NOT_VALIDATED.value,
                ThresholdStatus.ESTABLISHED.value,
                f"MAE ({mae:.2f}) exceeds domain threshold ({max_mae:.2f})."
            )

        if max_rmse is not None and rmse is not None and rmse > max_rmse:
            return (
                ValidationStatus.NOT_VALIDATED.value,
                ThresholdStatus.ESTABLISHED.value,
                f"RMSE ({rmse:.2f}) exceeds domain threshold ({max_rmse:.2f})."
            )

        if max_bias is not None and bias is not None and abs(bias) > max_bias:
            return (
                ValidationStatus.VALIDATED_WITH_LIMITATIONS.value,
                ThresholdStatus.ESTABLISHED.value,
                f"Systematic bias ({bias:.2f}) exceeds tolerance ({max_bias:.2f})."
            )

        if valid_count >= cls.MIN_SAMPLES_FOR_OFFICIAL_VALIDATION:
            return (
                ValidationStatus.VALIDATED.value,
                ThresholdStatus.ESTABLISHED.value,
                f"Passed all domain validation criteria (n={valid_count})."
            )
        else:
            return (
                ValidationStatus.VALIDATED_WITH_LIMITATIONS.value,
                ThresholdStatus.ESTABLISHED.value,
                f"Passed criteria with preliminary sample size (n={valid_count} < {cls.MIN_SAMPLES_FOR_OFFICIAL_VALIDATION})."
            )
