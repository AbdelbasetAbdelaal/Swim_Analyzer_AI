"""
Double-Blind Human Annotation Quality Control & Per-Metric Inter-Rater Reliability Engine.

Adheres strictly to the scientific protocol:
1. Content-Level Blinding Verification: Verifies syntactic absence of model predictions and AI fields.
2. Single-Trial Discrepancy Gating: Temporal frame differences (<= 2 frames) and continuous metric differences.
   Never pools heterogeneous metrics into a fake single-trial "overall ICC".
3. Per-Metric Cohort Inter-Rater Reliability: Computes two-way random absolute agreement ICC(2,1)
   strictly per metric across multiple independent trials (items).
4. Small-Sample Gate: Prohibits claiming scientific validation from single trials or small pilot cohorts (n < 24).
"""
from typing import Dict, List, Optional, Any, Tuple
import os
import json
import math
from pathlib import Path
from datetime import datetime, timezone, timedelta

from core.logger import setup_logger
from .ground_truth_models import (
    GroundTruthSample,
    InclusionStatus,
    AnnotationStatus,
    QualityStatus,
)
from .provenance_contract import ProvenanceValidator

logger = setup_logger(__name__)

# Content-level blinding scan targets
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


def verify_content_level_blinding(rater_data: Dict[str, Any], rater_label: str = "Rater") -> Tuple[bool, List[str]]:
    """
    Performs CONTENT-LEVEL BLINDING VERIFICATION by scanning annotation dictionaries
    for forbidden AI prediction keywords and keys.
    
    IMPORTANT SCIENTIFIC DISTINCTION:
    This verification confirms the syntactic absence of model predictions and AI fields in the data file.
    It DOES NOT prove human procedural blinding, which requires organizational separation during capture.
    """
    violations: List[str] = []

    def _scan_dict(d: Dict[str, Any], prefix: str = ""):
        for k, v in d.items():
            full_key = f"{prefix}.{k}" if prefix else k
            if k.lower() in FORBIDDEN_AI_KEYS:
                violations.append(
                    f"CONTENT BLINDING VIOLATION in {rater_label}: found forbidden AI field '{full_key}'"
                )
            if isinstance(v, dict):
                _scan_dict(v, full_key)
            elif isinstance(v, list):
                for idx, item in enumerate(v):
                    if isinstance(item, dict):
                        _scan_dict(item, f"{full_key}[{idx}]")

    _scan_dict(rater_data)
    is_clean = (len(violations) == 0)
    return is_clean, violations


def compute_metric_icc_2_1(
    metric_name: str,
    trial_pairs: List[Tuple[float, float]],
    alpha: float = 0.05
) -> Dict[str, Any]:
    """
    Computes two-way random effects single-measure Intraclass Correlation Coefficient ICC(2,1)
    for absolute agreement across two raters on n independent trials (items).
    
    CRITICAL SCIENTIFIC RULES:
    1. NEVER pool heterogeneous metrics (e.g. spm, ms, deg) into one calculation.
       ICC(2,1) MUST be computed strictly for ONE metric across multiple trials.
    2. Minimum sample requirement: n >= 2 trials.
    3. Small-sample rule: When n < 24, label output as PILOT INTER-RATER RELIABILITY only.
    """
    n = len(trial_pairs)
    if n < 2:
        return {
            "metric_name": metric_name,
            "n_items": n,
            "icc_2_1": None,
            "confidence_interval": None,
            "agreement_interpretation": "INSUFFICIENT_SAMPLE: Minimum 2 independent trials required to evaluate ICC across items.",
            "is_pilot_evidence": True,
            "status": "INSUFFICIENT_SAMPLE",
        }

    k = 2  # two raters
    y1 = [float(p[0]) for p in trial_pairs]
    y2 = [float(p[1]) for p in trial_pairs]

    row_means = [(y1[i] + y2[i]) / 2.0 for i in range(n)]
    grand_mean = sum(row_means) / n

    col_mean_1 = sum(y1) / n
    col_mean_2 = sum(y2) / n

    # Total Sum of Squares
    sst = sum((y1[i] - grand_mean) ** 2 + (y2[i] - grand_mean) ** 2 for i in range(n))

    # Sum of Squares Rows (Between Items/Trials)
    ssr = k * sum((rm - grand_mean) ** 2 for rm in row_means)

    # Sum of Squares Columns (Between Raters)
    ssc = n * ((col_mean_1 - grand_mean) ** 2 + (col_mean_2 - grand_mean) ** 2)

    # Sum of Squares Error (Residual)
    sse = max(0.0, sst - ssr - ssc)

    # Mean Squares
    msr = ssr / (n - 1) if n > 1 else 0.0
    msc = ssc / (k - 1) if k > 1 else 0.0
    mse = sse / ((n - 1) * (k - 1)) if (n - 1) * (k - 1) > 0 else 0.0

    # Denominator for ICC(2,1): MSR + (k - 1)MSE + (k/n)(MSC - MSE)
    denominator = msr + (k - 1) * mse + (k / n) * (msc - mse)

    if denominator <= 0:
        # Check if ratings are identical
        if max(abs(y1[i] - y2[i]) for i in range(n)) < 1e-6:
            icc_val = 1.0
        else:
            icc_val = 0.0
    else:
        icc_val = (msr - mse) / denominator
        icc_val = max(-1.0, min(1.0, float(icc_val)))

    # Approximate 95% Confidence Interval
    ci = None
    if n >= 4 and msr > 0 and mse > 0:
        f_stat = msr / mse if mse > 0 else 1.0
        # Approximate SE for single-measure ICC(2,1)
        se = math.sqrt(2.0 * ((1.0 - icc_val) ** 2) * ((1.0 + (k - 1) * icc_val) ** 2) / (k * (k - 1) * (n - 1)))
        ci_lower = max(-1.0, round(icc_val - 1.96 * se, 4))
        ci_upper = min(1.0, round(icc_val + 1.96 * se, 4))
        ci = [ci_lower, ci_upper]

    # Standard interpretation (Koo & Li, 2016)
    if icc_val >= 0.90:
        qual = "Excellent agreement"
    elif icc_val >= 0.75:
        qual = "Good agreement"
    elif icc_val >= 0.50:
        qual = "Moderate agreement"
    else:
        qual = "Poor agreement"

    # Small-sample prefix
    is_pilot = (n < 24)
    if is_pilot:
        interpretation = f"PILOT_INTER_RATER_RELIABILITY: {qual} observed in preliminary cohort (n={n}); does not constitute definitive scientific validation."
    else:
        interpretation = f"VALIDATION_INTER_RATER_RELIABILITY: {qual} (n={n})."

    return {
        "metric_name": metric_name,
        "n_items": n,
        "icc_2_1": round(icc_val, 4),
        "confidence_interval": ci,
        "agreement_interpretation": interpretation,
        "is_pilot_evidence": is_pilot,
        "status": "CALCULATED",
    }


class GroundTruthQCEngine:
    """
    Manages double-blind quality control, single-trial rater discrepancy gating,
    and multi-trial per-metric ICC evaluation.
    """

    def __init__(self, repo_root: Optional[Path] = None):
        self.repo_root = repo_root or Path(__file__).resolve().parent.parent.parent
        self.qc_dir = self.repo_root / "data" / "ground_truth" / "quality_control"
        self.annotations_dir = self.repo_root / "data" / "ground_truth" / "annotations"

    def verify_blinding(self, rater_data: Dict[str, Any], rater_label: str) -> List[str]:
        """Wrapper around verify_content_level_blinding."""
        _, violations = verify_content_level_blinding(rater_data, rater_label)
        return violations

    def evaluate_single_trial_discrepancies(
        self,
        sample_id: str,
        rater_a: Dict[str, Any],
        rater_b: Dict[str, Any],
        max_frame_tolerance: int = 2,
    ) -> Dict[str, Any]:
        """
        Evaluates agreement for a SINGLE trial using operational discrepancy gates.
        
        DOES NOT compute a pooled or single-trial "overall ICC".
        Instead, evaluates:
        1. Temporal cycle boundary discrepancies (<= 2 frames at 30-60 fps).
        2. Per-metric absolute divergences against operational review thresholds.
        """
        report = {
            "sample_id": sample_id,
            "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
            "rater_a_id": rater_a.get("annotator_id", "RATER_A"),
            "rater_b_id": rater_b.get("annotator_id", "RATER_B"),
            "temporal_discrepancies": [],
            "metric_discrepancies": [],
            "all_temporal_passed": True,
            "all_metrics_passed": True,
            "requires_adjudication": False,
            "operational_status": "PASSED",
            "notes": [],
        }

        # 1. Temporal Cycle Checks (start/end frame <= max_frame_tolerance)
        cycles_a = rater_a.get("cycle_annotations", [])
        cycles_b = rater_b.get("cycle_annotations", [])

        if len(cycles_a) != len(cycles_b):
            report["all_temporal_passed"] = False
            report["requires_adjudication"] = True
            report["notes"].append(
                f"Cycle count mismatch: Rater A recorded {len(cycles_a)} cycles, Rater B recorded {len(cycles_b)} cycles."
            )
        else:
            for i in range(len(cycles_a)):
                ca = cycles_a[i]
                cb = cycles_b[i]
                start_diff = abs(ca.get("start_frame", 0) - cb.get("start_frame", 0))
                end_diff = abs(ca.get("end_frame", 0) - cb.get("end_frame", 0))
                passed = (start_diff <= max_frame_tolerance and end_diff <= max_frame_tolerance)
                if not passed:
                    report["all_temporal_passed"] = False
                    report["requires_adjudication"] = True
                report["temporal_discrepancies"].append({
                    "cycle_index": i + 1,
                    "rater_a_start": ca.get("start_frame"),
                    "rater_b_start": cb.get("start_frame"),
                    "start_frame_diff": start_diff,
                    "rater_a_end": ca.get("end_frame"),
                    "rater_b_end": cb.get("end_frame"),
                    "end_frame_diff": end_diff,
                    "passed": passed,
                })

        # 2. Metric Discrepancies
        metrics_a = rater_a.get("metric_annotations", {})
        metrics_b = rater_b.get("metric_annotations", {})
        all_metric_keys = sorted(list(set(metrics_a.keys()).union(set(metrics_b.keys()))))

        tolerances = {
            "stroke_rate_spm": 2.0,
            "cycle_duration_ms": 60.0,
            "mean_elbow_angle_deg": 6.0,
            "mean_knee_angle_deg": 6.0,
            "body_roll_amplitude_deg": 6.0,
            "stroke_symmetry_percent": 5.0,
            "hand_excursion_proxy_bl": 0.08,
        }

        for m_key in all_metric_keys:
            obj_a = metrics_a.get(m_key, {})
            obj_b = metrics_b.get(m_key, {})
            val_a = obj_a.get("value") if isinstance(obj_a, dict) else None
            val_b = obj_b.get("value") if isinstance(obj_b, dict) else None

            if val_a is not None and val_b is not None:
                diff = abs(val_a - val_b)
                tol = tolerances.get(m_key, 5.0)
                passed = (diff <= tol)
                if not passed:
                    report["all_metrics_passed"] = False
                    report["requires_adjudication"] = True
                    report["notes"].append(
                        f"Metric '{m_key}' divergence exceeds operational threshold: |{val_a} - {val_b}| = {diff:.2f} > {tol}"
                    )
                report["metric_discrepancies"].append({
                    "metric": m_key,
                    "rater_a_value": val_a,
                    "rater_b_value": val_b,
                    "absolute_diff": round(diff, 3),
                    "tolerance": tol,
                    "passed": passed,
                })
            elif val_a is not None or val_b is not None:
                report["all_metrics_passed"] = False
                report["requires_adjudication"] = True
                report["metric_discrepancies"].append({
                    "metric": m_key,
                    "rater_a_value": val_a,
                    "rater_b_value": val_b,
                    "passed": False,
                    "error": "Metric present in only one rater annotation.",
                })

        if report["requires_adjudication"]:
            report["operational_status"] = "ADJUDICATION_REQUIRED"
        else:
            report["operational_status"] = "PASSED"

        return report

    def compute_cohort_metric_iccs(
        self,
        trial_pairs_by_metric: Dict[str, List[Tuple[float, float]]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Computes ICC(2,1) for every metric separately across the cohort of trials.
        Strictly prevents pooling heterogeneous metrics.
        """
        results = {}
        for m_name, pairs in trial_pairs_by_metric.items():
            results[m_name] = compute_metric_icc_2_1(m_name, pairs)
        return results

    def process_and_save_trial_qc(
        self,
        sample_id: str,
        rater_a_data: Dict[str, Any],
        rater_b_data: Dict[str, Any],
        adjudication_data: Optional[Dict[str, Any]] = None,
        save_to_annotations: bool = True,
    ) -> Tuple[bool, Dict[str, Any], List[str]]:
        """
        Processes single-trial dual-rater quality control and preserves audit artifacts.
        Enforces content-level blinding, timestamp integrity, and operational discrepancy gating.
        """
        errors: List[str] = []
        sample_qc_dir = self.qc_dir / sample_id
        sample_qc_dir.mkdir(parents=True, exist_ok=True)

        # 1. Content-level Blinding Check
        ok_a, blind_errs_a = verify_content_level_blinding(rater_a_data, "Rater A")
        ok_b, blind_errs_b = verify_content_level_blinding(rater_b_data, "Rater B")
        all_blind_errs = blind_errs_a + blind_errs_b
        if not ok_a or not ok_b:
            return False, {}, all_blind_errs

        # 2. Timestamp Integrity Check (cannot be future-dated)
        now_utc = datetime.now(timezone.utc)
        for r_name, r_data in [("Rater A", rater_a_data), ("Rater B", rater_b_data)]:
            ts_str = r_data.get("annotation_timestamp")
            if ts_str:
                try:
                    ts_clean = ts_str.replace("Z", "+00:00")
                    dt = datetime.fromisoformat(ts_clean)
                    if dt > (now_utc + timedelta(seconds=60)):
                        errors.append(f"TIMESTAMP ERROR in {r_name}: future-dated timestamp '{ts_str}' rejected.")
                        return False, {}, errors
                except Exception as e:
                    errors.append(f"TIMESTAMP PARSE ERROR in {r_name}: {e}")
                    return False, {}, errors

        # 3. Save raw rater annotations
        with open(sample_qc_dir / "rater_A.json", "w", encoding="utf-8") as f:
            json.dump(rater_a_data, f, indent=2)

        with open(sample_qc_dir / "rater_B.json", "w", encoding="utf-8") as f:
            json.dump(rater_b_data, f, indent=2)

        # 4. Evaluate discrepancies (no fake per-trial ICC!)
        discrepancy_report = self.evaluate_single_trial_discrepancies(sample_id, rater_a_data, rater_b_data)
        with open(sample_qc_dir / "agreement.json", "w", encoding="utf-8") as f:
            json.dump(discrepancy_report, f, indent=2)

        # 5. Adjudication check
        if discrepancy_report["requires_adjudication"]:
            if not adjudication_data:
                errors.append(
                    f"Sample {sample_id} requires adjudication due to inter-rater discrepancies, but no adjudication record provided."
                )
                return False, discrepancy_report, errors
            adj_record = adjudication_data
        else:
            adj_record = {
                "sample_id": sample_id,
                "adjudication": "NOT_REQUIRED",
                "reason": "All inter-rater discrepancy criteria met within operational tolerances.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        with open(sample_qc_dir / "adjudication.json", "w", encoding="utf-8") as f:
            json.dump(adj_record, f, indent=2)

        # 6. Produce final Ground Truth record
        final_gt = dict(rater_a_data)
        final_gt["sample_id"] = sample_id
        final_gt["secondary_annotator_id"] = rater_b_data.get("annotator_id", "EXPERT-RATER-02")
        final_gt["annotation_version"] = "1.0.0"
        final_gt["annotation_timestamp"] = datetime.now(timezone.utc).isoformat()

        # Update quality flags (explicitly null out per-trial ICC)
        q_flags = final_gt.get("quality_flags", {})
        q_flags["inter_rater_agreement_icc"] = None  # ICC computed at cohort level, not single trial
        q_flags["requires_adjudication"] = discrepancy_report.get("requires_adjudication", False)
        final_gt["quality_flags"] = q_flags

        # Merge cycle annotations (mean of start/end frames)
        merged_cycles = []
        cycles_a = rater_a_data.get("cycle_annotations", [])
        cycles_b = rater_b_data.get("cycle_annotations", [])
        fps = float(final_gt.get("video_fps", 30.0))

        for i in range(min(len(cycles_a), len(cycles_b))):
            ca = cycles_a[i]
            cb = cycles_b[i]
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

        # Merge metrics (consensus arithmetic mean)
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
                merged_entry["value"] = round((val_a + val_b) / 2.0, 2)
            merged_metrics[m_key] = merged_entry

        if adjudication_data and "metric_overrides" in adjudication_data:
            for ov_k, ov_v in adjudication_data["metric_overrides"].items():
                if ov_k in merged_metrics:
                    merged_metrics[ov_k]["value"] = ov_v

        final_gt["metric_annotations"] = merged_metrics

        # Save final_ground_truth.json in QC dir
        with open(sample_qc_dir / "final_ground_truth.json", "w", encoding="utf-8") as f:
            json.dump(final_gt, f, indent=2)

        if save_to_annotations:
            self.annotations_dir.mkdir(parents=True, exist_ok=True)
            ann_path = self.annotations_dir / f"{sample_id}.json"
            with open(ann_path, "w", encoding="utf-8") as f:
                json.dump(final_gt, f, indent=2)

        return True, final_gt, []
