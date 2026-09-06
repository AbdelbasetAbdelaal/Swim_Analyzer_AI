"""
Statistical comparison engine between AI predictions and Ground Truth annotations.
"""
from typing import List, Dict, Optional, Any, Tuple
import math
import numpy as np

from .ground_truth_models import (
    MetricComparison,
    MeasurementType,
)
from .ground_truth_policy import GroundTruthValidationPolicy, ValidationStatus


# Registry of supported metrics, their canonical units, and scientific measurement classifications
METRIC_REGISTRY = {
    "stroke_rate": {
        "gt_key": "stroke_rate_spm",
        "unit": "spm",
        "type": MeasurementType.MEASURED_PHYSICAL_QUANTITY.value,
        "description": "Cycle rate in strokes per minute",
    },
    "cycle_duration": {
        "gt_key": "cycle_duration_ms",
        "unit": "ms",
        "type": MeasurementType.MEASURED_PHYSICAL_QUANTITY.value,
        "description": "Mean cycle duration in milliseconds",
    },
    "mean_elbow_angle": {
        "gt_key": "mean_elbow_angle_deg",
        "unit": "deg",
        "type": MeasurementType.MEASURED_PHYSICAL_QUANTITY.value,
        "description": "Mean elbow angle during pull phase",
    },
    "mean_knee_angle": {
        "gt_key": "mean_knee_angle_deg",
        "unit": "deg",
        "type": MeasurementType.MEASURED_PHYSICAL_QUANTITY.value,
        "description": "Mean knee flexion angle",
    },
    "body_roll_amplitude": {
        "gt_key": "body_roll_amplitude_deg",
        "unit": "deg",
        "type": MeasurementType.MEASURED_PHYSICAL_QUANTITY.value,
        "description": "Longitudinal body roll amplitude",
    },
    "stroke_length_proxy": {
        "gt_key": "hand_excursion_proxy_bl",
        "unit": "BL",
        "type": MeasurementType.PROXY_ESTIMATE_NORMALIZED.value,
        "description": "Normalized wrist travel relative to torso. NOT literal CoM displacement.",
    },
    "true_dps": {
        "gt_key": "true_dps_meters",
        "unit": "m",
        "type": MeasurementType.MEASURED_PHYSICAL_QUANTITY.value,
        "description": "True whole-body center-of-mass translation per cycle.",
    },
    "stroke_symmetry": {
        "gt_key": "stroke_symmetry_percent",
        "unit": "%",
        "type": MeasurementType.PROXY_ESTIMATE_NORMALIZED.value,
        "description": "Left vs. right pull phase kinematic symmetry percentage.",
    },
}


class GroundTruthComparator:
    """
    Computes rigorous statistical agreement metrics between AI outputs and Ground Truth annotations.
    """

    @staticmethod
    def compute_statistics(
        y_ai: List[float],
        y_gt: List[float]
    ) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float], Optional[float]]:
        """
        Computes (MAE, RMSE, Bias, MAPE, Pearson r) for paired arrays.
        Guards against zero divisions and empty arrays.
        """
        if not y_ai or not y_gt or len(y_ai) != len(y_gt) or len(y_ai) == 0:
            return None, None, None, None, None

        ai_arr = np.array(y_ai, dtype=float)
        gt_arr = np.array(y_gt, dtype=float)
        n = len(ai_arr)

        diff = ai_arr - gt_arr
        mae = float(np.mean(np.abs(diff)))
        rmse = float(np.sqrt(np.mean(diff ** 2)))
        bias = float(np.mean(diff))

        # MAPE (guard division by zero)
        non_zero_mask = (gt_arr != 0.0)
        if np.any(non_zero_mask):
            mape = float(np.mean(np.abs(diff[non_zero_mask] / gt_arr[non_zero_mask])) * 100.0)
        else:
            mape = None

        # Pearson correlation (supplementary only)
        if n >= 2:
            std_ai = float(np.std(ai_arr))
            std_gt = float(np.std(gt_arr))
            if std_ai > 1e-9 and std_gt > 1e-9:
                corr_matrix = np.corrcoef(ai_arr, gt_arr)
                pearson_r = float(corr_matrix[0, 1])
                if math.isnan(pearson_r):
                    pearson_r = None
            else:
                pearson_r = None
        else:
            pearson_r = None

        return mae, rmse, bias, mape, pearson_r

    @classmethod
    def compare_metric(
        cls,
        canonical_metric_name: str,
        paired_observations: List[Tuple[Optional[float], Optional[float]]],
        custom_thresholds: Optional[Dict[str, Any]] = None,
    ) -> MetricComparison:
        """
        Compares paired (ai_val, gt_val) observations for a single metric.
        """
        meta = METRIC_REGISTRY.get(
            canonical_metric_name,
            {
                "gt_key": canonical_metric_name,
                "unit": "arbitrary",
                "type": MeasurementType.PROXY_ESTIMATE_NORMALIZED.value,
                "description": canonical_metric_name,
            },
        )

        sample_count = len(paired_observations)
        valid_ai: List[float] = []
        valid_gt: List[float] = []
        missing_ai_count = 0
        missing_gt_count = 0

        for ai_val, gt_val in paired_observations:
            has_ai = ai_val is not None and not math.isnan(ai_val)
            has_gt = gt_val is not None and not math.isnan(gt_val)

            if not has_ai and not has_gt:
                missing_ai_count += 1
                missing_gt_count += 1
            elif not has_ai:
                missing_ai_count += 1
            elif not has_gt:
                missing_gt_count += 1
            else:
                valid_ai.append(float(ai_val))
                valid_gt.append(float(gt_val))

        valid_count = len(valid_ai)
        mae, rmse, bias, mape, pearson_r = cls.compute_statistics(valid_ai, valid_gt)

        status, threshold_status, notes = GroundTruthValidationPolicy.evaluate_metric_status(
            metric_name=canonical_metric_name,
            valid_count=valid_count,
            mae=mae,
            rmse=rmse,
            bias=bias,
            custom_thresholds=custom_thresholds,
        )

        return MetricComparison(
            metric_name=canonical_metric_name,
            unit=meta["unit"],
            measurement_type=meta["type"],
            sample_count=sample_count,
            valid_comparison_count=valid_count,
            missing_ai_count=missing_ai_count,
            missing_gt_count=missing_gt_count,
            mae=mae,
            rmse=rmse,
            bias=bias,
            mape=mape,
            correlation_pearson=pearson_r,
            status=status,
            threshold_status=threshold_status,
            notes=notes,
        )

    @classmethod
    def compare_cohort(
        cls,
        ai_results: List[Dict[str, Any]],
        gt_samples: List[Dict[str, Any]],
        custom_thresholds: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, MetricComparison]:
        """
        Runs cohort-wide metric comparisons across paired trials.
        Expects ai_results and gt_samples to be ordered and matched 1-to-1.
        """
        comparisons: Dict[str, MetricComparison] = {}

        for metric_name, meta in METRIC_REGISTRY.items():
            gt_key = meta["gt_key"]
            pairs: List[Tuple[Optional[float], Optional[float]]] = []

            for ai_dict, gt_dict in zip(ai_results, gt_samples):
                # Extract AI value
                ai_val = ai_dict.get(metric_name)
                if ai_val is None and metric_name == "stroke_rate":
                    ai_val = ai_dict.get("stroke_rate_spm")
                elif ai_val is None and metric_name == "cycle_duration":
                    ai_val = ai_dict.get("avg_cycle_duration_ms")
                elif ai_val is None and metric_name == "stroke_length_proxy":
                    ai_val = ai_dict.get("stroke_length")

                # Extract GT value (supports both structured provenance dict and legacy numeric value)
                gt_metrics = gt_dict.get("metric_annotations", {})
                gt_entry = gt_metrics.get(gt_key)
                if isinstance(gt_entry, dict):
                    gt_val = gt_entry.get("value")
                elif gt_entry is not None:
                    gt_val = gt_entry
                elif gt_key in gt_dict:
                    gt_val = gt_dict.get(gt_key)
                else:
                    gt_val = None

                pairs.append((ai_val, gt_val))

            metric_thresh = (custom_thresholds or {}).get(metric_name)
            comparisons[metric_name] = cls.compare_metric(
                canonical_metric_name=metric_name,
                paired_observations=pairs,
                custom_thresholds=metric_thresh,
            )

        return comparisons
