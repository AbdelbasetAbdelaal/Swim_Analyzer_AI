"""
Unit tests for HybridStrokeDecisionEngine and VisibilityGate.
"""

from unittest.mock import MagicMock
from models.data_models import StrokeType, StrokeDetectionResult
from analysis.classification.visibility_gate import VisibilityGate, VisibilityGateResult
from analysis.classification.hybrid_stroke_decision_engine import HybridStrokeDecisionEngine

def test_visibility_gate_evaluation():
    """Verify VisibilityGate evaluates frame sequence visibility ratio cleanly."""
    gate = VisibilityGate(min_valid_ratio=0.05)
    
    lms = [MagicMock(x=0.5, y=0.5, z=0.0, visibility=0.9) for _ in range(33)]
    frames = [type('SimpleFrame', (), {'raw_landmarks': lms})() for _ in range(10)]

    res = gate.evaluate(frames)
    assert res.is_sufficient is True
    assert res.total_frames == 10
    assert res.valid_frames == 10
    assert res.visibility_ratio == 1.0

def test_hybrid_stroke_decision_engine_fusion():
    """Verify HybridStrokeDecisionEngine fuses Rule and AI results into 6-part decision structure."""
    engine = HybridStrokeDecisionEngine(rule_weight=0.5, ai_weight=0.5)

    rule_res = StrokeDetectionResult(
        predicted_stroke=StrokeType.FREESTYLE, confidence=0.85,
        predictions={"Freestyle": 0.85, "Backstroke": 0.05, "Breaststroke": 0.05, "Butterfly": 0.05},
        selected_stroke=StrokeType.AUTO_DETECT, manual_override=False, is_inconsistent=False,
        classification_status="ACCEPTED", classification_reason="Rule test",
        feature_values={}, feature_contributions={"arm_phase_alternating": 0.85},
        classifier_version="1.0", threshold_version="1.0"
    )

    ai_res = StrokeDetectionResult(
        predicted_stroke=StrokeType.FREESTYLE, confidence=0.90,
        predictions={"Freestyle": 0.90, "Backstroke": 0.04, "Breaststroke": 0.03, "Butterfly": 0.03},
        selected_stroke=StrokeType.AUTO_DETECT, manual_override=False, is_inconsistent=False,
        classification_status="ACCEPTED", classification_reason="AI test",
        feature_values={"arm_phase_correlation": -0.85}, feature_contributions={"ai_ensemble": 0.90},
        classifier_version="2.0", threshold_version="2.0"
    )

    vis_res = VisibilityGateResult(
        is_sufficient=True, total_frames=100, valid_frames=90,
        visibility_ratio=0.90, wrist_visibility=0.85, shoulder_visibility=0.90,
        ankle_visibility=0.85, missing_landmarks=[],
        gate_reason="Good visibility"
    )

    decision = engine.evaluate_hybrid_decision(rule_res, ai_res, vis_res)

    assert decision.stroke_type == StrokeType.FREESTYLE
    assert decision.confidence >= 0.85
    assert "visibility_ratio" in decision.evidence
    assert "arm_phase_alternating" in decision.rule_contributions
    assert "ai_ensemble" in decision.ai_contributions
    assert 0.0 <= decision.uncertainty <= 1.0
