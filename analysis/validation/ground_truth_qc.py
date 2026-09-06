"""
Double-Blind Human Annotation Quality Control & Agreement Engine.
Enforces audit preservation of independent rater annotations, verifies annotator blinding,
computes inter-rater agreement (ICC(2,1) and frame tolerances), and tracks adjudication.
"""
from typing import Dict, List, Optional, Any, Tuple
import os
import json
import math
from pathlib import Path
from datetime import datetime, timezone

from core.logger import setup_logger
from .ground_truth_models import (
    GroundTruthSample,
    InclusionStatus,
    AnnotationStatus,
    QualityStatus,
)
from .provenance_contract import ProvenanceValidator

logger = setup_logger(__name__)

FORBIDDEN_AI_KEYS = {
    "overall_score",
    "technique_score",
    "reliability_score",
    "analysis_reliability",
    "scientific_confidence",
    "benchmark_percentile",
    "ai_prediction",
    "predicted_stroke",
    "model_confidence",
    "ai_error_list",
    "ai_feedback",
    "pose_backend",
}


def calculate_icc_2_1(data_pairs: List[Tuple[float, float]]) -> float:
    """
    Computes two-way random effects single-measure Intraclass Correlation Coefficient ICC(2,1)
    for absolute agreement across two raters on k items.
    
    Returns 1.0 if variance is zero and ratings match exactly.
    """
    n = len(data_pairs)
    if n < 2:
        return 1.0

    # Extract ratings
    y1 = [p[0] for p in data_pairs]
    y2 = [p[1] for p in data_pairs]
    k = 2 # two raters

    row_means = [(y1[i] + y2[i]) / 2.0 for i in range(n)]
    grand_mean = sum(row_means) / n

    col_mean_1 = sum(y1) / n
    col_mean_2 = sum(y2) / n

    # Sum of squares total
    sst = sum((y1[i] - grand_mean) ** 2 + (y2[i] - grand_mean) ** 2 for i in range(n))

    # Sum of squares rows (between items/targets)
    ssr = k * sum((rm - grand_mean) ** 2 for rm in row_means)

    # Sum of squares columns (between raters)
    ssc = n * ((col_mean_1 - grand_mean) ** 2 + (col_mean_2 - grand_mean) ** 2)

    # Sum of squares error (residual)
    sse = sst - ssr - ssc
    if sse < 0:
        sse = 0.0

    # Mean squares
    msr = ssr / (n - 1) if n > 1 else 0.0
    msc = ssc / (k - 1) if k > 1 else 0.0
    mse = sse / ((n - 1) * (k - 1)) if (n - 1) * (k - 1) > 0 else 0.0

    # ICC(2,1) formula: (MSR - MSE) / (MSR + (k - 1)MSE + (k/n)(MSC - MSE))
    denominator = msr + (k - 1) * mse + (k / n) * (msc - mse)
    if denominator <= 0:
        # Check if ratings are identical
        if max(abs(y1[i] - y2[i]) for i in range(n)) < 1e-6:
            return 1.0
        return 0.0

    icc = (msr - mse) / denominator
    return max(-1.0, min(1.0, float(icc)))


class GroundTruthQCEngine:
    """
    Manages double-blind quality control, agreement verification, adjudication,
    and audit preservation under data/ground_truth/quality_control/<sample_id>/.
    """

    def __init__(self, repo_root: Optional[Path] = None):
        self.repo_root = repo_root or Path(__file__).resolve().parent.parent.parent
        self.qc_dir = self.repo_root / "data" / "ground_truth" / "quality_control"
        self.annotations_dir = self.repo_root / "data" / "ground_truth" / "annotations"

    def verify_blinding(self, rater_data: Dict[str, Any], rater_label: str) -> List[str]:
        """
        Ensures rater annotation contains no AI output, predicted labels, or scores.
        """
        violations: List[str] = []
        
        def _scan_dict(d: Dict[str, Any], prefix: str = ""):
            for k, v in d.items():
                full_key = f"{prefix}.{k}" if prefix else k
                if k.lower() in FORBIDDEN_AI_KEYS:
                    violations.append(
                        f"BLINDING VIOLATION in {rater_label}: found forbidden AI field '{full_key}'"
                    )
                if isinstance(v, dict):
                    _scan_dict(v, full_key)
                elif isinstance(v, list):
                    for idx, item in enumerate(v):
                        if isinstance(item, dict):
                            _scan_dict(item, f"{full_key}[{idx}]")

        _scan_dict(rater_data)
        return violations

    def evaluate_inter_rater_agreement(
        self,
        sample_id: str,
        rater_a: Dict[str, Any],
        rater_b: Dict[str, Any],
        max_frame_tolerance: int = 2,
    ) -> Dict[str, Any]:
        """
        Compares Rater A and Rater B annotations across temporal and continuous metrics.
        Returns a comprehensive agreement evaluation dictionary.
        """
        agreement_report = {
            "sample_id": sample_id,
            "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
            "rater_a_id": rater_a.get("annotator_id", "RATER_A"),
            "rater_b_id": rater_b.get("annotator_id", "RATER_B"),
            "temporal_checks": [],
            "metric_checks": [],
            "all_temporal_passed": True,
            "all_metrics_passed": True,
            "requires_adjudication": False,
            "calculated_icc": None,
            "agreement_status": "PASSED",
            "notes": [],
        }

        # 1. Temporal Cycle Checks (start/end frame <= tolerance)
        cycles_a = rater_a.get("cycle_annotations", [])
        cycles_b = rater_b.get("cycle_annotations", [])

        if len(cycles_a) != len(cycles_b):
            agreement_report["all_temporal_passed"] = False
            agreement_report["requires_adjudication"] = True
            agreement_report["notes"].append(
                f"Cycle count mismatch: Rater A identified {len(cycles_a)} cycles, Rater B identified {len(cycles_b)} cycles."
            )
        else:
            for i in range(len(cycles_a)):
                ca = cycles_a[i]
                cb = cycles_b[i]
                start_diff = abs(ca.get("start_frame", 0) - cb.get("start_frame", 0))
                end_diff = abs(ca.get("end_frame", 0) - cb.get("end_frame", 0))
                passed = (start_diff <= max_frame_tolerance and end_diff <= max_frame_tolerance)
                if not passed:
                    agreement_report["all_temporal_passed"] = False
                    agreement_report["requires_adjudication"] = True
                agreement_report["temporal_checks"].append({
                    "cycle_index": i + 1,
                    "rater_a_start": ca.get("start_frame"),
                    "rater_b_start": cb.get("start_frame"),
                    "start_frame_diff": start_diff,
                    "rater_a_end": ca.get("end_frame"),
                    "rater_b_end": cb.get("end_frame"),
                    "end_frame_diff": end_diff,
                    "passed": passed,
                })

        # 2. Metric Annotations Checks
        metrics_a = rater_a.get("metric_annotations", {})
        metrics_b = rater_b.get("metric_annotations", {})
        paired_values_for_icc: List[Tuple[float, float]] = []

        common_metric_keys = set(metrics_a.keys()).union(set(metrics_b.keys()))
        
        # Metric tolerances for triggering review
        tolerances = {
            "stroke_rate_spm": 2.0,
            "cycle_duration_ms": 60.0,
            "mean_elbow_angle_deg": 6.0,
            "mean_knee_angle_deg": 6.0,
            "body_roll_amplitude_deg": 6.0,
            "stroke_symmetry_percent": 5.0,
            "hand_excursion_proxy_bl": 0.08,
        }

        for m_key in sorted(common_metric_keys):
            obj_a = metrics_a.get(m_key, {})
            obj_b = metrics_b.get(m_key, {})
            val_a = obj_a.get("value") if isinstance(obj_a, dict) else None
            val_b = obj_b.get("value") if isinstance(obj_b, dict) else None

            if val_a is not None and val_b is not None:
                diff = abs(val_a - val_b)
                tol = tolerances.get(m_key, 5.0)
                passed = (diff <= tol)
                if not passed:
                    agreement_report["all_metrics_passed"] = False
                    agreement_report["requires_adjudication"] = True
                    agreement_report["notes"].append(
                        f"Metric '{m_key}' divergence exceeds operational tolerance: |{val_a} - {val_b}| = {diff:.2f} > {tol}"
                    )
                paired_values_for_icc.append((float(val_a), float(val_b)))
                agreement_report["metric_checks"].append({
                    "metric": m_key,
                    "rater_a_value": val_a,
                    "rater_b_value": val_b,
                    "absolute_diff": round(diff, 3),
                    "tolerance": tol,
                    "passed": passed,
                })
            elif val_a is not None or val_b is not None:
                # One rater annotated, other missed
                agreement_report["all_metrics_passed"] = False
                agreement_report["requires_adjudication"] = True
                agreement_report["metric_checks"].append({
                    "metric": m_key,
                    "rater_a_value": val_a,
                    "rater_b_value": val_b,
                    "passed": False,
                    "error": "Metric present in only one rater annotation.",
                })

        # 3. Overall ICC(2,1)
        if len(paired_values_for_icc) >= 2:
            icc_val = calculate_icc_2_1(paired_values_for_icc)
            agreement_report["calculated_icc"] = round(icc_val, 4)
            if icc_val < 0.90:
                agreement_report["requires_adjudication"] = True
                agreement_report["notes"].append(
                    f"Overall ICC(2,1) = {icc_val:.4f} is below scientific threshold of 0.90."
                )

        if agreement_report["requires_adjudication"]:
            agreement_report["agreement_status"] = "ADJUDICATION_REQUIRED"
        else:
            agreement_report["agreement_status"] = "PASSED"

        return agreement_report

    def process_and_save_trial_qc(
        self,
        sample_id: str,
        rater_a_data: Dict[str, Any],
        rater_b_data: Dict[str, Any],
        adjudication_data: Optional[Dict[str, Any]] = None,
        save_to_annotations: bool = True,
    ) -> Tuple[bool, Dict[str, Any], List[str]]:
        """
        Executes full double-blind QC workflow:
        1. Checks blinding violations.
        2. Preserves rater_A.json and rater_B.json in quality_control/<sample_id>/.
        3. Computes and saves agreement.json.
        4. Saves adjudication.json.
        5. Produces final_ground_truth.json and optionally saves to data/ground_truth/annotations/.
        """
        errors: List[str] = []
        sample_qc_dir = self.qc_dir / sample_id
        sample_qc_dir.mkdir(parents=True, exist_ok=True)

        # 1. Blinding check
        blind_errs_a = self.verify_blinding(rater_a_data, "Rater A")
        blind_errs_b = self.verify_blinding(rater_b_data, "Rater B")
        all_blind_errs = blind_errs_a + blind_errs_b
        if all_blind_errs:
            return False, {}, all_blind_errs

        # 2. Save Rater A and Rater B raw data
        with open(sample_qc_dir / "rater_A.json", "w", encoding="utf-8") as f:
            json.dump(rater_a_data, f, indent=2)

        with open(sample_qc_dir / "rater_B.json", "w", encoding="utf-8") as f:
            json.dump(rater_b_data, f, indent=2)

        # 3. Evaluate agreement
        agreement = self.evaluate_inter_rater_agreement(sample_id, rater_a_data, rater_b_data)
        with open(sample_qc_dir / "agreement.json", "w", encoding="utf-8") as f:
            json.dump(agreement, f, indent=2)

        # 4. Adjudication check
        if agreement["requires_adjudication"]:
            if not adjudication_data:
                errors.append(
                    f"Sample {sample_id} requires adjudication due to inter-rater discrepancies, but no adjudication record provided."
                )
                return False, agreement, errors
            adj_record = adjudication_data
        else:
            adj_record = {
                "sample_id": sample_id,
                "adjudication": "NOT_REQUIRED",
                "reason": "All inter-rater agreement criteria met within operational tolerances (frame diff <= 2, ICC >= 0.90).",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        with open(sample_qc_dir / "adjudication.json", "w", encoding="utf-8") as f:
            json.dump(adj_record, f, indent=2)

        # 5. Produce Final Ground Truth record
        # Start from base of Rater A, take mean/consensus for metrics and cycles
        final_gt = dict(rater_a_data)
        final_gt["sample_id"] = sample_id
        final_gt["secondary_annotator_id"] = rater_b_data.get("annotator_id", "EXPERT-RATER-02")
        final_gt["annotation_version"] = "1.0.0"
        final_gt["annotation_timestamp"] = datetime.now(timezone.utc).isoformat()

        # Update quality flags
        q_flags = final_gt.get("quality_flags", {})
        q_flags["inter_rater_agreement_icc"] = agreement.get("calculated_icc")
        q_flags["requires_adjudication"] = agreement.get("requires_adjudication", False)
        final_gt["quality_flags"] = q_flags

        # Merge cycle annotations (mean of start/end frames)
        merged_cycles = []
        cycles_a = rater_a_data.get("cycle_annotations", [])
        cycles_b = rater_b_data.get("cycle_annotations", [])
        fps = float(final_gt.get("video_fps", 30.0))

        for i in range(min(len(cycles_a), len(cycles_b))):
            ca = cycles_a[i]
            cb = cycles_b[i]
            # If adjudicated, use adjudicated value if available
            c_start = int(round((ca["start_frame"] + cb["start_frame"]) / 2.0))
            c_end = int(round((ca["end_frame"] + cb["end_frame"]) / 2.0))
            dur_ms = round(((c_end - c_start) / fps) * 1000.0, 1)
            sr_spm = round((60.0 / ((c_end - c_start) / fps)), 2)
            
            merged_cycles.append({
                "cycle_index": i + 1,
                "start_frame": c_start,
                "end_frame": c_end,
                "duration_ms": dur_ms,
                "stroke_rate_spm": sr_spm,
                "phase_events": ca.get("phase_events", []),
            })
        final_gt["cycle_annotations"] = merged_cycles

        # Merge metric annotations (consensus mean or adjudicated)
        merged_metrics = {}
        metrics_a = rater_a_data.get("metric_annotations", {})
        metrics_b = rater_b_data.get("metric_annotations", {})

        for m_key in metrics_a.keys():
            ma = metrics_a[m_key]
            mb = metrics_b.get(m_key, {})
            val_a = ma.get("value")
            val_b = mb.get("value") if isinstance(mb, dict) else None

            merged_entry = dict(ma)
            if val_a is not None and val_b is not None:
                # Compute arithmetic mean rounded to 2 decimals
                merged_entry["value"] = round((val_a + val_b) / 2.0, 2)
            merged_metrics[m_key] = merged_entry

        # Overwrite with any adjudicated metrics if applicable
        if adjudication_data and "metric_overrides" in adjudication_data:
            for ov_k, ov_v in adjudication_data["metric_overrides"].items():
                if ov_k in merged_metrics:
                    merged_metrics[ov_k]["value"] = ov_v

        final_gt["metric_annotations"] = merged_metrics

        # Save final_ground_truth.json in QC dir
        with open(sample_qc_dir / "final_ground_truth.json", "w", encoding="utf-8") as f:
            json.dump(final_gt, f, indent=2)

        # Save to data/ground_truth/annotations/<sample_id>.json
        if save_to_annotations:
            self.annotations_dir.mkdir(parents=True, exist_ok=True)
            ann_path = self.annotations_dir / f"{sample_id}.json"
            with open(ann_path, "w", encoding="utf-8") as f:
                json.dump(final_gt, f, indent=2)

        return True, final_gt, []
