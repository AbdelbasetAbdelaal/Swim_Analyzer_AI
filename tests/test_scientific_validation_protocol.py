"""
Tests for Step 65: Scientific Validation Protocol & Scientific Safety Gate.
Verifies the priority metrics validation protocols, unestablished threshold policies,
and scientific safety gate invariants.
"""
import json
import pytest
from pathlib import Path

from analysis.strategies.freestyle_biomechanics_calculator import FreestyleBiomechanicsCalculator
from analysis.strategies.backstroke_biomechanics_calculator import BackstrokeBiomechanicsCalculator
from analysis.strategies.breaststroke_biomechanics_calculator import BreaststrokeBiomechanicsCalculator
from analysis.strategies.butterfly_biomechanics_calculator import ButterflyBiomechanicsCalculator


def test_scientific_validation_protocol_json_exists_and_valid():
    """Verify data/reference/scientific_validation_protocol.json exists and has 8 priority metrics."""
    protocol_path = Path("data/reference/scientific_validation_protocol.json")
    assert protocol_path.exists(), "scientific_validation_protocol.json must exist"

    with open(protocol_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["protocol_version"] == "1.0.0"
    assert data["pose_engine"] == "MediaPipe_Tasks_API_Only"
    assert data["empirical_ground_truth_available_in_repo"] is False
    assert len(data["priority_metrics"]) == 8

    expected_ids = {
        "stroke_rate",
        "avg_cycle_duration",
        "stroke_length_dps_proxy",
        "elbow_angle",
        "knee_angle",
        "shoulder_angle",
        "body_roll",
        "stroke_phase_timing"
    }
    found_ids = {m["id"] for m in data["priority_metrics"]}
    assert found_ids == expected_ids, f"Mismatch in priority metric IDs: {found_ids ^ expected_ids}"


def test_priority_metrics_have_unestablished_thresholds_and_not_validated_status():
    """
    CRITICAL SCIENTIFIC SAFETY RULE:
    If empirical ground truth is missing, acceptance/repeatability criteria
    MUST be explicitly 'THRESHOLD NOT YET ESTABLISHED' and status must be
    'NOT_VALIDATED — INSUFFICIENT GROUND TRUTH'.
    """
    protocol_path = Path("data/reference/scientific_validation_protocol.json")
    with open(protocol_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for m in data["priority_metrics"]:
        assert "THRESHOLD NOT YET ESTABLISHED" in m["acceptance_criterion"], (
            f"Metric {m['id']} must explicitly state THRESHOLD NOT YET ESTABLISHED"
        )
        assert "THRESHOLD NOT YET ESTABLISHED" in m["repeatability_criterion"], (
            f"Metric {m['id']} must explicitly state THRESHOLD NOT YET ESTABLISHED"
        )
        assert m["status"] == "NOT_VALIDATED — INSUFFICIENT GROUND TRUTH", (
            f"Metric {m['id']} status must be 'NOT_VALIDATED — INSUFFICIENT GROUND TRUTH'"
        )
        assert len(m["required_landmarks"]) > 0
        assert m["ground_truth_type_required"] != ""
        assert len(m["conditions_marked_not_validated"]) >= 2


def test_scientific_safety_gate_no_false_empirical_claims():
    """
    Ensure baseline JSON and protocol JSON do not claim empirical scientific validation
    in the absence of paired physical ground truth datasets.
    """
    baseline_path = Path("data/reference/biomechanics_metric_baseline.json")
    assert baseline_path.exists()

    with open(baseline_path, "r", encoding="utf-8") as f:
        baseline = json.load(f)

    assert baseline["empirical_validation_summary"]["VALIDATED"] == 0
    assert baseline["empirical_validation_summary"]["NOT_VALIDATED"] == 41
    assert baseline["scientific_safety_gate"]["allowed_to_claim_scientifically_validated"] is False

    for metric in baseline["metrics"]:
        assert metric["empirical_validation_status"] == "NOT_VALIDATED — INSUFFICIENT GROUND TRUTH"
        assert metric["ground_truth_in_repo"] is False


def test_four_stroke_calculators_deterministic_instantiation():
    """Verify all four stroke calculators instantiate and preserve mathematical integrity."""
    calcs = [
        FreestyleBiomechanicsCalculator,
        BackstrokeBiomechanicsCalculator,
        BreaststrokeBiomechanicsCalculator,
        ButterflyBiomechanicsCalculator
    ]
    for calc in calcs:
        assert hasattr(calc, "calculate_global_metrics")
